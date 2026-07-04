"""Engine registry and router (the ``route`` layer's selection step).

Engines register themselves against the content types they support. For a given
content type the registry returns the matching engines ordered by priority
(highest first) — that ordered list is the fallback chain the orchestrator walks
until one engine succeeds.
"""

from __future__ import annotations

from viparse.protocols import Engine


class EngineRegistry:
    """A priority-ordered registry of extraction engines."""

    def __init__(self) -> None:
        self._engines: list[Engine] = []

    def register(self, engine: Engine) -> None:
        """Add ``engine`` to the registry.

        Registering the same engine instance twice is a no-op, so accidental
        double-registration at bootstrap does not duplicate it in the fallback
        chain.
        """
        if any(existing is engine for existing in self._engines):
            return
        self._engines.append(engine)

    def engines_for(self, content_type: str) -> list[Engine]:
        """Return the engines that support ``content_type``, highest priority first.

        This is the fallback chain: try each in order until one extracts
        successfully. Engines of equal priority keep registration order (stable
        sort), so registration is the documented tie-breaker.
        """
        matches = [engine for engine in self._engines if engine.supports(content_type)]
        return sorted(matches, key=lambda engine: engine.priority, reverse=True)

    def select(self, content_type: str) -> Engine:
        """Return the highest-priority engine for ``content_type``.

        Raises ``ValueError`` if no registered engine supports it. (S1 E1.5 will
        replace this with a dedicated ``EngineUnavailable`` exception.)
        """
        chain = self.engines_for(content_type)
        if not chain:
            raise ValueError(f"no engine registered for content type {content_type!r}")
        return chain[0]
