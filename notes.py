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
import subprocess
import getpass
import shutil
import zipfile
from datetime import datetime

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

# Global password cache (cleared when script exits)
PASSWORD_CACHE = {}

def get_cached_password(file_key: str, prompt: str) -> str:
    """Get password from cache or prompt user."""
    if file_key in PASSWORD_CACHE:
        return PASSWORD_CACHE[file_key]

    password = getpass.getpass(prompt)
    PASSWORD_CACHE[file_key] = password
    return password

def encrypt_file(input_path: Path, output_path: Path, password: str) -> bool:
    """Encrypt file using OpenSSL (AES-256-CBC) with password from parameter."""
    try:
        cmd = [
            "openssl", "enc", "-aes-256-cbc",
            "-e", "-in", str(input_path),
            "-out", str(output_path),
            "-pass", f"pass:{password}",
            "-md", "sha256",
            "-pbkdf2"  # Use PBKDF2 for better compatibility
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Encryption failed: {result.stderr}", file=sys.stderr)
            return False

        return True

    except Exception as e:
        print(f"Encryption error: {e}", file=sys.stderr)
        return False

def decrypt_file(input_path: Path, output_path: Path, password: str) -> bool:
    """Decrypt file using OpenSSL with password from parameter."""
    try:
        cmd = [
            "openssl", "enc", "-aes-256-cbc",
            "-d", "-in", str(input_path),
            "-out", str(output_path),
            "-pass", f"pass:{password}",
            "-md", "sha256",
            "-pbkdf2"  # Use the same PBKDF2 for compatibility
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("Decryption failed (wrong password or corrupted file).", file=sys.stderr)
            return False

        # Extra validation: read decrypted file as UTF-8
        try:
            output_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print("Decrypted file is not valid UTF-8. Possible decryption error.", file=sys.stderr)
            return False

        return True

    except Exception as e:
        print(f"Decryption error: {e}", file=sys.stderr)
        return False


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
    """Return list of (id, path) for all .md and .enc.md files in a notebook, sorted by id."""
    folder = notebook_path(notebook)
    if not folder.exists():
        return []

    ids_and_paths = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix in [".md", ".enc.md"]:
            name = f.stem
            if name.endswith(".enc"):
                name = name[:-4]
            if name.isdigit():
                ids_and_paths.append((int(name), f))
    return sorted(ids_and_paths)




def next_id(notebook: str) -> int:
    """Next free id in notebook (1, 2, 3, ...)."""
    existing = list_note_files(notebook)
    if not existing:
        return 1
    return max(id_ for id_, _ in existing) + 1

def get_title(path: Path) -> str:
    if not path.exists():
        return "(no title)"

    # Explicit check for encrypted file
    if path.suffix == ".enc.md":
        return "🔒Encrypted note"

    try:
        content = path.read_text(encoding="utf-8")
        first = content.split("\n")[0].strip()
        return first or "(empty title)"
    except UnicodeDecodeError:
        # Extra guard: if the file looks encrypted but has .md extension
        if path.suffix == ".md" and path.stem.endswith(".enc"):
            return "🔒Encrypted note"
        return "(invalid UTF-8 encoding)"
    except Exception as e:
        print(f"Error reading note title: {e}", file=sys.stderr)
        return "(error reading title)"

def cmd_export() -> None:
    """Create a ZIP archive with all notes and notebooks, named with current timestamp."""
    if not NOTES_DIR.exists():
        print("Notes directory not found.", file=sys.stderr)
        sys.exit(1)

    # Format current date and time for archive filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"notes_backup_{timestamp}.zip"
    archive_path = PROJECT_ROOT / archive_name

    try:
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add notebooks.txt
            if NOTEBOOKS_FILE.exists():
                zipf.write(NOTEBOOKS_FILE, NOTEBOOKS_FILE.name)

            # Recursively add all files from notes directory
            for file_path in NOTES_DIR.rglob('*'):
                if file_path.is_file():
                    # Preserve relative path inside archive
                    arcname = file_path.relative_to(PROJECT_ROOT)
                    zipf.write(file_path, arcname)

        print(f"Export successful: {archive_path.relative_to(PROJECT_ROOT)}")
        print(f"Total files archived: {len(zipf.filelist)}")

    except Exception as e:
        print(f"Export failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_encrypt(notebook: str, note_id: int) -> None:
    """Encrypt a note using OpenSSL with password confirmation."""
    notebooks = get_notebooks()
    if notebook not in notebooks:
        print(f"Notebook '{notebook}' is not listed in notebooks.txt.", file=sys.stderr)
        sys.exit(1)

    folder = notebook_path(notebook)
    original_path = folder / f"{note_id}.md"
    encrypted_path = folder / f"{note_id}.enc.md"  # .enc.md extension for encrypted files

    if not original_path.exists():
        print(f"Note {note_id} in notebook '{notebook}' not found.", file=sys.stderr)
        sys.exit(1)

    # Prompt for password and confirmation
    while True:
        password1 = getpass.getpass(f"Enter password to encrypt {notebook}/{note_id}: ")
        password2 = getpass.getpass("Confirm password: ")

        if password1 == password2:
            break
        else:
            print("Passwords do not match. Please try again.")

    # Encrypt file with provided password
    if encrypt_file(original_path, encrypted_path, password1):
        # Remove original file after successful encryption
        original_path.unlink()
        print(f"Encrypted note: {notebook}/{note_id}.md -> {notebook}/{note_id}.enc.md")
    else:
        print("Encryption failed, original file preserved.", file=sys.stderr)
        sys.exit(1)



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
    # Search for note file with any supported extension
    possible_paths = [
        folder / f"{note_id}.md",
        folder / f"{note_id}.enc.md"
    ]

    target_path = None
    for path in possible_paths:
        if path.exists():
            target_path = path
            break

    if target_path is None:
        print(f"Note {note_id} in notebook '{notebook}' not found.", file=sys.stderr)
        sys.exit(1)

    target_path.unlink()
    print(f"Deleted note: {target_path.relative_to(PROJECT_ROOT)}")


def cmd_edit(notebook: str, note_id: int) -> None:
    notebooks = get_notebooks()
    if notebook not in notebooks:
        print(f"Notebook '{notebook}' is not listed in notebooks.txt.", file=sys.stderr)
        sys.exit(1)

    folder = notebook_path(notebook)
    encrypted_path = folder / f"{note_id}.enc.md"
    is_encrypted = encrypted_path.exists()

    temp_path = None
    password = None

    try:
        if is_encrypted:
            file_key = str(encrypted_path)
            password = get_cached_password(file_key, f"Enter password for {notebook}/{note_id}: ")

            # Create temporary decrypted file
            temp_path = folder / f"temp_{note_id}.md"
            if not decrypt_file(encrypted_path, temp_path, password):
                print("Failed to decrypt note for editing.", file=sys.stderr)
                sys.exit(1)
            path_to_edit = temp_path
            editor = "vim"  # Use Vim for encrypted notes
        else:
            path_to_edit = folder / f"{note_id}.md"
            if not path_to_edit.exists():
                print(f"Note {note_id} in notebook '{notebook}' not found.", file=sys.stderr)
                sys.exit(1)
            editor = "macdown"  # Use MacDown for regular notes

        # Open editor and wait for it to exit
        result = subprocess.run([editor, str(path_to_edit)], cwd=PROJECT_ROOT)

        if result.returncode != 0:
            print("Editor exited with error.", file=sys.stderr)
            raise Exception("Editor error")

        if is_encrypted:
            # Re-encrypt after editing
            if not encrypt_file(temp_path, encrypted_path, password):
                print("Failed to re-encrypt file after editing.", file=sys.stderr)
                raise Exception("Encryption failed")

            # Remove temporary file only after successful encryption
            if temp_path and temp_path.exists():
                temp_path.unlink()
                print(f"Temporary file {temp_path} removed.")

    except Exception as e:
        # Keep temporary file for debugging if an error occurs
        if temp_path and temp_path.exists():
            print(f"Temporary file preserved for debugging: {temp_path}")
        sys.exit(1)

    print(f"Edited note: {notebook}/{note_id}.md")



def cmd_move(notebook_from: str, notebook_to: str, note_id: int) -> None:
    print(f"Moving note {note_id} from '{notebook_from}' to '{notebook_to}'")

    # Validate notebooks
    notebooks = get_notebooks()
    if notebook_from not in notebooks:
        print(f"ERROR: Source notebook '{notebook_from}' not in notebooks.txt", file=sys.stderr)
        sys.exit(1)
    if notebook_to not in notebooks:
        print(f"ERROR: Target notebook '{notebook_to}' not in notebooks.txt", file=sys.stderr)
        sys.exit(1)

    folder_from = notebook_path(notebook_from)
    folder_to = notebook_path(notebook_to)
    folder_to.mkdir(parents=True, exist_ok=True)

    # Locate source file
    source_md = folder_from / f"{note_id}.md"
    source_enc = folder_from / f"{note_id}.enc.md"

    source_path = None

    if source_enc.exists():
        source_path = source_enc
    elif source_md.exists():
        source_path = source_md
    else:
        print(f"ERROR: Note {note_id} not found in '{notebook_from}'", file=sys.stderr)
        sys.exit(1)

    # Get full file extension
    full_extension = ''.join(source_path.suffixes)
    print(f"Full extension detected: {full_extension}")

    # Determine target ID and path
    new_id = next_id(notebook_to)
    target_path = folder_to / f"{new_id}{full_extension}"
    print(f"Target path: {target_path} (ID: {new_id})")

    try:
        # Move file as-is, without decryption
        print(f"Moving file: {source_path} -> {target_path}")
        shutil.move(str(source_path), str(target_path))

        # Final verification
        if target_path.exists():
            print(f"SUCCESS: Moved note: {notebook_from}/{note_id}{full_extension} -> {notebook_to}/{new_id}{full_extension}")
        else:
            print("ERROR: Target file was not created!", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"ERROR during move: {e}", file=sys.stderr)
        sys.exit(1)


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
        try:
            title = get_title(path)  # Uses updated function
            print(f"{nid}. {title}")
        except Exception as e:
            print(f"{nid}. (error reading note: {e})")



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
def cmd_flist(word: str, notebook: str = None) -> None:
    """Search note contents. If notebook is specified, search only in it and show simplified output."""
    notebooks = get_notebooks()

    # If notebook is specified, search only in it
    if notebook:
        if notebook not in notebooks:
            print(f"Notebook '{notebook}' is not listed in notebooks.txt.", file=sys.stderr)
            sys.exit(1)

        folder = notebook_path(notebook)
        if not folder.exists():
            print(f"No notes in notebook '{notebook}'.")
            return

        pattern = re.compile(re.escape(word), re.IGNORECASE)
        found_any = False

        for path in sorted(folder.glob("*.md")):
            if not path.stem.isdigit():
                continue

            try:
                text = path.read_text(encoding="utf-8")
                lines = text.split("\n")
                title = lines[0].strip() if lines else ""
                nid = int(path.stem)

                if pattern.search(text):
                    found_any = True
                    print(f"{nid}. {title}")
            except Exception as e:
                print(f"Error reading {path}: {e}", file=sys.stderr)

        if not found_any:
            print(f"No results found for \"{word}\" in notebook '{notebook}'.")

    # Global search across all notebooks (legacy behavior)
    else:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        found_any = False
        print()

        for notebook_name in notebooks:
            folder = notebook_path(notebook_name)
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
                    print(f"{notebook_name}/{nid}. {title}")

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

    flist_p = sub.add_parser("flist", help="Search note contents (all notebooks or specific notebook)")
    flist_p.add_argument("word", help="Word or phrase to search for")
    flist_p.add_argument("--notebook", "-n", help="Optional: notebook to search in (simplified output)")
    flist_p.set_defaults(func=lambda a: cmd_flist(a.word, a.notebook))


    encrypt_p = sub.add_parser("encrypt", help="Encrypt a note with password using OpenSSL")
    encrypt_p.add_argument("notebook", help="Notebook name")
    encrypt_p.add_argument("note_id", type=int, help="Note ID")
    encrypt_p.set_defaults(func=lambda a: cmd_encrypt(a.notebook, a.note_id))

    export_p = sub.add_parser("export", help="Create a ZIP archive of all notes with current timestamp")
    export_p.set_defaults(func=lambda _a: cmd_export())




    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
