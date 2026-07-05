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

DEFAULT_NORMALIZE_FORM: NormalizeForm = "NFC"
"""The single source of truth for the default normalization form (the moat's golden rule)."""

DEFAULT_MAX_BYTES = 100 * 1024 * 1024
"""Default maximum input file size (100 MiB); a hostile oversized file is rejected early."""


@dataclass(frozen=True, slots=True)
class LoadOptions:
    """Per-call knobs for :func:`viparse.load` / the pipeline.

    - ``fmt``: renderer output format.
    - ``encoding``: force a legacy source encoding (e.g. ``"tcvn3"``) instead of relying
      on the font signal. Pass ``"auto"`` to opt into content-based detection for a
      source with no font signal (the caller asserts the text is legacy Vietnamese; it
      is off by default because it can misclassify non-Vietnamese text).
    - ``ocr``: force OCR on (``True``) or off (``False``); ``None`` lets the
      engine decide from the scanned-PDF hint.
    - ``normalize_form``: target Unicode normalization form (default ``"NFC"``).
    - ``strict``: when ``True`` (default), extraction failures raise; when
      ``False`` (lenient), the pipeline returns a best-effort result with the
      failure recorded as a warning in the document metadata.
    - ``max_bytes``: reject an input file larger than this (untrusted-input safety);
      default 100 MiB.
    """

    fmt: OutputFormat = DEFAULT_OUTPUT_FORMAT
    encoding: str | None = None
    ocr: bool | None = None
    normalize_form: NormalizeForm = DEFAULT_NORMALIZE_FORM
    strict: bool = True
    max_bytes: int = DEFAULT_MAX_BYTES
