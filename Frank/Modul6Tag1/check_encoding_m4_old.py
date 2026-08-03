#!/usr/bin/env python3
"""Check and fix the encoding of the uncommitted files to UTF-8 without BOM.

The files are taken from `git status`: everything untracked, modified or
staged below the scope directory (default: the current working directory).
"""

import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def uncommitted_files(scope: Path) -> tuple[Path, list[Path]]:
    """Collect the uncommitted files below `scope`.

    Returns:
        Tuple of (repo_root, files). Deleted entries and directories are
        dropped, the source side of a rename is skipped.
    """
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=scope, capture_output=True, text=True,
            encoding="utf-8", check=True
        )
        return result.stdout

    repo_root = Path(git("rev-parse", "--show-toplevel").strip())

    # -z separates entries with NUL, so paths with spaces stay intact.
    entries = git("status", "--porcelain", "-uall", "-z", "--", str(scope)).split("\0")

    files = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        status, path = entry[:2], entry[3:]
        if status[0] in ("R", "C"):
            i += 1  # a rename/copy carries its source path as the next entry
        file_path = repo_root / path
        if file_path.is_file():
            files.append(file_path)

    return repo_root, files


def is_binary(file_path: Path) -> bool:
    """A NUL byte in the first block means the file is not text."""
    with open(file_path, "rb") as f:
        return b"\x00" in f.read(8192)


def detect_encoding_and_bom(file_path: Path) -> tuple[str, bool]:
    """Detect encoding and check for BOM.

    Returns:
        Tuple of (encoding, has_bom)
    """
    with open(file_path, "rb") as f:
        raw_data = f.read(4)

    # Check for common BOMs
    if raw_data.startswith(b'\xef\xbb\xbf'):
        return "utf-8-sig", True
    elif raw_data.startswith(b'\xff\xfe'):
        if raw_data.startswith(b'\xff\xfe\x00\x00'):
            return "utf-32-le", True
        return "utf-16-le", True
    elif raw_data.startswith(b'\xfe\xff'):
        return "utf-16-be", True
    elif raw_data.startswith(b'\x00\x00\xfe\xff'):
        return "utf-32-be", True

    # Try to detect as UTF-8 without BOM
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read()
        return "utf-8", False
    except UnicodeDecodeError:
        pass

    # Try cp1252 before latin-1: cp1252 rejects undefined bytes (e.g. 0x81),
    # while latin-1 accepts every byte value and thus acts as the final fallback.
    for encoding in ["cp1252", "latin-1", "iso-8859-1"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                f.read()
            return encoding, False
        except (UnicodeDecodeError, LookupError):
            continue

    return "unknown", False


def convert_to_utf8_no_bom(file_path: Path) -> None:
    """Convert file to UTF-8 without BOM."""
    # Read the file with detected encoding
    encoding, has_bom = detect_encoding_and_bom(file_path)

    if encoding == "unknown":
        raise ValueError(f"Cannot determine encoding for {file_path}")

    # Read content, keeping the line endings as they are on disk
    with open(file_path, "r", encoding=encoding, newline="") as f:
        content = f.read()

    # Strip a leading BOM character that the codec decoded from the BOM bytes
    # (utf-8-sig strips it automatically; utf-16-*/utf-32-* do not).
    if has_bom and content.startswith("\ufeff"):
        content = content[1:]

    # Write back as UTF-8 without BOM
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        f.write(content)


def main() -> int:
    scope = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

    print("=" * 70)
    print("Encoding Check and Fix")
    print(f"Scope: {scope}")
    print("=" * 70)

    try:
        repo_root, files = uncommitted_files(scope)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git failed: {e.stderr.strip()}")
        return 1

    if not files:
        print("No uncommitted files found — nothing to check.")
        print("\nFiles checked: 0")
        print("Files changed: 0")
        return 0

    checked_count = 0
    skipped_files = []
    changed_files = []
    errors = []

    for file_path in files:
        label = os.path.relpath(file_path, scope).replace(os.sep, "/")

        if is_binary(file_path):
            print(f"–  {label} — binary, skipped")
            skipped_files.append(label)
            continue

        checked_count += 1
        encoding, has_bom = detect_encoding_and_bom(file_path)

        # Check if needs conversion
        needs_fix = (encoding != "utf-8") or has_bom

        if needs_fix:
            print(f"⚠️  {label}")
            print(f"   Current: {encoding}, BOM: {has_bom}")
            try:
                convert_to_utf8_no_bom(file_path)
                print(f"   ✓ Converted to UTF-8 (no BOM)")
                changed_files.append(label)
            except Exception as e:
                errors.append(f"Failed to convert {label}: {e}")
                print(f"   ERROR: {e}")
        else:
            print(f"✓ {label}")

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Files checked: {checked_count}")
    print(f"Files changed: {len(changed_files)}")
    print(f"Files skipped (binary): {len(skipped_files)}")

    if changed_files:
        print("\nChanged files:")
        for f in changed_files:
            print(f"  - {f}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
