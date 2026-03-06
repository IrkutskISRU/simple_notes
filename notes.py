#!/usr/bin/env python3
"""
Заметочница — CLI для управления заметками в ноутбуках.
Ноутбуки задаются в notebooks.txt, каждая заметка — .md файл в папке notes/<notebook>/.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


# Корень проекта — каталог, где лежит скрипт
PROJECT_ROOT = Path(__file__).resolve().parent
NOTES_DIR = PROJECT_ROOT / "notes"
NOTEBOOKS_FILE = PROJECT_ROOT / "notebooks.txt"


def get_notebooks():
    """Читает список ноутбуков из notebooks.txt."""
    if not NOTEBOOKS_FILE.exists():
        print("Файл notebooks.txt не найден.", file=sys.stderr)
        sys.exit(1)
    lines = NOTEBOOKS_FILE.read_text(encoding="utf-8").strip().splitlines()
    return [line.strip() for line in lines if line.strip()]


def notebook_path(notebook: str) -> Path:
    return NOTES_DIR / notebook


def list_note_files(notebook: str) -> list[tuple[int, Path]]:
    """Возвращает список (id, path) для всех .md в ноутбуке, отсортированный по id."""
    folder = notebook_path(notebook)
    if not folder.exists():
        return []
    ids_and_paths = []
    for f in folder.iterdir():
        if f.suffix == ".md" and f.name[:-3].isdigit():
            ids_and_paths.append((int(f.stem), f))
    return sorted(ids_and_paths)


def next_id(notebook: str) -> int:
    """Следующий свободный id в ноутбуке (1, 2, 3, ...)."""
    existing = list_note_files(notebook)
    if not existing:
        return 1
    return max(id_ for id_, _ in existing) + 1


def get_title(path: Path) -> str:
    """Первая строка файла — заголовок."""
    if not path.exists():
        return "(нет заголовка)"
    text = path.read_text(encoding="utf-8")
    first = text.split("\n")[0].strip()
    return first or "(пустой заголовок)"


def cmd_add(notebook: str) -> None:
    notebooks = get_notebooks()
    if notebook not in notebooks:
        print(f"Ноутбук '{notebook}' не указан в notebooks.txt.", file=sys.stderr)
        sys.exit(1)
    folder = notebook_path(notebook)
    folder.mkdir(parents=True, exist_ok=True)
    nid = next_id(notebook)
    path = folder / f"{nid}.md"
    path.write_text("", encoding="utf-8")
    editor = os.environ.get("EDITOR", "macdown")
    subprocess.run([editor, str(path)], cwd=PROJECT_ROOT)
    print(f"Создана заметка: {path.relative_to(PROJECT_ROOT)}")


def cmd_del(notebook: str, note_id: int) -> None:
    notebooks = get_notebooks()
    if notebook not in notebooks:
        print(f"Ноутбук '{notebook}' не указан в notebooks.txt.", file=sys.stderr)
        sys.exit(1)
    folder = notebook_path(notebook)
    path = folder / f"{note_id}.md"
    if not path.exists():
        print(f"Заметка {note_id} в ноутбуке '{notebook}' не найдена.", file=sys.stderr)
        sys.exit(1)
    path.unlink()
    print(f"Удалена заметка: {notebook}/{note_id}.md")


def cmd_edit(notebook: str, note_id: int) -> None:
    notebooks = get_notebooks()
    if notebook not in notebooks:
        print(f"Ноутбук '{notebook}' не указан в notebooks.txt.", file=sys.stderr)
        sys.exit(1)
    folder = notebook_path(notebook)
    path = folder / f"{note_id}.md"
    if not path.exists():
        print(f"Заметка {note_id} в ноутбуке '{notebook}' не найдена.", file=sys.stderr)
        sys.exit(1)
    editor = os.environ.get("EDITOR", "macdown")
    subprocess.run([editor, str(path)], cwd=PROJECT_ROOT)


def cmd_move(notebook_from: str, notebook_to: str, note_id: int) -> None:
    notebooks = get_notebooks()
    if notebook_from not in notebooks or notebook_to not in notebooks:
        print("Оба ноутбука должны быть указаны в notebooks.txt.", file=sys.stderr)
        sys.exit(1)
    folder_from = notebook_path(notebook_from)
    path_from = folder_from / f"{note_id}.md"
    if not path_from.exists():
        print(f"Заметка {note_id} в ноутбуке '{notebook_from}' не найдена.", file=sys.stderr)
        sys.exit(1)
    folder_to = notebook_path(notebook_to)
    folder_to.mkdir(parents=True, exist_ok=True)
    new_id = next_id(notebook_to)
    path_to = folder_to / f"{new_id}.md"
    path_from.rename(path_to)
    print(f"Заметка перемещена: {notebook_from}/{note_id}.md -> {notebook_to}/{new_id}.md")


def cmd_list(notebook: str) -> None:
    notebooks = get_notebooks()
    if notebook not in notebooks:
        print(f"Ноутбук '{notebook}' не указан в notebooks.txt.", file=sys.stderr)
        sys.exit(1)
    items = list_note_files(notebook)
    if not items:
        print(f"В ноутбуке '{notebook}' заметок нет.")
        return
    for nid, path in items:
        title = get_title(path)
        print(f"{nid}. {title}")


def cmd_find(word: str) -> None:
    notebooks = get_notebooks()
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    found_any = False
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
                    start = max(0, m.start() - 30)
                    end = min(len(line), m.end() + 30)
                    context = line[start:end]
                    if start > 0:
                        context = "…" + context
                    if end < len(line):
                        context = context + "…"
                    print(f"{notebook}/{nid}. {title}\t{context}")
                    break
    if not found_any:
        print(f"По запросу «{word}» ничего не найдено.")


def cmd_show() -> None:
    script = PROJECT_ROOT / "dashboard.sh"
    if not script.exists():
        print("Файл dashboard.sh не найден в корне проекта.", file=sys.stderr)
        sys.exit(1)
    # Запускаем dashboard.sh через bash в корне проекта,
    # чтобы не требовать execute-бит на файле
    subprocess.run(["bash", str(script)], cwd=PROJECT_ROOT)


def main():
    parser = argparse.ArgumentParser(prog="notes", description="Заметочница — управление заметками в ноутбуках")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Создать заметку в ноутбуке")
    add_p.add_argument("notebook", help="Имя ноутбука (например project)")
    add_p.set_defaults(func=lambda a: cmd_add(a.notebook))

    show_p = sub.add_parser("show", help="Показать дашборд заметок")
    show_p.set_defaults(func=lambda _a: cmd_show())

    edit_p = sub.add_parser("edit", help="Отредактировать заметку")
    edit_p.add_argument("notebook", help="Имя ноутбука")
    edit_p.add_argument("note_id", type=int, help="Номер заметки")
    edit_p.set_defaults(func=lambda a: cmd_edit(a.notebook, a.note_id))

    del_p = sub.add_parser("del", help="Удалить заметку")
    del_p.add_argument("notebook", help="Имя ноутбука")
    del_p.add_argument("note_id", type=int, help="Номер заметки")
    del_p.set_defaults(func=lambda a: cmd_del(a.notebook, a.note_id))

    move_p = sub.add_parser("move", help="Переместить заметку в другой ноутбук")
    move_p.add_argument("notebook_from", help="Исходный ноутбук")
    move_p.add_argument("notebook_to", help="Целевой ноутбук")
    move_p.add_argument("note_id", type=int, help="Номер заметки")
    move_p.set_defaults(func=lambda a: cmd_move(a.notebook_from, a.notebook_to, a.note_id))

    list_p = sub.add_parser("list", help="Список заметок в ноутбуке")
    list_p.add_argument("notebook", help="Имя ноутбука")
    list_p.set_defaults(func=lambda a: cmd_list(a.notebook))

    find_p = sub.add_parser("find", help="Поиск по тексту во всех ноутбуках")
    find_p.add_argument("word", help="Слово или фраза для поиска")
    find_p.set_defaults(func=lambda a: cmd_find(a.word))

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
