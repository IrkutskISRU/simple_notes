# Simple notes

CLI to manage notes. All notes live in the project folder: each note is in its own **notebook** (subfolder inside `notes/`). The list of notebooks is defined in `notebooks.txt`.

## Usage

```bash
python3 notes.py <command> ...
```

It's convenient to create a short alias: `alias notes='python3 /path/to/notes/notes.py'`

## Commands

| Command | Description |
|--------|-------------|
| `notes show` | Show dashboard (`dashboard.sh`) for all notes. |
| `notes add <notebook>` | Create a note in a notebook. Creates file `notes/<notebook>/N.md` (N is auto‑increment), opens an editor (by default `macdown`, can be overridden via `EDITOR`). First line is the title, the rest is the body. |
| `notes edit <notebook> <id>` | Open an existing note in the editor (`EDITOR`, default `macdown`) for editing. |
| `notes del <notebook> <id>` | Delete note with number `id` in the given notebook. |
| `notes move <notebook_from> <notebook_to> <id>` | Move note `id` from one notebook to another (new id assigned automatically). |
| `notes list <notebook>` | List notes in a notebook: ID and title. |
| `notes find "word"` | Search contents across all notebooks. Output: ID, title and a snippet around the match. |
| `notes flist "word"` | Search contents across all notebooks. Output: notebook, ID and title of matching notes. |

## Requirements

- Python 3.10+
- For `add` and `edit`: system must have a GUI/CLI editor (defaults to `macdown`, can be set via `EDITOR`).

## Structure

- `notebooks.txt` — list of notebook names (one per line), e.g. `project` and `work`.
- `notes/<notebook>/` — folders with notes; files `1.md`, `2.md`, ... (first line = title).
