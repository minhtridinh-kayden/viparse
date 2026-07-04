"""Load-time options threaded through the pipeline.

``LoadOptions`` is the single context object the orchestrator passes to each
layer, so per-call hooks (output format, encoding override, OCR, normalization
form) reach the engine, normalizer, and renderer without widening their method
signatures per hook.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OutputFormat = Literal["text", "markdown", "json"]
"""Supported renderer output formats."""

DEFAULT_OUTPUT_FORMAT: OutputFormat = "markdown"
"""The single source of truth for the default output format."""

NormalizeForm = Literal["NFC", "NFD", "NFKC", "NFKD"]
"""Unicode normalization form. viparse defaults to — and is built around — NFC."""


@dataclass(frozen=True, slots=True)
class LoadOptions:
    """Per-call knobs for :func:`viparse.load` / the pipeline.

    - ``fmt``: renderer output format.
    - ``encoding``: force a source/legacy encoding instead of auto-detecting it
      (a hint honored by the normalizer).
    - ``ocr``: force OCR on (``True``) or off (``False``); ``None`` lets the
      engine decide from the scanned-PDF hint.
    - ``normalize_form``: target Unicode normalization form (default ``"NFC"``).
    """

    fmt: OutputFormat = DEFAULT_OUTPUT_FORMAT
    encoding: str | None = None
    ocr: bool | None = None
    normalize_form: NormalizeForm = "NFC"
