"""Guards for the packaging contract declared in ``pyproject.toml``.

These lock the promises SPEC-5 makes: a light ``core`` install, heavy engines behind
extras, and a working CLI entry point — so a future edit can't silently break them.
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


@lru_cache(maxsize=1)
def _project() -> dict[str, object]:
    with _PYPROJECT.open("rb") as fh:
        project: dict[str, object] = tomllib.load(fh)["project"]
    return project


def test_core_install_has_no_runtime_dependencies() -> None:
    # `pip install viparse` (core) must not pull any parser/OCR binaries.
    assert _project()["dependencies"] == []


def test_extras_isolate_heavy_engines() -> None:
    extras = _project()["optional-dependencies"]
    assert any("python-docx" in dep for dep in extras["office"])
    assert any("pytesseract" in dep for dep in extras["ocr"])


def test_all_extra_unions_the_engine_extras() -> None:
    # Order- and shape-tolerant: `all` must pull in both engine extras, however written.
    joined = " ".join(_project()["optional-dependencies"]["all"])
    assert "office" in joined
    assert "ocr" in joined


def test_cli_entry_point_is_declared() -> None:
    assert _project()["scripts"]["viparse"] == "viparse.cli:main"
