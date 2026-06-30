"""Smoke test: the package imports and exposes a version string."""

import viparse


def test_version_is_exposed() -> None:
    assert isinstance(viparse.__version__, str)
    assert viparse.__version__
