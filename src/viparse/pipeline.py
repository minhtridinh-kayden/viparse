"""The pipeline orchestrator: route → extract → normalize → structure.

``Pipeline`` wires the four layers together for a single file and returns a
:class:`Document`. It holds an :class:`EngineRegistry` (route/extract), a
:class:`Normalizer`, and a :class:`Renderer`; concrete implementations are
injected so the orchestrator stays dependency-free and testable with fakes.

The public API is synchronous (SPEC-1 §6); parallel batch processing lives in
S7 and plugs in at :meth:`Pipeline.run_batch`.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace

from viparse.detect import DetectedFormat, detect_format
from viparse.errors import EngineUnavailable, ExtractionError, MissingDependency, ViparseError
from viparse.model import Document, DocumentMetadata, RawExtraction
from viparse.observability import MetricsHook, PipelineMetrics, logger
from viparse.options import LoadOptions
from viparse.protocols import Engine, Normalizer, Renderer, Source
from viparse.registry import EngineRegistry
from viparse.safety import check_file_size, check_zip_bomb

# Content type used for a lenient result when detection itself failed.
_UNKNOWN_CONTENT_TYPE = "application/octet-stream"


@dataclass
class _Trace:
    """Mutable per-run scratchpad the orchestrator fills for the metrics record."""

    layer_seconds: dict[str, float] = field(default_factory=dict)
    content_type: str | None = None
    engine: str | None = None
    encoding_detected: str | None = None
    ok: bool = False
    error: str | None = None

    def to_metrics(self, source: str, total_seconds: float) -> PipelineMetrics:
        """Freeze this scratchpad into an immutable metrics record."""
        return PipelineMetrics(
            source=source,
            content_type=self.content_type,
            engine=self.engine,
            encoding_detected=self.encoding_detected,
            ok=self.ok,
            total_seconds=total_seconds,
            layer_seconds=dict(self.layer_seconds),
            error=self.error,
        )


@contextmanager
def _timed(store: dict[str, float], label: str) -> Iterator[None]:
    """Record the wall-clock duration of the enclosed block under ``label``."""
    start = time.perf_counter()
    try:
        yield
    finally:
        store[label] = time.perf_counter() - start


class Pipeline:
    """Runs the extraction pipeline for a single source through injected layers."""

    def __init__(
        self,
        registry: EngineRegistry,
        normalizer: Normalizer,
        renderer: Renderer,
        metrics_hook: MetricsHook | None = None,
    ) -> None:
        self._registry = registry
        self._normalizer = normalizer
        self._renderer = renderer
        self._metrics_hook = metrics_hook

    def run(self, source: Source, options: LoadOptions | None = None) -> Document:
        """Route, extract, normalize, and render ``source`` into a Document.

        ``options`` (default :class:`LoadOptions`) is threaded to every layer so
        its hooks — output format, encoding override, OCR, normalization form —
        reach the engine, normalizer, and renderer. When ``options.ocr`` is left
        unset, the router's scanned-PDF hint resolves it before extraction.

        Every run emits a :class:`~viparse.observability.PipelineMetrics` record
        (to the logger and any metrics hook), even when it fails.
        """
        opts = options if options is not None else LoadOptions()
        trace = _Trace()
        start = time.perf_counter()
        try:
            return self._execute(source, opts, trace)
        except Exception as exc:  # noqa: BLE001 — record any failure for metrics, then re-raise
            trace.error = repr(exc)
            raise
        finally:
            self._emit(str(source), trace, time.perf_counter() - start)

    def _execute(self, source: Source, opts: LoadOptions, trace: _Trace) -> Document:
        """Run the four layers, recording timing/results into ``trace``."""
        # Detection is its own stage: on failure the content type is unknown, so
        # a lenient result falls back to a generic type. Only detect_format itself
        # is timed — building the lenient fallback is not part of "detect".
        try:
            with _timed(trace.layer_seconds, "detect"):
                check_file_size(source, opts.max_bytes)  # reject a hostile oversized file early
                detected = detect_format(source)
        except ViparseError as exc:
            if opts.strict:
                raise
            trace.error = repr(exc)
            return self._lenient_result(source, _UNKNOWN_CONTENT_TYPE, exc)

        trace.content_type = detected.content_type
        opts = self._apply_scan_hint(opts, detected)
        try:
            check_zip_bomb(source, detected.content_type)  # reject a decompression bomb
            chain = self._select_by_ocr(self._registry.engines_for(detected.content_type), opts.ocr)
            if not chain:
                raise EngineUnavailable(
                    f"no engine registered for content type {detected.content_type!r}"
                )
            with _timed(trace.layer_seconds, "extract"):
                raw = self._extract_with_fallback(chain, source, opts)
            trace.engine = raw.engine
            with _timed(trace.layer_seconds, "normalize"):
                normalized = self._normalizer.normalize(raw, opts)
            trace.encoding_detected = normalized.encoding_detected
            with _timed(trace.layer_seconds, "render"):
                document = self._renderer.render(normalized, opts.fmt)
            trace.ok = True
            return document
        except ViparseError as exc:
            # Lenient mode degrades any viparse error in the extract → normalize →
            # render stages into a best-effort Document with a warning. Non-viparse
            # errors (programming bugs) always propagate.
            if opts.strict:
                raise
            trace.error = repr(exc)
            return self._lenient_result(source, detected.content_type, exc)

    def _emit(self, source: str, trace: _Trace, total_seconds: float) -> None:
        """Log a structured summary and deliver metrics to the hook (if any)."""
        metrics = trace.to_metrics(source, total_seconds)
        logger.info(
            "viparse.load source=%s content_type=%s engine=%s encoding=%s ok=%s total=%.4fs",
            source,
            trace.content_type,
            trace.engine,
            trace.encoding_detected,
            trace.ok,
            total_seconds,
        )
        if self._metrics_hook is not None:
            try:
                self._metrics_hook(metrics)
            except Exception:  # noqa: BLE001 — a metrics hook must never break the pipeline
                logger.exception("viparse metrics hook raised")

    @staticmethod
    def _select_by_ocr(chain: list[Engine], ocr: bool | None) -> list[Engine]:
        """Order an engine chain around OCR intent.

        OCR engines (those marking ``ocr = True``) are heavy and only meaningful for
        scanned input, so they run **only when explicitly requested** (``options.ocr``
        is ``True``). When requested, OCR engines are used *exclusively* if any exist for
        the format — never with a plain-engine fallback, so an OCR failure (timeout,
        missing binary) surfaces to the caller instead of silently degrading to a
        text-less digital result. For a format with no OCR engine, the flag is moot and
        the plain engines handle it. When not requested, OCR engines are excluded.
        """
        ocr_engines = [engine for engine in chain if getattr(engine, "ocr", False)]
        plain = [engine for engine in chain if not getattr(engine, "ocr", False)]
        return (ocr_engines or plain) if ocr is True else plain

    @staticmethod
    def _apply_scan_hint(options: LoadOptions, detected: DetectedFormat) -> LoadOptions:
        """Resolve an unset ``ocr`` hook from the router's scanned-PDF hint."""
        if options.ocr is None and detected.is_scanned_pdf is not None:
            return replace(options, ocr=detected.is_scanned_pdf)
        return options

    @staticmethod
    def _extract_with_fallback(
        chain: list[Engine], source: Source, options: LoadOptions
    ) -> RawExtraction:
        """Try each engine in order, falling back when one fails to *parse* the source.

        Returns the first successful extraction. A :class:`~viparse.errors.MissingDependency`
        propagates immediately and is never masked: it means the selected engine's
        dependency (e.g. Tesseract for OCR) is not installed — an actionable infrastructure
        error, not "this engine can't handle this file", so falling back to another engine
        would silently hide it. If every engine fails to parse, raises
        :class:`~viparse.errors.ExtractionError` naming each failure, with the first
        engine's exception as ``__cause__``.
        """
        failures: list[Exception] = []
        for engine in chain:
            try:
                return engine.extract(source, options)
            except MissingDependency:
                raise  # a missing dependency is actionable and must never be masked
            except Exception as exc:  # noqa: BLE001 — fall back to the next engine
                failures.append(exc)
        detail = "; ".join(f"{type(exc).__name__}: {exc}" for exc in failures)
        raise ExtractionError(
            f"all {len(failures)} engine(s) failed to extract {source!s}: {detail}"
        ) from failures[0]

    @staticmethod
    def _lenient_result(source: Source, content_type: str, error: ViparseError) -> Document:
        """Build a best-effort empty Document that records the failure as a warning."""
        cause = error.__cause__
        detail = str(error) if cause is None else f"{error}: {cause}"
        metadata = DocumentMetadata(
            source=str(source), content_type=content_type, warnings=[detail]
        )
        return Document(text="", metadata=metadata)

    def run_batch(
        self, sources: list[Source], options: LoadOptions | None = None
    ) -> list[Document]:
        """Run :meth:`run` for each source, returning one Document per source.

        This is the extension point for batch processing: the MVP runs the
        sources sequentially; S7 replaces the body with parallel execution while
        keeping this signature.
        """
        return [self.run(source, options) for source in sources]
