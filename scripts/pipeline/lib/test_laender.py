"""
Tests für scripts/pipeline/lib/laender.py (CI-177). Ohne DB, ohne Netz.

Aufruf (Shell, Repo-Wurzel, venv aktiv; braucht pytest):
    python -m pytest scripts/pipeline/lib/test_laender.py -q
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.laender import LaenderFehler, Zuordnung, norm  # noqa: E402

KOPF = "schluessel,name_quelle,iso3,aktion,grund,von,bis,beleg\n"

LAENDER = [
    {"iso_numeric": "562", "iso_code_3": "NER", "iso_code_2": "NE", "name": "Niger", "cow_code": 436, "gw_code": 436},
    {"iso_numeric": "566", "iso_code_3": "NGA", "iso_code_2": "NG", "name": "Nigeria", "cow_code": 475, "gw_code": 475},
    {"iso_numeric": "688", "iso_code_3": "SRB", "iso_code_2": "RS", "name": "Serbia", "cow_code": 345, "gw_code": 345},
    {"iso_numeric": "643", "iso_code_3": "RUS", "iso_code_2": "RU", "name": "Russia", "cow_code": 365, "gw_code": 365},
    {"iso_numeric": "384", "iso_code_3": "CIV", "iso_code_2": "CI", "name": "Ivory Coast", "cow_code": 437, "gw_code": 437},
    {"iso_numeric": "044", "iso_code_3": "BHS", "iso_code_2": "BS", "name": "Bahamas", "cow_code": 31, "gw_code": 31},
    {"iso_numeric": "516", "iso_code_3": "NAM", "iso_code_2": "NA", "name": "Namibia", "cow_code": 565, "gw_code": 565},
    {"iso_numeric": "999", "iso_code_3": "XXA", "iso_code_2": "XA", "name": "Doppel A", "cow_code": 900, "gw_code": None},
    {"iso_numeric": "998", "iso_code_3": "XXB", "iso_code_2": "XB", "name": "Doppel B", "cow_code": 900, "gw_code": None},
]


def z_mit(tmp_path, csv_text=None, quelle="T", art="name"):
    if csv_text is not None:
        (tmp_path / f"{quelle}.csv").write_text(KOPF + csv_text, encoding="utf-8")
    return Zuordnung(quelle, art, LAENDER, ordner=tmp_path)


def test_norm():
    assert norm("  Côte d’Ivoire ") == "cote d'ivoire"
    assert norm("Bosnia & Herzegovina") == "bosnia and herzegovina"
    assert norm("São  Tomé") == "sao tome"


def test_exakter_name_ohne_liste(tmp_path):
    z = z_mit(tmp_path)
    assert z.iso_numeric("Niger", 2020) == "562"
    assert z.iso_numeric("NIGERIA", 2020) == "566"
    assert z.wege["name_exakt"] == 2


def test_kein_teilstring_kein_fuzzy(tmp_path):
    z = z_mit(tmp_path)
    for roh in ["Niger State", "Nigeria (Federal Republic)", "Serbia and Montenegro", "Russian Federation"]:
        with pytest.raises(LaenderFehler):
            z.iso_numeric(roh, 2000)


def test_unbekannt_meldet_alle_auf_einmal(tmp_path):
    z = z_mit(tmp_path)
    with pytest.raises(LaenderFehler) as e:
        z.pruefe_alle([("Atlantis", 2000), ("Niger", 2000), ("Lemuria", 2001), ("Atlantis", 2001)])
    text = str(e.value)
    assert "2 Rohwerte nicht zugeordnet" in text
    assert "'Atlantis' (Jahre 2000–2001)" in text and "'Lemuria'" in text


def test_vorschlag_ist_nur_text(tmp_path):
    z = z_mit(tmp_path)
    with pytest.raises(LaenderFehler) as e:
        z.iso_numeric("Nigeria Republic", 2000)
    assert "Vorschlag (nur Hilfe)" in str(e.value)
    assert z.wege == {}            # kein Treffer gezählt


def test_liste_vor_exaktem_namen(tmp_path):
    # Quelle meint mit "Niger" in Wahrheit Nigeria (konstruierter Fall): Liste gewinnt.
    z = z_mit(tmp_path, "Niger,Niger,NGA,zuordnen,,,,Test\n")
    assert z.iso_numeric("Niger", 2000) == "566"
    assert z.wege["liste"] == 1


def test_verwerfen_mit_grund(tmp_path):
    z = z_mit(tmp_path, "Kosovo,Kosovo,,verwerfen,nicht in countries,,,CI-172\n")
    assert z.iso_numeric("Kosovo", 2010) is None
    assert z.verworfen[("Kosovo", "nicht in countries")] == 1


@pytest.mark.parametrize("zeile,muster", [
    ("Kosovo,Kosovo,,verwerfen,,,,x\n", "verwerfen ohne grund"),
    ("Kosovo,Kosovo,SRB,verwerfen,g,,,x\n", "verwerfen mit iso3"),
    ("Foo,Foo,,zuordnen,,,,x\n", "zuordnen ohne iso3"),
    ("Foo,Foo,NGA,umhaengen,,,,x\n", "aktion 'umhaengen'"),
    ("Foo,Foo,NGA,zuordnen,,1995,1990,x\n", "von 1995 > bis 1990"),
    ("Foo,Foo,NGA,zuordnen,,abc,,x\n", "keine Jahreszahl"),
])
def test_formfehler(tmp_path, zeile, muster):
    with pytest.raises(LaenderFehler, match=re.escape(muster)):
        z_mit(tmp_path, zeile)


def test_iso3_nicht_in_countries(tmp_path):
    with pytest.raises(LaenderFehler, match="nicht in countries"):
        z_mit(tmp_path, "Foo,Foo,ZZZ,zuordnen,,,,x\n")


def test_kopfzeile_falsch(tmp_path):
    (tmp_path / "T.csv").write_text("name,iso3\nFoo,NGA\n", encoding="utf-8")
    with pytest.raises(LaenderFehler, match="Kopfzeile"):
        Zuordnung("T", "name", LAENDER, ordner=tmp_path)


def test_von_bis(tmp_path):
    z = z_mit(tmp_path,
              "Soviet Union,Soviet Union,,verwerfen,UdSSR historisch,,1991,x\n"
              "Soviet Union,Soviet Union,RUS,zuordnen,,1992,,x\n")
    assert z.iso_numeric("Soviet Union", 1980) is None
    assert z.iso_numeric("Soviet Union", 1992) == "643"


def test_von_bis_luecke_kein_rueckfall(tmp_path):
    # Steht der Schlüssel in der Liste, gilt sie allein – auch wenn der Name exakt passen würde.
    z = z_mit(tmp_path, "Serbia,Serbia,SRB,zuordnen,,2006,,x\n")
    assert z.iso_numeric("Serbia", 2010) == "688"
    with pytest.raises(LaenderFehler, match="nicht für diese Jahre"):
        z.iso_numeric("Serbia", 2000)


def test_ueberlappende_zeitraeume(tmp_path):
    with pytest.raises(LaenderFehler, match="überlappen"):
        z_mit(tmp_path,
              "Foo,Foo,NGA,zuordnen,,1990,2000,x\n"
              "Foo,Foo,NER,zuordnen,,2000,,x\n")


def test_static_braucht_eintrag_ohne_zeitgrenzen(tmp_path):
    z = z_mit(tmp_path, "Foo,Foo,NGA,zuordnen,,1990,,x\n")
    with pytest.raises(LaenderFehler):
        z.iso_numeric("Foo", None)


def test_eins_zu_eins_je_jahr_niger_fall(tmp_path):
    # Der CI-172-Fall: zwei Rohwerte landen im selben Jahr auf Nigeria → Abbruch.
    z = z_mit(tmp_path, "Niger,Niger,NGA,zuordnen,,,,falsch eingetragen\n")
    z.iso_numeric("Niger", 2012)
    z.iso_numeric("Nigeria", 2012)
    with pytest.raises(LaenderFehler, match=r"Nigeria \(566\) 2012: \['Niger', 'Nigeria'\]"):
        z.pruefe_eindeutig()


def test_eins_zu_eins_gleicher_rohwert_mehrfach_ok(tmp_path):
    z = z_mit(tmp_path)
    for _ in range(3):
        z.iso_numeric("Nigeria", 2012)
    z.pruefe_eindeutig()


def test_codes_mit_fuehrenden_nullen_und_excel_float(tmp_path):
    z = z_mit(tmp_path, art="m49")
    assert z.iso_numeric("44", 2000) == "044"
    assert z.iso_numeric("044", 2000) == "044"
    assert z.iso_numeric("44.0", 2000) == "044"


def test_iso2_na_ist_namibia(tmp_path):
    z = z_mit(tmp_path, art="iso2")
    assert z.iso_numeric("NA", 2000) == "516"


def test_doppelter_code_greift_nicht_automatisch(tmp_path):
    z = z_mit(tmp_path, art="cow")
    with pytest.raises(LaenderFehler):
        z.iso_numeric(900, 2000)
    assert z.iso_numeric(436, 2000) == "562"


def test_ungenutzte_listenzeile_im_bericht(tmp_path):
    z = z_mit(tmp_path, "Nigerr,Nigerr,NER,zuordnen,,,,Tippfehler\n")
    z.iso_numeric("Niger", 2000)
    assert "Listenzeilen ohne Treffer: Z. 2 'Nigerr'" in z.bericht_text()


def test_neue_loader_ohne_unscharfe_wege():
    """Abnahme CI-177: umgestellte Loader enthalten keinen Fuzzy-, Paket- oder Teilstring-Weg."""
    pipeline = Path(__file__).resolve().parents[1]
    verboten = ["search_fuzzy(", "import pycountry", "countrycode", ".str.contains(", " in name.lower()"]
    for rel in ["governance/load_freedom_house.py", "international/load_henley.py",
                "economy/load_cpi.py", "culture/load_whr.py",
                "governance/load_gitoc.py", "governance/load_fsi.py",
                "international/load_kof.py"]:
        if not (pipeline / rel).exists():
            continue        # neuer Loader noch nicht übernommen
        text = (pipeline / rel).read_text(encoding="utf-8")
        if 'raise SystemExit("CI-172: Loader gesperrt' in text:
            continue        # noch nicht übernommen und weiter gesperrt – läuft nicht, also kein Risiko
        treffer = [v for v in verboten if v in text]
        assert not treffer, f"{rel}: {treffer}"
        assert "from lib.laender import" in text
