"""The ``viparse`` command-line interface (SPEC-5 E5.2).

A thin wrapper over the viparse pipeline — no parsing or normalization logic lives
here, only argument handling, input expansion (globs/directories), and output
plumbing. ``viparse doctor`` reports which engines are usable given installed extras.

Uses only the standard library (``argparse``) so the ``core`` install stays light.
"""

from __future__ import annotations

import argparse
import glob as globlib
import importlib.util
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

from viparse import __version__
from viparse.api import _build_pipeline, _default_engines
from viparse.errors import ViparseError
from viparse.options import DEFAULT_NORMALIZE_FORM, LoadOptions, NormalizeForm, OutputFormat

# CLI format aliases → the canonical OutputFormat the API expects.
_OUTPUT_ALIASES: dict[str, OutputFormat] = {
    "md": "markdown",
    "markdown": "markdown",
    "text": "text",
    "txt": "text",
    "json": "json",
}
_OUTPUT_SUFFIX: dict[OutputFormat, str] = {"markdown": ".md", "text": ".txt", "json": ".json"}
_NORMALIZE_FORMS: list[NormalizeForm] = ["NFC", "NFD", "NFKC", "NFKD"]
# Extensions the built-in engines handle today; used to expand directory arguments.
_SUPPORTED_SUFFIXES = ("*.docx",)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``viparse`` command. Returns a process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    # Match ``doctor`` only when it is the sole argument, so a real file passed as
    # ``./doctor`` (or ``viparse doctor a.docx``) still reaches the file-processing mode.
    if args == ["doctor"]:
        sys.stdout.write(_doctor() + "\n")
        return 0

    ns = _build_parser().parse_args(args)
    output = _OUTPUT_ALIASES[ns.output]
    paths = _resolve_paths(ns.paths)
    if not paths:
        sys.stderr.write("viparse: no input files matched\n")
        return 1

    out_dir = Path(ns.out) if ns.out else None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    # Build the pipeline once and reuse it across every input in this invocation.
    pipeline = _build_pipeline()
    options = LoadOptions(fmt=output, encoding=ns.encoding, ocr=ns.ocr, normalize_form=ns.normalize)
    used: set[Path] = set()
    rendered: list[str] = []
    failures = 0
    for path in paths:
        try:
            document = pipeline.run(path, options)
        except (ViparseError, OSError) as exc:
            sys.stderr.write(f"viparse: {path}: {exc}\n")
            failures += 1
            continue
        if out_dir is not None:
            dest = _unique_dest(out_dir, path.stem, _OUTPUT_SUFFIX[output], used)
            dest.write_text(document.text + "\n", encoding="utf-8")
        else:
            rendered.append(document.text)

    if out_dir is None and rendered:
        sys.stdout.write("\n\n".join(rendered) + "\n")
    return 1 if failures else 0


def _unique_dest(out_dir: Path, stem: str, suffix: str, used: set[Path]) -> Path:
    """A destination path in ``out_dir`` for ``stem``, disambiguated so inputs that share
    a basename (from different directories) never silently overwrite one another."""
    candidate = out_dir / f"{stem}{suffix}"
    counter = 1
    while candidate in used:
        candidate = out_dir / f"{stem}-{counter}{suffix}"
        counter += 1
    used.add(candidate)
    return candidate


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the file-processing mode."""
    parser = argparse.ArgumentParser(
        prog="viparse",
        description="Parse Vietnamese documents into clean Unicode-NFC markdown/text/json.",
    )
    parser.add_argument("paths", nargs="+", help="files, directories, or globs to parse")
    parser.add_argument(
        "-o",
        "--output",
        choices=sorted(_OUTPUT_ALIASES),
        default="md",
        help="output format (default: md)",
    )
    parser.add_argument(
        "--out", metavar="DIR", help="write one file per input into DIR instead of stdout"
    )
    parser.add_argument("--encoding", help="force a legacy source encoding (e.g. tcvn3)")
    parser.add_argument(
        "--ocr",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="force OCR on/off (default: auto-detect)",
    )
    parser.add_argument(
        "--normalize",
        choices=_NORMALIZE_FORMS,
        default=DEFAULT_NORMALIZE_FORM,
        help="Unicode normalization form (default: NFC)",
    )
    return parser


def _resolve_paths(patterns: Sequence[str]) -> list[Path]:
    """Expand globs and directories into an ordered, de-duplicated list of files.

    Dedup keys on the resolved (absolute, symlink-collapsed) path, so the same file
    reached via a relative and an absolute argument is processed only once.
    """
    resolved: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in _expand(pattern):
            key = path.resolve()
            if key not in seen:
                seen.add(key)
                resolved.append(path)
    return resolved


def _expand(pattern: str) -> list[Path]:
    """Expand a single argument: a directory (recursive), a literal file, or a glob.

    A literal file that exists is returned as-is *before* glob interpretation, so a
    filename that legitimately contains ``[``/``]``/``*`` is not mistaken for a pattern.
    """
    path = Path(pattern)
    if path.is_dir():
        found: list[Path] = []
        for suffix in _SUPPORTED_SUFFIXES:
            found.extend(sorted(path.rglob(suffix)))
        return found
    if path.exists():
        return [path]
    if any(ch in pattern for ch in "*?["):
        return [Path(match) for match in sorted(globlib.glob(pattern, recursive=True))]
    return [path]  # a non-existent literal path — reported per-file when load opens it


def _doctor() -> str:
    """Report the viparse version and which built-in engines are usable.

    An engine can require a pip ``dependency`` and/or an external ``binary`` (e.g.
    LibreOffice's ``soffice``); both are probed so ``doctor`` never reports an engine
    available when its non-pip binary is missing.
    """
    lines = [f"viparse {__version__}", "", "Engines:"]
    for engine in _default_engines():
        name = type(engine).__name__
        dependency: str | None = getattr(engine, "dependency", None)
        extra: str | None = getattr(engine, "extra", None)
        binary: str | None = getattr(engine, "binary", None)
        if dependency is not None and importlib.util.find_spec(dependency) is None:
            status = f"unavailable — pip install 'viparse[{extra}]'"
        elif binary is not None and shutil.which(binary) is None:
            status = f"unavailable — install the {binary!r} binary"
        else:
            status = "available"
        lines.append(f"  {name} ({dependency or 'stdlib'}): {status}")
    return "\n".join(lines)
