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

from collections import deque
from collections.abc import Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor

from viparse.cache import Cache, cache_key
from viparse.chunk import ChunkOptions
from viparse.engines.docx import DocxEngine
from viparse.engines.legacy import LegacyOfficeEngine
from viparse.engines.ocr import OcrEngine
from viparse.engines.pdf import PdfEngine
from viparse.engines.xlsx import XlsxEngine
from viparse.errors import ViparseError
from viparse.model import Document, NormalizedDoc
from viparse.normalize.normalizer import VietnameseNormalizer
from viparse.options import (
    DEFAULT_MAX_BYTES,
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

# Content type for a batch error Document whose real type was never determined (matches
# the pipeline's own unknown-type sentinel).
_UNKNOWN_CONTENT_TYPE = "application/octet-stream"


def _default_engines() -> list[Engine]:
    """The engines registered by default.

    Each is a thin adapter whose heavy parse library is imported lazily at extraction
    time, so listing one here never pulls its dependency at import — ``core`` stays light.
    """
    return [DocxEngine(), XlsxEngine(), PdfEngine(), OcrEngine(), LegacyOfficeEngine()]


def _build_pipeline() -> Pipeline:
    """Assemble the default pipeline: built-in engines → normalizer → renderer."""
    registry = EngineRegistry()
    for engine in _default_engines():
        registry.register(engine)
    return Pipeline(registry, VietnameseNormalizer(), DocumentRenderer())


def _options(
    output: OutputFormat,
    encoding: str | None,
    ocr: bool | None,
    normalize: NormalizeForm,
    max_bytes: int,
    chunk: ChunkOptions | None,
) -> LoadOptions:
    """Map the public keyword parameters onto the internal :class:`LoadOptions`."""
    return LoadOptions(
        fmt=output,
        encoding=encoding,
        ocr=ocr,
        normalize_form=normalize,
        max_bytes=max_bytes,
        chunk=chunk,
    )


def load(
    source: Source,
    *,
    output: OutputFormat = DEFAULT_OUTPUT_FORMAT,
    encoding: str | None = None,
    ocr: bool | None = None,
    normalize: NormalizeForm = DEFAULT_NORMALIZE_FORM,
    max_bytes: int = DEFAULT_MAX_BYTES,
    cache: Cache | None = None,
    chunk: ChunkOptions | None = None,
) -> list[Document]:
    """Parse ``source`` into a list of Unicode-**NFC** :class:`Document` objects.

    :param source: path to the document (``str`` or :class:`~pathlib.Path`).
    :param output: rendered output format — ``"markdown"`` (default), ``"text"``, or ``"json"``.
    :param encoding: force a legacy source encoding (e.g. ``"tcvn3"``), or ``"auto"`` to
        opt into content-based detection when the source carries no font signal.
    :param ocr: force OCR on/off; ``None`` (default) lets the router decide from the file.
    :param normalize: target Unicode normalization form (default ``"NFC"``).
    :param max_bytes: reject an input larger than this many bytes (default 100 MiB).
    :param cache: optional content-hash :class:`~viparse.cache.Cache`; a cache hit skips
        re-parsing an unchanged file (SPEC-7 E7.3).
    :param chunk: optional :class:`~viparse.chunk.ChunkOptions`; when given, the returned
        Document's ``chunks`` are populated with retrieval-sized pieces (SPEC-4 E4.2).
    """
    options = _options(output, encoding, ocr, normalize, max_bytes, chunk)
    return [_load_one(_build_pipeline(), source, options, cache)]


def _load_one(
    pipeline: Pipeline, source: Source, options: LoadOptions, cache: Cache | None
) -> Document:
    """Run one source through the pipeline, consulting/populating ``cache`` if given."""
    if cache is None:
        return pipeline.run(source, options)
    key = cache_key(source, options)
    cached = cache.get(key)
    if cached is not None:
        return cached
    document = pipeline.run(source, options)
    cache.set(key, document)
    return document


def _error_document(source: Source, error: Exception, fmt: OutputFormat) -> Document:
    """A best-effort Document for a source that failed to load in a batch.

    Rendered through the normal renderer so its ``text`` is valid for the requested format
    (e.g. a parseable JSON payload under ``output="json"``, not an empty string), with the
    failure in ``metadata.warnings`` and the unknown-content sentinel as the content type.
    """
    normalized = NormalizedDoc(
        source=str(source),
        content_type=_UNKNOWN_CONTENT_TYPE,
        text="",
        warnings=[f"failed to load: {error}"],
    )
    return DocumentRenderer().render(normalized, fmt)


def _batch_load(
    pipeline: Pipeline, source: Source, options: LoadOptions, cache: Cache | None
) -> Document:
    """Load one source for a batch, isolating a per-source *failure* into an error Document.

    Only extraction/format failures (:class:`~viparse.errors.ViparseError`) and file-access
    errors (:class:`OSError`) are isolated so one bad file can't sink the batch. Programming
    bugs (``TypeError`` etc.) deliberately propagate — matching the pipeline's rule that
    they must never be silently downgraded to a warning.
    """
    try:
        return _load_one(pipeline, source, options, cache)
    except (ViparseError, OSError) as error:
        return _error_document(source, error, options.fmt)


def load_batch(
    sources: Iterable[Source],
    *,
    output: OutputFormat = DEFAULT_OUTPUT_FORMAT,
    encoding: str | None = None,
    ocr: bool | None = None,
    normalize: NormalizeForm = DEFAULT_NORMALIZE_FORM,
    max_bytes: int = DEFAULT_MAX_BYTES,
    cache: Cache | None = None,
    workers: int | None = None,
    chunk: ChunkOptions | None = None,
) -> Iterator[list[Document]]:
    """Lazily load each source, yielding its result list **in input order**.

    A generator (not a materialized list), so results stream out as they're ready and the
    caller controls consumption. Unlike :func:`load`, a batch **isolates failures**: a
    source that errors yields a best-effort Document recording the failure (its
    ``metadata.warnings``) instead of sinking the whole batch (SPEC-7 T7.2.3).

    ``workers`` (>1) parses up to that many sources concurrently on a thread pool —
    extraction is largely IO / subprocess bound (LibreOffice, Tesseract, file reads). Only
    ``workers`` sources are ever in flight at once (backpressure), and output order still
    matches the input. ``None``/1 runs sequentially. Abandoning the iterator early waits for
    the (at most ``workers``) in-flight parses to finish before the pool shuts down.

    ``chunk`` behaves as in :func:`load`: when set, each result Document's ``chunks`` are
    populated with retrieval-sized pieces.
    """
    options = _options(output, encoding, ocr, normalize, max_bytes, chunk)
    pipeline = _build_pipeline()
    if workers is None or workers <= 1:
        for source in sources:
            yield [_batch_load(pipeline, source, options, cache)]
        return
    yield from _parallel_load_batch(pipeline, sources, options, cache, workers)


def _parallel_load_batch(
    pipeline: Pipeline,
    sources: Iterable[Source],
    options: LoadOptions,
    cache: Cache | None,
    workers: int,
) -> Iterator[list[Document]]:
    """Parse sources on a bounded thread pool, yielding results in input order."""
    pending: deque[Future[Document]] = deque()
    source_iter = iter(sources)
    with ThreadPoolExecutor(max_workers=workers) as executor:

        def submit_next() -> bool:
            try:
                source = next(source_iter)
            except StopIteration:
                return False
            pending.append(executor.submit(_batch_load, pipeline, source, options, cache))
            return True

        for _ in range(workers):  # prime the in-flight window
            if not submit_next():
                break
        while pending:
            document = pending.popleft().result()  # oldest first → input order
            submit_next()  # keep the window full as each result drains
            yield [document]
