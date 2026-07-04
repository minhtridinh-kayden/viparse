"""Tests for the engine registry and fallback ordering."""

from __future__ import annotations

import pytest

from viparse.errors import EngineUnavailable
from viparse.model import RawExtraction
from viparse.options import LoadOptions
from viparse.protocols import Source
from viparse.registry import EngineRegistry


class StubEngine:
    """A stub Engine that supports a fixed set of content types."""

    def __init__(self, name: str, content_types: set[str], priority: int) -> None:
        self.name = name
        self._content_types = content_types
        self.priority = priority

    def supports(self, content_type: str) -> bool:
        return content_type in self._content_types

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        return RawExtraction(source=str(source), content_type="", text="", engine=self.name)


def test_select_returns_highest_priority() -> None:
    reg = EngineRegistry()
    low = StubEngine("low", {"text/plain"}, priority=10)
    high = StubEngine("high", {"text/plain"}, priority=90)
    reg.register(low)
    reg.register(high)
    assert reg.select("text/plain").name == "high"


def test_engines_for_is_priority_ordered() -> None:
    reg = EngineRegistry()
    reg.register(StubEngine("mid", {"application/pdf"}, priority=50))
    reg.register(StubEngine("top", {"application/pdf"}, priority=99))
    reg.register(StubEngine("bottom", {"application/pdf"}, priority=1))
    reg.register(StubEngine("other", {"text/plain"}, priority=100))
    chain = reg.engines_for("application/pdf")
    assert [e.name for e in chain] == ["top", "mid", "bottom"]


def test_equal_priority_keeps_registration_order() -> None:
    reg = EngineRegistry()
    reg.register(StubEngine("first", {"x"}, priority=50))
    reg.register(StubEngine("second", {"x"}, priority=50))
    assert [e.name for e in reg.engines_for("x")] == ["first", "second"]


def test_engines_for_returns_empty_when_unsupported() -> None:
    reg = EngineRegistry()
    reg.register(StubEngine("only", {"text/plain"}, priority=10))
    assert reg.engines_for("application/pdf") == []


def test_select_raises_when_no_engine() -> None:
    reg = EngineRegistry()
    with pytest.raises(EngineUnavailable, match="no engine registered"):
        reg.select("application/pdf")


def test_double_registration_is_a_noop() -> None:
    reg = EngineRegistry()
    engine = StubEngine("only", {"x"}, priority=10)
    reg.register(engine)
    reg.register(engine)
    assert reg.engines_for("x") == [engine]
