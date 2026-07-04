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
