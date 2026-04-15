#!/usr/bin/env python3
"""
TU Delft Research Management CLI
Manage research notes and memos for sabbatical research.
"""

import argparse
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path


BASE_DIR = Path(__file__).parent
RESEARCH_DIR = BASE_DIR / "research"
MEMOS_DIR = BASE_DIR / "memos"
TEMPLATES_DIR = BASE_DIR / "templates"

RESEARCH_TEMPLATE = TEMPLATES_DIR / "research_note.md"
MEMO_TEMPLATE = TEMPLATES_DIR / "memo.md"


def slugify(text: str) -> str:
    """Convert a title to a safe filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text


def get_author() -> str:
    """Return the author name from git config or environment, with fallback."""
    for var in ("GIT_AUTHOR_NAME", "USER", "USERNAME"):
        val = os.environ.get(var)
        if val:
            return val
    try:
        import subprocess
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, check=True
        )
        name = result.stdout.strip()
        if name:
            return name
    except Exception:
        pass
    return "Unknown"


def create_note(args):
    """Create a new research note from the template."""
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    slug = slugify(args.title)
    filename = RESEARCH_DIR / f"{today}-{slug}.md"

    if filename.exists():
        print(f"Error: Note already exists: {filename}", file=sys.stderr)
        sys.exit(1)

    template = RESEARCH_TEMPLATE.read_text()
    content = template.format(
        title=args.title,
        date=today,
        author=get_author(),
        tags=", ".join(args.tags) if args.tags else "",
        summary="",
        background="",
        notes="",
    )
    filename.write_text(content)
    print(f"Created research note: {filename}")


def create_memo(args):
    """Create a new memo from the template."""
    MEMOS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    slug = slugify(args.subject)
    filename = MEMOS_DIR / f"{today}-{slug}.md"

    if filename.exists():
        print(f"Error: Memo already exists: {filename}", file=sys.stderr)
        sys.exit(1)

    template = MEMO_TEMPLATE.read_text()
    content = template.format(
        title=args.subject,
        date=today,
        to=args.to or "",
        author=get_author(),
        subject=args.subject,
        purpose="",
        details="",
        next_steps="",
    )
    filename.write_text(content)
    print(f"Created memo: {filename}")


def list_items(args):
    """List research notes and/or memos."""
    kind = args.kind

    def _list_dir(directory: Path, label: str):
        files = sorted(directory.glob("*.md"))
        if not files:
            print(f"  (no {label} found)")
            return
        for f in files:
            # Extract title from first heading in the file
            title = f.stem
            lines = f.read_text().splitlines()
            for line in lines:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            print(f"  {f.name}  —  {title}")

    if kind in ("notes", "all"):
        print(f"\nResearch Notes ({RESEARCH_DIR}):")
        _list_dir(RESEARCH_DIR, "notes")

    if kind in ("memos", "all"):
        print(f"\nMemos ({MEMOS_DIR}):")
        _list_dir(MEMOS_DIR, "memos")


def search_items(args):
    """Search notes and memos for a keyword (case-insensitive)."""
    keyword = args.keyword.lower()
    found = False

    for label, directory in [("Research Notes", RESEARCH_DIR), ("Memos", MEMOS_DIR)]:
        if not directory.exists():
            continue
        for f in sorted(directory.glob("*.md")):
            content = f.read_text()
            if keyword in content.lower():
                if not found:
                    print()
                print(f"[{label}] {f.name}")
                # Show matching lines with context
                for i, line in enumerate(content.splitlines(), 1):
                    if keyword in line.lower():
                        print(f"  line {i}: {line.strip()}")
                found = True

    if not found:
        print(f"No results found for '{args.keyword}'.")


def main():
    parser = argparse.ArgumentParser(
        prog="research",
        description="TU Delft Research Management — manage research notes and memos.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # note
    note_parser = subparsers.add_parser("note", help="Create a new research note")
    note_parser.add_argument("title", help="Title of the research note")
    note_parser.add_argument(
        "--tags", nargs="*", metavar="TAG", help="Optional tags"
    )
    note_parser.set_defaults(func=create_note)

    # memo
    memo_parser = subparsers.add_parser("memo", help="Create a new memo")
    memo_parser.add_argument("subject", help="Subject / title of the memo")
    memo_parser.add_argument("--to", metavar="RECIPIENT", help="Recipient of the memo")
    memo_parser.set_defaults(func=create_memo)

    # list
    list_parser = subparsers.add_parser("list", help="List research notes and memos")
    list_parser.add_argument(
        "kind",
        nargs="?",
        choices=["notes", "memos", "all"],
        default="all",
        help="What to list (default: all)",
    )
    list_parser.set_defaults(func=list_items)

    # search
    search_parser = subparsers.add_parser(
        "search", help="Search notes and memos for a keyword"
    )
    search_parser.add_argument("keyword", help="Keyword to search for")
    search_parser.set_defaults(func=search_items)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
