"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

_ENV_KEYS = (
    "VIPARSE_OUTPUT",
    "VIPARSE_ENCODING",
    "VIPARSE_OCR",
    "VIPARSE_NORMALIZE",
    "VIPARSE_MAX_BYTES",
)


@pytest.fixture(autouse=True)
def _isolate_viparse_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Make layered configuration deterministic for every test.

    ``load`` / ``load_batch`` / the CLI resolve their defaults from ``VIPARSE_*`` env vars and
    a ``viparse.toml`` in the working directory (SPEC-5 E5.4). Without isolation, a developer's
    stray env var or a repo-root config file could silently flip assertions in tests that rely
    on the built-in defaults. This clears those env vars and runs each test from a clean, empty
    working directory; tests that exercise layering set their own env / cwd, which stacks on top.
    """
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
