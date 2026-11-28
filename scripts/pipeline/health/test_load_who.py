"""
Tests für load_who.py (CI-174) ohne API und ohne DB.
Aufruf (Shell, Repo-Wurzel, venv aktiv): python -m pytest scripts/pipeline/health/test_load_who.py -q
"""

import sys
from pathlib import Path

import pytest

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent))
import load_who as W  # noqa: E402
from lib.laender import LaenderFehler, Zuordnung  # noqa: E402

LAENDER = [
    {"iso_numeric": "068", "iso_code_3": "BOL", "iso_code_2": "BO", "name": "Bolivia", "cow_code": 145, "gw_code": 145},
    {"iso_numeric": "276", "iso_code_3": "DEU", "iso_code_2": "DE", "name": "Germany", "cow_code": 255, "gw_code": 260},
]


def z(tmp_path):
    return Zuordnung("WHO", "iso3", LAENDER, ordner=tmp_path)


def zeile(land, jahr, wert, d1=None, d2=None, d3=None, typ="COUNTRY", ttyp="YEAR"):
    return {"SpatialDimType": typ, "SpatialDim": land, "TimeDimType": ttyp, "TimeDim": jahr,
            "Dim1": d1, "Dim2": d2, "Dim3": d3, "NumericValue": wert}


def test_teenager_geburten_nimmt_15_19(tmp_path):
    # Der #92-Fall: 10–14 und 15–19 je Land-Jahr; die alte Fassung nahm die erste Zeile.
    zeilen = [zeile("BOL", 2020, 2.8, "SEX_FMLE", "AGEGROUP_YEARS10-14"),
              zeile("BOL", 2020, 89.0, "SEX_FMLE", "AGEGROUP_YEARS15-19"),
              zeile("AFR", 2020, 99.0, "SEX_FMLE", "AGEGROUP_YEARS15-19", typ="REGION")]
    out, b = W.waehle("WHO:MDG_0000000003", zeilen, z(tmp_path))
    assert out == {("068", "2020"): 89.0}
    assert b["andere_dimension"] == 1 and b["nicht_land"] == 1


def test_mehrfach_trotz_auswahl_bricht_ab(tmp_path):
    zeilen = [zeile("DEU", 2010, 20.6, "SEX_BTSX", "AGEGROUP_YEARS18-PLUS"),
              zeile("DEU", 2010, 20.7, "SEX_BTSX", "AGEGROUP_YEARS18-PLUS")]
    with pytest.raises(W.LadeFehler, match="mehrfach"):
        W.waehle("WHO:NCD_BMI_30A", zeilen, z(tmp_path))


def test_leer_nach_auswahl_bricht_ab_und_nennt_kombinationen(tmp_path):
    zeilen = [zeile("DEU", 2010, 18.9, "SEX_FMLE", "AGEGROUP_YEARS18-PLUS")]
    with pytest.raises(W.LadeFehler, match="0 Zeilen mit Auswahl.*SEX_FMLE"):
        W.waehle("WHO:NCD_BMI_30A", zeilen, z(tmp_path))


def test_unbekannter_landescode_bricht_ab(tmp_path):
    zeilen = [zeile("XKX", 2010, 5.0)]
    with pytest.raises(LaenderFehler, match="XKX"):
        W.waehle("WHO:WHS3_62", zeilen, z(tmp_path))


def test_nicht_jaehrlich_bricht_ab(tmp_path):
    with pytest.raises(W.LadeFehler, match="TimeDimType"):
        W.waehle("WHO:WHS3_62", [zeile("DEU", 2010, 1.0, ttyp="YEAR_RANGE")], z(tmp_path))


def test_null_wert_wird_gezaehlt_nicht_geladen(tmp_path):
    out, b = W.waehle("WHO:WHS3_62", [zeile("DEU", 2010, None), zeile("BOL", 2010, 0.0)], z(tmp_path))
    assert out == {("068", "2010"): 0.0} and b["ohne_wert"] == 1


class FakeResp:
    def __init__(self, status, payload=None):
        self.status_code, self._p = status, payload

    def json(self):
        return self._p


class FakeSession:
    def __init__(self, antworten):
        self.antworten, self.urls = list(antworten), []

    def get(self, url, timeout):
        self.urls.append(url)
        a = self.antworten.pop(0)
        if isinstance(a, Exception):
            raise a
        return a


def test_hole_wiederholt_und_blaettert(monkeypatch):
    monkeypatch.setattr(W, "SEITE", 2)
    monkeypatch.setattr(W.time, "sleep", lambda s: None)
    s = FakeSession([FakeResp(500), FakeResp(200, {"value": [1, 2]}), FakeResp(200, {"value": [3]})])
    assert W.hole("X", s) == [1, 2, 3]
    assert "$skip=2" in s.urls[-1] and "Dim1,Dim2,Dim3" in s.urls[0]


def test_hole_bricht_nach_drei_versuchen_laut_ab(monkeypatch):
    monkeypatch.setattr(W.time, "sleep", lambda s: None)
    s = FakeSession([FakeResp(503), W.requests.ConnectionError("weg"), FakeResp(500)])
    with pytest.raises(W.LadeFehler, match="nach 3 Versuchen"):
        W.hole("X", s)


def test_auswahl_deckt_alle_codes_der_alten_loader():
    alt = {"SDGPM25", "WSH_WATER_BASIC", "WSH_SANITATION_BASIC", "MDG_0000000001", "MDG_0000000007",
           "WHOSIS_000014", "CHILDMORT5TO14", "MDG_0000000003", "NCD_BMI_30A", "NCD_BMI_25A", "NCD_BMI_18A",
           "NCD_DIABETES_PREVALENCE_AGESTD", "NCD_DIABETES_TREATMENT_AGESTD", "NCD_BMI_PLUS1C", "NCD_BMI_MINUS2C",
           "WHS3_62", "WHS3_57", "WHS3_41", "WHS3_43", "WHS3_53", "TB_c_newinc", "TB_c_new_tsr",
           "NCD_PAA", "UHC_INDEX_REPORTED"}
    neu = {c.split(":")[1] for c in list(W.AUSWAHL) + list(W.AUSGESETZT)}
    assert alt == neu
