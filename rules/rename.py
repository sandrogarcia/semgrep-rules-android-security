#!/usr/bin/env python3
from pathlib import Path
import re
import sys


# Matches filenames like:
# mstg-storage-6.1.yaml  -> mstg-storage-6_1.yaml
# mstg-code-8.3.java     -> mstg-code-8_3.java
# mstg-arch-9.1.xml      -> mstg-arch-9_1.xml
#
# Also supports section names with multiple words:
# mstg-network-communication-1.2.yaml
FILENAME_RE = re.compile(
    r"^(?P<prefix>mstg-[a-z0-9-]+-)"
    r"(?P<major>\d+)\.(?P<minor>\d+)"
    r"(?P<suffix>\.[^.]+)$",
    re.IGNORECASE,
)


# Matches IDs anywhere in text files:
# MSTG-STORAGE-6.1 -> MSTG-STORAGE-6_1
# MSTG-CODE-8.3    -> MSTG-CODE-8_3
# MSTG-ARCH-9.1    -> MSTG-ARCH-9_1
#
# Also supports section names with multiple words:
# MSTG-NETWORK-COMMUNICATION-1.2
ANY_OLD_ID_RE = re.compile(
    r"\b(?P<prefix>MSTG-[A-Z0-9-]+-)"
    r"(?P<major>\d+)\.(?P<minor>\d+)\b"
)


def is_text_file(path: Path) -> bool:
    try:
        path.read_text(encoding="utf-8")
        return True
    except UnicodeDecodeError:
        return False
    except OSError:
        return False


def rename_file(path: Path, dry_run: bool) -> Path:
    match = FILENAME_RE.match(path.name)
    if not match:
        return path

    new_name = (
        f"{match.group('prefix')}"
        f"{match.group('major')}_{match.group('minor')}"
        f"{match.group('suffix')}"
    )
    new_path = path.with_name(new_name)

    if new_path.exists():
        raise FileExistsError(
            f"Cannot rename {path} -> {new_path}: target already exists"
        )

    print(f"RENAME FILE: {path.name} -> {new_path.name}")

    if not dry_run:
        path.rename(new_path)

    return new_path


def replace_dotted_ids_in_file(path: Path, dry_run: bool) -> int:
    if not path.is_file():
        return 0

    if not is_text_file(path):
        return 0

    text = path.read_text(encoding="utf-8")

    def replace(match: re.Match) -> str:
        return (
            f"{match.group('prefix')}"
            f"{match.group('major')}_{match.group('minor')}"
        )

    new_text, count = ANY_OLD_ID_RE.subn(replace, text)

    if count:
        print(
            f"UPDATE IDS: {path.name} "
            f"({count} replacement{'s' if count != 1 else ''})"
        )

        if not dry_run:
            path.write_text(new_text, encoding="utf-8")

    return count


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    recursive = "--recursive" in sys.argv or "-r" in sys.argv
    root = Path(".")

    if recursive:
        files_before = sorted(p for p in root.rglob("*") if p.is_file())
    else:
        files_before = sorted(p for p in root.iterdir() if p.is_file())

    # First rename files.
    for path in files_before:
        rename_file(path, dry_run=dry_run)

    # Then scan all files for old dotted IDs.
    if recursive:
        files_after = sorted(p for p in root.rglob("*") if p.is_file())
    else:
        files_after = sorted(p for p in root.iterdir() if p.is_file())

    total_replacements = 0

    for path in files_after:
        total_replacements += replace_dotted_ids_in_file(path, dry_run=dry_run)

    if total_replacements == 0:
        print("No dotted MSTG IDs found inside files.")
    else:
        print(
            f"Done. Replaced {total_replacements} dotted ID reference"
            f"{'s' if total_replacements != 1 else ''}."
        )

    if dry_run:
        print("Dry run only. No files were changed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
