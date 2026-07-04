"""Tests for the viparse exception hierarchy."""

from __future__ import annotations

import pytest

import viparse
from viparse.errors import (
    EncodingError,
    EngineUnavailable,
    ExtractionError,
    MissingDependency,
    UnsupportedFormat,
    ViparseError,
)

_SUBCLASSES = [
    UnsupportedFormat,
    ExtractionError,
    EncodingError,
    EngineUnavailable,
    MissingDependency,
]


@pytest.mark.parametrize("cls", _SUBCLASSES)
def test_all_errors_derive_from_viparse_error(cls: type) -> None:
    assert issubclass(cls, ViparseError)


def test_base_error_is_an_exception() -> None:
    assert issubclass(ViparseError, Exception)


@pytest.mark.parametrize("cls", [ViparseError, *_SUBCLASSES])
def test_errors_are_exported_from_package_root(cls: type) -> None:
    assert getattr(viparse, cls.__name__) is cls


def test_can_catch_any_viparse_error_with_base() -> None:
    with pytest.raises(ViparseError):
        raise UnsupportedFormat("boom")
