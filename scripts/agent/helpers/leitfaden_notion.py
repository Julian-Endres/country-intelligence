"""
Wandelt einen Quellen-Leitfaden (leitfaden.md, normales Markdown) in Notion-Markdown mit
ausklappbaren Abschnitten um: jede "## …"-Überschrift wird eine Toggle-Überschrift, der Abschnitt
ihr Inhalt. Der Titel ("# …") wird zum Seitentitel und erscheint nicht im Text. Ohne KI.

Aufruf aus der Repo-Wurzel:
  python3 scripts/agent/helpers/leitfaden_notion.py <lauf>
Ergebnis: leitfaden_notion.md im Lauf-Ordner (Inhalt für die Notion-Seite, Übertragung im Chat).

Datensatz-Seite (Format vom 23.11.): Liegt im Lauf-Ordner eine kasten.md (Zeilen "Was: …", "Wer: …",
"Umfang: …", "Art der Werte: …", "Nutzung: …", optional "Vorsicht: …"), steht der Kasten oben.
Hat der Leitfaden keinen Abschnitt "Herkunft und Belege", wird er aus status.json und protokoll.md
erzeugt (Datum, Lauf, Modell, Kosten). Fehlt kasten.md, gibt es eine Warnung, keinen Abbruch.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import kasten as K, runs  # noqa: E402

TAG_LIKE = re.compile(r"<(?=[A-Za-z/])")
# Indikatorcodes mit Punkten (NY.GDP.PCAP.CD) und Dateinamen hält Notion sonst für Internetadressen
LINK_TRAP = re.compile(r"(?<![\w/`.])([A-Z][A-Z0-9]+(?:\.[A-Za-z0-9]+){2,}|[\w-]+\.(?:md|sql|json|csv|txt|py))(?![\w/`])")


# Nackte Domains (rsf.org/en/index, nobelprize.org) macht Notion zu http-Links (Fall RSF 24.11.)
DOMAIN_TRAP = re.compile(r"(?<![\w/`.@-])((?:[a-z0-9-]+\.)+(?:org|com|net|int|edu|gov|de|ch|se|uk|io)(?:/[\w./%-]*[\w/])?)(?![\w`])")


def escape_tags(line: str) -> str:
    """Notion wertet <tag> als Block-Tag; im Fließtext maskieren, in `Code` nicht (dort gilt es wörtlich)."""
    parts = line.split("`")
    for i in range(0, len(parts), 2):          # gerade Teile liegen außerhalb von Backticks
        parts[i] = TAG_LIKE.sub(r"\\<", parts[i])
        parts[i] = re.sub(r"(?<!\\)\$", r"\\$", parts[i])   # sonst setzt Notion Text zwischen zwei $ als Formel
        if "](" not in parts[i] and "://" not in parts[i]:   # echte Links nicht anfassen
            parts[i] = LINK_TRAP.sub(r"`\1`", parts[i])
            parts[i] = DOMAIN_TRAP.sub(r"`\1`", parts[i])
    return "`".join(parts)


def toggle_title(title: str) -> str:
    """Nummer am Anfang maskieren, sonst liest Notion "1. Titel" als Listenpunkt (leere Überschrift)."""
    return re.sub(r"^(\d+)\.", r"\1\\.", escape_tags(title))


def convert(md: str) -> tuple[str, str]:
    title, intro, sections = "", [], []
    current = None
    in_code = False
    for line in md.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if not in_code and line.startswith("## "):
            current = {"title": line[3:].strip(), "body": []}
            sections.append(current)
            continue
        text = line if in_code else escape_tags(line)
        target = current["body"] if current else intro
        # Zeilen, die fett beginnen ("**Wann nehmen:** …"), sonst verschmilzt Markdown sie zu einem Absatz
        if not in_code and text.startswith("**") and target and target[-1].strip() \
                and not target[-1].lstrip().startswith(("- ", "* ", "#")) and not re.match(r"\s*\d+\.", target[-1]):
            target.append("")
        target.append(text)

    out = []
    intro_text = "\n".join(intro).strip()
    if intro_text:
        out += [intro_text, ""]
    for sec in sections:
        body = "\n".join(sec["body"]).strip()
        out.append(f'<toggle heading="h2">{toggle_title(sec["title"])}')
        if body:
            out += ["", body]
        out += ["</toggle>", ""]
    return title, "\n".join(out).rstrip() + "\n"


def kasten(run_dir: Path) -> str:
    f = run_dir / "kasten.md"
    if not f.exists():
        print("WARNUNG: keine kasten.md – Seite ohne Kasten")
        return ""
    eintraege, fehler = K.parse(f.read_text(encoding="utf-8"))
    if fehler:
        sys.exit("kasten.md: " + "; ".join(fehler))
    zeilen = [f"**{feld}:** {escape_tags(text)}" for _, feld, text in eintraege]
    return '<callout icon="📌" color="gray_bg">\n' + "<br>".join(zeilen) + "\n</callout>\n\n"


def herkunft(run_dir: Path) -> str:
    st = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    d = st.get("erstellt", "")[:10]
    datum = f"{d[8:10]}.{d[5:7]}.{d[0:4]}" if len(d) == 10 else "?"
    proto = (run_dir / "protokoll.md").read_text(encoding="utf-8") if (run_dir / "protokoll.md").exists() else ""
    m = re.search(r"Modell: claude-(\w+)", proto)
    k = re.search(r"Kosten \(rechnerisch\): ([\d.]+) USD", proto)
    modell = m.group(1).capitalize() if m else "Modell ?"
    kosten = f"{float(k.group(1)):.2f}".replace(".", ",") + " USD" if k else "Kosten ?"
    if not m or not k:
        print("WARNUNG: Modell oder Kosten nicht im protokoll.md gefunden")
    zeilen = [
        f"Entwurf vom {datum}, noch nicht freigegeben.",
        f"Entwurf des Sekretär-Agenten, Lauf `{run_dir.name}` ({modell}, {kosten}).",
        "Belege pro Abschnitt: `leitfaden_belege.md`, Datenbefunde: `befunde.md`, beide im Lauf-Ordner.",
        "Nachträge von Claude sind kursiv markiert." + (" Kasten von Claude." if (run_dir / "kasten.md").exists() else ""),
    ]
    return '<toggle heading="h2">Herkunft und Belege\n\n' + "\n".join(f"- {z}" for z in zeilen) + "\n</toggle>\n"


def main(arg: str) -> None:
    run_dir = runs.resolve_run(arg)
    src = run_dir / "leitfaden.md"
    if not src.exists():
        sys.exit(f"Keine leitfaden.md in {run_dir.name}")
    title, content = convert(src.read_text(encoding="utf-8"))
    content = kasten(run_dir) + content
    if "Herkunft und Belege" not in content:
        content = content.rstrip() + "\n\n" + herkunft(run_dir)
    out = run_dir / "leitfaden_notion.md"
    out.write_text(content, encoding="utf-8")
    n = content.count('<toggle heading="h2">')
    print(f"Titel: {title or '(kein Titel)'}\n{n} ausklappbare Abschnitte -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python3 scripts/agent/helpers/leitfaden_notion.py <lauf>")
    main(sys.argv[1])
