"""Exception hierarchy for viparse.

All errors raised by the library derive from :class:`ViparseError`, so callers
can catch everything viparse-specific with a single ``except ViparseError``.
"""

from __future__ import annotations


class ViparseError(Exception):
    """Base class for every error raised by viparse."""


class UnsupportedFormat(ViparseError):
    """The source's format could not be recognized or is not supported."""


class ExtractionError(ViparseError):
    """An engine failed to extract content from the source.

    The underlying engine exception is preserved as the ``__cause__``.
    """


class EncodingError(ViparseError):
    """A legacy encoding could not be detected or converted to Unicode."""


class EngineUnavailable(ViparseError):
    """No engine is registered for the source's content type."""


class MissingDependency(ViparseError):
    """An engine's optional dependency is not installed.

    Distinct from :class:`EngineUnavailable` (the format is unsupported): here the
    engine exists but its extra was not installed. The message names the extra.
    """


class UnsafeInput(ViparseError):
    """The source is rejected by a safety limit (too large, or a decompression bomb).

    Raised before parsing untrusted input, so a hostile file fails fast with a clear
    error instead of exhausting memory or time (SPEC-8 E8.3).
    """


class ConfigError(ViparseError):
    """Layered configuration is invalid (bad value in ``viparse.toml`` or a ``VIPARSE_*`` env var).

    The message names the offending key so the misconfiguration is easy to fix (SPEC-5 E5.4).
    """
