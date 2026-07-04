"""Observability for the pipeline: a module logger and a metrics record.

viparse logs through the standard-library ``logging`` module under the
``viparse`` logger, so applications control handlers and levels. The orchestrator
also emits a :class:`PipelineMetrics` record per run to an optional metrics hook,
so downstream can measure throughput and per-layer timing without parsing logs.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger("viparse")


@dataclass(frozen=True, slots=True)
class PipelineMetrics:
    """A per-run measurement emitted by the orchestrator.

    ``ok`` is ``True`` only for a fully successful run; a lenient degrade or a
    strict failure reports ``ok=False`` with ``error`` set. ``layer_seconds`` maps
    each executed layer (``detect``, ``extract``, ``normalize``, ``render``) to its
    wall-clock duration.
    """

    source: str
    content_type: str | None
    engine: str | None
    encoding_detected: str | None
    ok: bool
    total_seconds: float
    layer_seconds: dict[str, float] = field(default_factory=dict, hash=False)
    error: str | None = None


MetricsHook = Callable[[PipelineMetrics], None]
"""A callback invoked once per pipeline run with its :class:`PipelineMetrics`."""
