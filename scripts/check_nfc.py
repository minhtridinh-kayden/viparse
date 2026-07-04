#!/usr/bin/env python3
"""Fail if any given text file is not Unicode NFC-normalized.

NFC (Canonical Composition) is a core viparse invariant: all text the loader
emits — and all text in this repo — must be NFC so that RAG dedup and search
compare byte-for-byte. This pre-commit hook guards the repo's own sources.

Files that cannot be decoded as UTF-8 carry no Unicode NFC form and are
skipped. Files that cannot be read at all fail closed: a gate that cannot
verify a file must not pass it.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path


def is_nfc(text: str) -> bool:
    """Return True if ``text`` is already in NFC form."""
    return unicodedata.is_normalized("NFC", text)


def check_file(path: Path) -> str | None:
    """Check one file's NFC status.

    Returns ``None`` when the file is fine (NFC, or non-Unicode so NFC does not
    apply). Returns a human-readable reason string when the file must be
    rejected. Unreadable files fail closed: a gate that cannot verify a file
    must not report it as clean.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Not UTF-8, so it carries no Unicode NFC form to enforce (e.g. a
        # binary blob or an intentional legacy-encoded test fixture). Skip it.
        return None
    except OSError as exc:
        return f"could not be read ({exc.strerror or exc})"
    if not is_nfc(text):
        return "not Unicode NFC-normalized"
    return None


def main(argv: list[str]) -> int:
    offenders = [(name, reason) for name in argv if (reason := check_file(Path(name)))]
    for name, reason in offenders:
        print(f"{name}: {reason}", file=sys.stderr)
    if offenders:
        print(
            "\nNormalize the files above to NFC "
            "(e.g. unicodedata.normalize('NFC', text)) and re-stage them.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
