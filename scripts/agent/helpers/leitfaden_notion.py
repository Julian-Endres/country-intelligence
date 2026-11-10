"""
Wandelt einen Quellen-Leitfaden (leitfaden.md, normales Markdown) in Notion-Markdown mit
ausklappbaren Abschnitten um: jede "## …"-Überschrift wird eine Toggle-Überschrift, der Abschnitt
ihr Inhalt. Der Titel ("# …") wird zum Seitentitel und erscheint nicht im Text. Ohne KI.

Aufruf aus der Repo-Wurzel:
  python3 scripts/agent/helpers/leitfaden_notion.py <lauf>
Ergebnis: leitfaden_notion.md im Lauf-Ordner (Inhalt für die Notion-Seite, Übertragung im Chat).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import runs  # noqa: E402

TAG_LIKE = re.compile(r"<(?=[A-Za-z/])")
# Indikatorcodes mit Punkten (NY.GDP.PCAP.CD) und Dateinamen hält Notion sonst für Internetadressen
LINK_TRAP = re.compile(r"(?<![\w/`.])([A-Z][A-Z0-9]+(?:\.[A-Za-z0-9]+){2,}|[\w-]+\.(?:md|sql|json|csv|txt|py))(?![\w/`])")


def escape_tags(line: str) -> str:
    """Notion wertet <tag> als Block-Tag; im Fließtext maskieren, in `Code` nicht (dort gilt es wörtlich)."""
    parts = line.split("`")
    for i in range(0, len(parts), 2):          # gerade Teile liegen außerhalb von Backticks
        parts[i] = TAG_LIKE.sub(r"\\<", parts[i])
        if "](" not in parts[i] and "://" not in parts[i]:   # echte Links nicht anfassen
            parts[i] = LINK_TRAP.sub(r"`\1`", parts[i])
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


def main(arg: str) -> None:
    run_dir = runs.resolve_run(arg)
    src = run_dir / "leitfaden.md"
    if not src.exists():
        sys.exit(f"Keine leitfaden.md in {run_dir.name}")
    title, content = convert(src.read_text(encoding="utf-8"))
    out = run_dir / "leitfaden_notion.md"
    out.write_text(content, encoding="utf-8")
    n = content.count('<toggle heading="h2">')
    print(f"Titel: {title or '(kein Titel)'}\n{n} ausklappbare Abschnitte -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python3 scripts/agent/helpers/leitfaden_notion.py <lauf>")
    main(sys.argv[1])
