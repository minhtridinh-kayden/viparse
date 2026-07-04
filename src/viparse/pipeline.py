"""The pipeline orchestrator: route → extract → normalize → structure.

``Pipeline`` wires the four layers together for a single file and returns a
:class:`Document`. It holds an :class:`EngineRegistry` (route/extract), a
:class:`Normalizer`, and a :class:`Renderer`; concrete implementations are
injected so the orchestrator stays dependency-free and testable with fakes.

The public API is synchronous (SPEC-1 §6); parallel batch processing lives in
S7 and plugs in at :meth:`Pipeline.run_batch`.
"""

from __future__ import annotations

from dataclasses import replace

from viparse.detect import DetectedFormat, detect_format
from viparse.model import Document, RawExtraction
from viparse.options import LoadOptions
from viparse.protocols import Engine, Normalizer, Renderer, Source
from viparse.registry import EngineRegistry


class Pipeline:
    """Runs the extraction pipeline for a single source through injected layers."""

    def __init__(
        self,
        registry: EngineRegistry,
        normalizer: Normalizer,
        renderer: Renderer,
    ) -> None:
        self._registry = registry
        self._normalizer = normalizer
        self._renderer = renderer

    def run(self, source: Source, options: LoadOptions | None = None) -> Document:
        """Route, extract, normalize, and render ``source`` into a Document.

        ``options`` (default :class:`LoadOptions`) is threaded to every layer so
        its hooks — output format, encoding override, OCR, normalization form —
        reach the engine, normalizer, and renderer. When ``options.ocr`` is left
        unset, the router's scanned-PDF hint resolves it before extraction.
        """
        opts = options if options is not None else LoadOptions()
        detected = detect_format(source)
        opts = self._apply_scan_hint(opts, detected)
        chain = self._registry.engines_for(detected.content_type)
        if not chain:
            raise ValueError(f"no engine registered for content type {detected.content_type!r}")
        raw = self._extract_with_fallback(chain, source, opts)
        normalized = self._normalizer.normalize(raw, opts)
        return self._renderer.render(normalized, opts.fmt)

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
        """Try each engine in priority order, falling back on failure.

        Returns the first successful extraction. If every engine fails, re-raises
        the last error. (S1 E1.5 refines this into the typed error/partial policy.)
        """
        last_error: Exception | None = None
        for engine in chain:
            try:
                return engine.extract(source, options)
            except Exception as exc:  # noqa: BLE001 — fall back to the next engine
                last_error = exc
        assert last_error is not None  # chain is non-empty, so a failure was recorded
        raise last_error

    def run_batch(
        self, sources: list[Source], options: LoadOptions | None = None
    ) -> list[Document]:
        """Run :meth:`run` for each source, returning one Document per source.

        This is the extension point for batch processing: the MVP runs the
        sources sequentially; S7 replaces the body with parallel execution while
        keeping this signature.
        """
        return [self.run(source, options) for source in sources]
