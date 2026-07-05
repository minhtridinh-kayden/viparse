"""The public :func:`load` / :func:`load_batch` API — the surface most callers use.

These are thin ergonomic wrappers over :class:`~viparse.pipeline.Pipeline`, assembled
with the built-in engines, the Vietnamese normalizer, and the document renderer. The
keyword-only parameters map onto :class:`~viparse.options.LoadOptions`; keeping them
keyword-only lets the surface grow (SemVer-safely) without breaking callers.

``load`` returns a ``list[Document]`` — one entry today, but the list shape reserves
room for sources that fan out into several documents (e.g. one per spreadsheet sheet)
without a signature change.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from viparse.engines.docx import DocxEngine
from viparse.engines.xlsx import XlsxEngine
from viparse.model import Document
from viparse.normalize.normalizer import VietnameseNormalizer
from viparse.options import (
    DEFAULT_NORMALIZE_FORM,
    DEFAULT_OUTPUT_FORMAT,
    LoadOptions,
    NormalizeForm,
    OutputFormat,
)
from viparse.pipeline import Pipeline
from viparse.protocols import Engine, Source
from viparse.registry import EngineRegistry
from viparse.structure import DocumentRenderer


def _default_engines() -> list[Engine]:
    """The engines registered by default.

    Each is a thin adapter whose heavy parse library is imported lazily at extraction
    time, so listing one here never pulls its dependency at import — ``core`` stays light.
    """
    return [DocxEngine(), XlsxEngine()]


def _build_pipeline() -> Pipeline:
    """Assemble the default pipeline: built-in engines → normalizer → renderer."""
    registry = EngineRegistry()
    for engine in _default_engines():
        registry.register(engine)
    return Pipeline(registry, VietnameseNormalizer(), DocumentRenderer())


def _options(
    output: OutputFormat, encoding: str | None, ocr: bool | None, normalize: NormalizeForm
) -> LoadOptions:
    """Map the public keyword parameters onto the internal :class:`LoadOptions`."""
    return LoadOptions(fmt=output, encoding=encoding, ocr=ocr, normalize_form=normalize)


def load(
    source: Source,
    *,
    output: OutputFormat = DEFAULT_OUTPUT_FORMAT,
    encoding: str | None = None,
    ocr: bool | None = None,
    normalize: NormalizeForm = DEFAULT_NORMALIZE_FORM,
) -> list[Document]:
    """Parse ``source`` into a list of Unicode-**NFC** :class:`Document` objects.

    :param source: path to the document (``str`` or :class:`~pathlib.Path`).
    :param output: rendered output format — ``"markdown"`` (default), ``"text"``, or ``"json"``.
    :param encoding: force a legacy source encoding (e.g. ``"tcvn3"``) instead of auto-detecting.
    :param ocr: force OCR on/off; ``None`` (default) lets the router decide from the file.
    :param normalize: target Unicode normalization form (default ``"NFC"``).
    """
    options = _options(output, encoding, ocr, normalize)
    return [_build_pipeline().run(source, options)]


def load_batch(
    sources: Iterable[Source],
    *,
    output: OutputFormat = DEFAULT_OUTPUT_FORMAT,
    encoding: str | None = None,
    ocr: bool | None = None,
    normalize: NormalizeForm = DEFAULT_NORMALIZE_FORM,
) -> Iterator[list[Document]]:
    """Lazily :func:`load` each source, yielding its result list in order.

    A generator (not a materialized list) so it stays the extension point for the
    parallel batch runner in S7 without changing this signature.

    This intentionally does not delegate to :meth:`Pipeline.run_batch`: that method is
    eager and returns a flat ``list[Document]`` (one per source), whereas this yields
    lazily and nests per source (reserving room for a source that fans out into several
    documents). Both share the same per-source primitive, :meth:`Pipeline.run`.
    """
    options = _options(output, encoding, ocr, normalize)
    pipeline = _build_pipeline()
    for source in sources:
        yield [pipeline.run(source, options)]
