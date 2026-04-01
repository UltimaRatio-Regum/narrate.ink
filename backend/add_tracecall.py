#!/usr/bin/env python3
"""
add_tracecall.py — Inject @tracecall onto every function definition in each
backend .py file that doesn't already have it, then verify the result parses.

Skipped files:
  - narrate_ink_logger.py  (defines tracecall; decorating it causes recursion)
  - main.py                (already fully decorated)
  - add_tracecall.py       (this script itself)

Strategy: use the tokenize module to find every INDENT level of every
function definition, then do a line-based pass to insert decorators and fix
the import.  After writing, ast.parse() is used to confirm no syntax errors
were introduced; if it fails the original file is restored.
"""

import ast
import re
import sys
import tokenize
import io
from pathlib import Path

SKIP = {"narrate_ink_logger.py", "main.py", "add_tracecall.py"}

DEF_RE = re.compile(r"^(\s*)(async\s+def|def)\s+\w+")
DECORATOR_RE = re.compile(r"^\s*@")
# Match only top-level (zero-indent) from/import lines
TOP_IMPORT_RE = re.compile(r"^(from\s+\S+\s+import\s+.+|import\s+.+)")
NARRATE_IMPORT_RE = re.compile(r"^from\s+narrate_ink_logger\s+import\s+(.+)$")


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def _has_tracecall_above(lines: list[str], def_idx: int, def_indent: int) -> tuple[bool, int]:
    """
    Walk backwards from def_idx over blank lines and same-indent decorators.
    Returns (already_has_tracecall, first_decorator_line_index).
    """
    insert_at = def_idx
    j = def_idx - 1
    while j >= 0:
        raw = lines[j]
        stripped = raw.strip()
        if stripped == "":
            j -= 1
            continue
        if DECORATOR_RE.match(raw) and _indent_of(raw) == def_indent:
            if stripped == "@tracecall":
                return True, insert_at
            insert_at = j
            j -= 1
            continue
        break
    return False, insert_at


def process_file(path: Path) -> tuple[bool, str | None]:
    """
    Returns (modified, error_message).
    error_message is None on success.
    """
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    # ── Step 1: find def lines that need @tracecall ─────────────────────────
    insertions: list[tuple[int, str]] = []  # (insert_before_line_idx, indent_str)

    for i, line in enumerate(lines):
        m = DEF_RE.match(line)
        if not m:
            continue
        indent = m.group(1)
        already, insert_at = _has_tracecall_above(lines, i, len(indent))
        if not already:
            insertions.append((insert_at, indent))

    # Apply in reverse so indices stay valid
    for insert_at, indent in reversed(insertions):
        lines.insert(insert_at, f"{indent}@tracecall\n")

    # ── Step 2: fix the import ───────────────────────────────────────────────
    # Only scan zero-indent from/import lines so we never land inside a function.
    last_top_import_idx: int | None = None
    narrate_import_idx: int | None = None

    i = 0
    while i < len(lines):
        stripped = lines[i].rstrip("\n\r")
        if NARRATE_IMPORT_RE.match(stripped):
            narrate_import_idx = i
            break
        if TOP_IMPORT_RE.match(stripped):
            last_top_import_idx = i
            # If the import uses parentheses spanning multiple lines, skip to
            # the closing ')' so we don't insert in the middle of it.
            if "(" in stripped and ")" not in stripped:
                while i < len(lines):
                    if ")" in lines[i]:
                        last_top_import_idx = i
                        break
                    i += 1
        i += 1

    if narrate_import_idx is not None:
        # Already has the import — ensure tracecall is in it
        stripped = lines[narrate_import_idx].rstrip("\n\r")
        m = NARRATE_IMPORT_RE.match(stripped)
        names = [n.strip() for n in m.group(1).split(",")]
        if "tracecall" not in names:
            names = sorted(set(names + ["tracecall"]))
            lines[narrate_import_idx] = f"from narrate_ink_logger import {', '.join(names)}\n"
    else:
        # Insert after the last top-level import (or at top if none found)
        insert_pos = (last_top_import_idx + 1) if last_top_import_idx is not None else 0
        lines.insert(insert_pos, "from narrate_ink_logger import tracecall\n")

    result = "".join(lines)

    # ── Step 3: verify ───────────────────────────────────────────────────────
    try:
        ast.parse(result)
    except SyntaxError as e:
        return False, str(e)

    if result == original:
        return False, None

    path.write_text(result, encoding="utf-8")
    return True, None


def main():
    backend = Path(__file__).parent
    targets = sorted(p for p in backend.glob("*.py") if p.name not in SKIP)

    if not targets:
        print("No files to process.")
        return

    ok = True
    for path in targets:
        modified, err = process_file(path)
        if err:
            print(f"  ERROR      {path.name}: {err}")
            ok = False
        else:
            status = "MODIFIED" if modified else "unchanged"
            print(f"  {status:10s}  {path.name}")

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
