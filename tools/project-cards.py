#!/usr/bin/env python3
"""Generate the project cards shown in the profile README.

Cards are described in tools/projects.json (order in the file = order in the README).
Running the script renders every card to media/projects/<slug>.svg and rewrites the
block between the `projects:start` / `projects:end` markers in README.md.

Usage:
  python3 tools/project-cards.py                         # rebuild all cards + README block
  python3 tools/project-cards.py add Lorenzo0111/Repo    # fetch repo info from GitHub, append, rebuild
      [--name "Display Name"] [--tags "Tag A,Tag B"] [--description "..."] [--language Java]
  python3 tools/project-cards.py remove Repo             # remove by repo or name, rebuild

Only the Python standard library is needed.
"""
import argparse
import json
import pathlib
import re
import sys
import urllib.request
from html import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "projects.json"
OUT = ROOT / "media" / "projects"
README = ROOT / "README.md"
START, END = "<!-- projects:start -->", "<!-- projects:end -->"

# ---- look ----
W, H, PAD = 490, 190, 28
AMBER, BG, CARD, BORDER = "#fcba03", "#141414", "#232323", "#2a2a2a"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
LANG_COLORS = {
    "Java": "#e76f00", "Kotlin": "#a97bff", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "PHP": "#4f5d95", "Dart": "#00b4ab", "Rust": "#dea584", "Python": "#3572a5", "Go": "#00add8",
    "C#": "#178600", "Swift": "#f05138", "MDX": "#fcb32c", "Shell": "#89e051", "Dockerfile": "#384d54",
}
DESC_CHARS = 56          # ~characters per description line at 14.5px
MONO_W = {12: 7.3, 11.5: 7.0}  # approx. glyph width of the mono font


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def wrap(text, width=DESC_CHARS, lines=2):
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f"{cur} {w}".strip()
        else:
            out.append(cur)
            cur = w
    out.append(cur)
    if len(out) > lines:
        print(f"  ! description too long, trimmed: {text!r}", file=sys.stderr)
        out = out[:lines]
        out[-1] = out[-1].rstrip(".,;: ") + "…"
    return out


def render(n, p):
    lang = p.get("language", "")
    desc = wrap(p["description"])
    parts = [
        f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>',
        f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="17.5" fill="none" stroke="{BORDER}"/>',
        f'<text x="{PAD}" y="40" class="mono" font-size="12" letter-spacing="2" fill="{AMBER}">{n:02d}</text>',
        f'<path d="M{W-42} 40l12-12M{W-39} 28h9v9" fill="none" stroke="#6b6b6b" stroke-width="1.8" stroke-linecap="round"/>',
        f'<text x="{PAD}" y="78" class="sans" font-size="26" font-weight="700" letter-spacing="-.4" fill="#fff">{escape(p["name"])}</text>',
    ]
    for i, line in enumerate(desc):
        parts.append(f'<text x="{PAD}" y="{106 + i*20}" class="sans" font-size="14.5" fill="#a1a1a1">{escape(line)}</text>')

    x = PAD
    if lang:
        parts.append(f'<circle cx="{x+6}" cy="157" r="6" fill="{LANG_COLORS.get(lang, AMBER)}"/>'
                     f'<text x="{x+18}" y="161" class="mono" font-size="12" fill="#d4d4d4">{escape(lang)}</text>')
        x += 18 + len(lang) * MONO_W[12] + 14
    for tag in p.get("tags", []):
        tw = len(tag) * MONO_W[11.5] + 18
        if x + tw > W - PAD:
            print(f"  ! tag {tag!r} doesn't fit on {p['name']}, skipped", file=sys.stderr)
            continue
        parts.append(f'<rect x="{x:.0f}" y="146" width="{tw:.0f}" height="22" rx="11" fill="{CARD}" stroke="#333"/>'
                     f'<text x="{x + tw/2:.0f}" y="161" text-anchor="middle" class="mono" font-size="11.5" fill="#a1a1a1">{escape(tag)}</text>')
        x += tw + 8

    label = escape(f'{p["name"]}: {p["description"]}', quote=True)
    body = "\n  ".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{label}">\n'
            f'  <style>.sans{{font-family:{SANS}}} .mono{{font-family:{MONO}}}</style>\n  {body}\n</svg>\n')


def readme_block(projects):
    lines = [START]
    for p in projects:
        url = p.get("url") or f'https://github.com/{p["repo"]}'
        alt = escape(f'{p["name"]} — {p["description"]}', quote=True)
        lines.append(f'<a href="{url}"><img src="media/projects/{slugify(p["name"])}.svg" width="49%" alt="{alt}"></a>')
    lines.append(END)
    return "\n".join(lines)


def build(projects):
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = set()
    for n, p in enumerate(projects, 1):
        f = OUT / f"{slugify(p['name'])}.svg"
        f.write_text(render(n, p))
        wanted.add(f.name)
        print(f"  ✓ {f.relative_to(ROOT)}")
    for old in OUT.glob("*.svg"):
        if old.name not in wanted:
            old.unlink()
            print(f"  ✗ removed {old.relative_to(ROOT)}")
    if len(projects) % 2:
        print("  ! odd number of projects: the last card will sit alone on its row", file=sys.stderr)

    text = README.read_text()
    if START in text and END in text:
        new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: readme_block(projects), text, flags=re.S)
        README.write_text(new)
        print("  ✓ README.md updated")
    else:
        print(f"  ! README.md has no {START} … {END} markers; paste this where the cards go:\n")
        print(readme_block(projects))


def fetch_repo(repo):
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "project-cards"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    add = sub.add_parser("add", help="add a project from a GitHub repo")
    add.add_argument("repo", help="owner/name")
    add.add_argument("--name")
    add.add_argument("--description")
    add.add_argument("--language")
    add.add_argument("--tags", help="comma-separated, e.g. 'Spigot,AI'")
    add.add_argument("--position", type=int, help="1-based position (default: last)")
    rm = sub.add_parser("remove", help="remove a project")
    rm.add_argument("which", help="repo (owner/name), repo name, or display name")
    args = ap.parse_args()

    projects = json.loads(DATA.read_text())

    if args.cmd == "add":
        info = {}
        if not (args.description and args.language):
            info = fetch_repo(args.repo)
        desc = args.description or info.get("description") or ""
        desc = re.sub(r"^[^\w(]+\s*", "", desc).strip()  # drop the leading emoji used in repo descriptions
        if desc and desc[-1] not in ".!?":
            desc += "."
        tags = [t.strip() for t in args.tags.split(",")] if args.tags else (info.get("topics") or [])[:2]
        entry = {"repo": args.repo, "name": args.name or args.repo.split("/")[-1],
                 "language": args.language or info.get("language") or "", "tags": tags, "description": desc}
        projects = [p for p in projects if p["repo"].lower() != args.repo.lower()]
        projects.insert((args.position - 1) if args.position else len(projects), entry)
        print(f"Added {entry['name']}: {json.dumps(entry, ensure_ascii=False)}")
    elif args.cmd == "remove":
        key = args.which.lower()
        before = len(projects)
        projects = [p for p in projects if key not in (p["repo"].lower(), p["repo"].split("/")[-1].lower(), p["name"].lower())]
        if len(projects) == before:
            sys.exit(f"No project matches {args.which!r}")

    DATA.write_text(json.dumps(projects, indent=2, ensure_ascii=False) + "\n")
    build(projects)


if __name__ == "__main__":
    main()
