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


def escape_tags(line: str) -> str:
    """Notion wertet <tag> als Block-Tag; im Fließtext daher maskieren."""
    return TAG_LIKE.sub(r"\\<", line)


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
        (current["body"] if current else intro).append(text)

    out = []
    intro_text = "\n".join(intro).strip()
    if intro_text:
        out += [intro_text, ""]
    for sec in sections:
        body = "\n".join(sec["body"]).strip()
        out.append(f'<toggle heading="h2">{escape_tags(sec["title"])}')
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
