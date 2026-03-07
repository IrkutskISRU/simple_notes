#!/usr/bin/env python3
"""
Simple notes — CLI to manage notes in notebooks.
Notebooks are defined in notebooks.txt, each note is a .md file in notes/<notebook>/.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


# Project root — directory where this script lives
PROJECT_ROOT = Path(__file__).resolve().parent
NOTES_DIR = PROJECT_ROOT / "notes"
NOTEBOOKS_FILE = PROJECT_ROOT / "notebooks.txt"

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def get_notebooks():
    """Read list of notebooks from notebooks.txt."""
    if not NOTEBOOKS_FILE.exists():
        print("File notebooks.txt not found.", file=sys.stderr)
        sys.exit(1)
    lines = NOTEBOOKS_FILE.read_text(encoding="utf-8").strip().splitlines()
    return [line.strip() for line in lines if line.strip()]


def notebook_path(notebook: str) -> Path:
    return NOTES_DIR / notebook


def list_note_files(notebook: str) -> list[tuple[int, Path]]:
    """Return list of (id, path) for all .md files in a notebook, sorted by id."""
    folder = notebook_path(notebook)
    if not folder.exists():
        return []
    ids_and_paths = []
    for f in folder.iterdir():
        if f.suffix == ".md" and f.name[:-3].isdigit():
            ids_and_paths.append((int(f.stem), f))
    return sorted(ids_and_paths)


def next_id(notebook: str) -> int:
    """Next free id in notebook (1, 2, 3, ...)."""
    existing = list_note_files(notebook)
    if not existing:
        return 1
    return max(id_ for id_, _ in existing) + 1


def get_title(path: Path) -> str:
    """First line of the file is the title."""
    if not path.exists():
        return "(no title)"
    text = path.read_text(encoding="utf-8")
    first = text.split("\n")[0].strip()
    return first or "(empty title)"


def cmd_add(notebook: str) -> None:
    notebooks = get_notebooks()
    if notebook not in notebooks:
        print(f"Notebook '{notebook}' is not listed in notebooks.txt.", file=sys.stderr)
        sys.exit(1)
    folder = notebook_path(notebook)
    folder.mkdir(parents=True, exist_ok=True)
    nid = next_id(notebook)
    path = folder / f"{nid}.md"
    path.write_text("", encoding="utf-8")
    editor = os.environ.get("EDITOR", "macdown")
    subprocess.run([editor, str(path)], cwd=PROJECT_ROOT)
    print(f"Created note: {path.relative_to(PROJECT_ROOT)}")


def cmd_del(notebook: str, note_id: int) -> None:
    notebooks = get_notebooks()
    if notebook not in notebooks:
        print(f"Notebook '{notebook}' is not listed in notebooks.txt.", file=sys.stderr)
        sys.exit(1)
    folder = notebook_path(notebook)
    path = folder / f"{note_id}.md"
    if not path.exists():
        print(f"Note {note_id} in notebook '{notebook}' not found.", file=sys.stderr)
        sys.exit(1)
    path.unlink()
    print(f"Deleted note: {notebook}/{note_id}.md")


def cmd_edit(notebook: str, note_id: int) -> None:
    notebooks = get_notebooks()
    if notebook not in notebooks:
        print(f"Notebook '{notebook}' is not listed in notebooks.txt.", file=sys.stderr)
        sys.exit(1)
    folder = notebook_path(notebook)
    path = folder / f"{note_id}.md"
    if not path.exists():
        print(f"Note {note_id} in notebook '{notebook}' not found.", file=sys.stderr)
        sys.exit(1)
    editor = os.environ.get("EDITOR", "macdown")
    subprocess.run([editor, str(path)], cwd=PROJECT_ROOT)


def cmd_move(notebook_from: str, notebook_to: str, note_id: int) -> None:
    notebooks = get_notebooks()
    if notebook_from not in notebooks or notebook_to not in notebooks:
        print("Both notebooks must be listed in notebooks.txt.", file=sys.stderr)
        sys.exit(1)
    folder_from = notebook_path(notebook_from)
    path_from = folder_from / f"{note_id}.md"
    if not path_from.exists():
        print(f"Note {note_id} in notebook '{notebook_from}' not found.", file=sys.stderr)
        sys.exit(1)
    folder_to = notebook_path(notebook_to)
    folder_to.mkdir(parents=True, exist_ok=True)
    new_id = next_id(notebook_to)
    path_to = folder_to / f"{new_id}.md"
    path_from.rename(path_to)
    print(f"Moved note: {notebook_from}/{note_id}.md -> {notebook_to}/{new_id}.md")


def cmd_list(notebook: str) -> None:
    notebooks = get_notebooks()
    if notebook not in notebooks:
        print(f"Notebook '{notebook}' is not listed in notebooks.txt.", file=sys.stderr)
        sys.exit(1)
    items = list_note_files(notebook)
    if not items:
        print(f"No notes in notebook '{notebook}'.")
        return
    for nid, path in items:
        title = get_title(path)
        print(f"{nid}. {title}")

def cmd_find(word: str) -> None:
    notebooks = get_notebooks()
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    found_any = False
    print()

    for notebook in notebooks:
        folder = notebook_path(notebook)
        if not folder.exists():
            continue

        for path in sorted(folder.glob("*.md")):
            if not path.stem.isdigit():
                continue

            text = path.read_text(encoding="utf-8")
            lines = text.split("\n")
            title = lines[0].strip() if lines else ""
            nid = path.stem

            for i, line in enumerate(lines):
                m = pattern.search(line)
                if m:
                    found_any = True
                    match_text = m.group(0)

                    start_orig = max(0, m.start() - 30)
                    end_orig = min(len(line), m.end() + 30)
                    context_orig = line[start_orig:end_orig]
                    highlighted_context = pattern.sub(f"{RED}\\g<0>{RESET}", context_orig)
                    if start_orig > 0:
                        highlighted_context = "…" + highlighted_context
                    if end_orig < len(line):
                        highlighted_context = highlighted_context + "…"
                    print(f"{YELLOW}{notebook}/{nid}{RESET}.\n{BLUE}{title}{RESET}\n{GREEN}{highlighted_context}{RESET}\n")
                    break

    if not found_any:
        print(f"No results found for \"{word}\".")


def cmd_flist(word: str) -> None:
    notebooks = get_notebooks()
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    found_any = False
    print()

    for notebook in notebooks:
        folder = notebook_path(notebook)
        if not folder.exists():
            continue

        for path in sorted(folder.glob("*.md")):
            if not path.stem.isdigit():
                continue

            text = path.read_text(encoding="utf-8")
            lines = text.split("\n")
            title = lines[0].strip() if lines else ""
            nid = int(path.stem)

            if pattern.search(text):
                found_any = True
                print(f"{notebook}/{nid}. {title}")

    if not found_any:
        print(f"No results found for \"{word}\".")


def cmd_show() -> None:
    script = PROJECT_ROOT / "dashboard.sh"
    if not script.exists():
        print("File dashboard.sh not found in project root.", file=sys.stderr)
        sys.exit(1)
    subprocess.run(["bash", str(script)], cwd=PROJECT_ROOT)


def main():
    parser = argparse.ArgumentParser(prog="notes", description="Simple notes — manage notes in notebooks")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Create a note in a notebook")
    add_p.add_argument("notebook", help="Notebook name (e.g. project)")
    add_p.set_defaults(func=lambda a: cmd_add(a.notebook))

    show_p = sub.add_parser("show", help="Show notes dashboard")
    show_p.set_defaults(func=lambda _a: cmd_show())

    edit_p = sub.add_parser("edit", help="Edit a note")
    edit_p.add_argument("notebook", help="Notebook name")
    edit_p.add_argument("note_id", type=int, help="Note ID")
    edit_p.set_defaults(func=lambda a: cmd_edit(a.notebook, a.note_id))

    del_p = sub.add_parser("del", help="Delete a note")
    del_p.add_argument("notebook", help="Notebook name")
    del_p.add_argument("note_id", type=int, help="Note ID")
    del_p.set_defaults(func=lambda a: cmd_del(a.notebook, a.note_id))

    move_p = sub.add_parser("move", help="Move a note to another notebook")
    move_p.add_argument("notebook_from", help="Source notebook")
    move_p.add_argument("notebook_to", help="Target notebook")
    move_p.add_argument("note_id", type=int, help="Note ID")
    move_p.set_defaults(func=lambda a: cmd_move(a.notebook_from, a.notebook_to, a.note_id))

    list_p = sub.add_parser("list", help="List notes in a notebook")
    list_p.add_argument("notebook", help="Notebook name")
    list_p.set_defaults(func=lambda a: cmd_list(a.notebook))

    find_p = sub.add_parser("find", help="Search note contents in all notebooks")
    find_p.add_argument("word", help="Word or phrase to search for")
    find_p.set_defaults(func=lambda a: cmd_find(a.word))

    flist_p = sub.add_parser("flist", help="Search note contents and list results as IDs and titles")
    flist_p.add_argument("word", help="Word or phrase to search for")
    flist_p.set_defaults(func=lambda a: cmd_flist(a.word))


    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
