"""Guards for the packaging contract declared in ``pyproject.toml``.

These lock the promises SPEC-5 makes: a light ``core`` install, heavy engines behind
extras, and a working CLI entry point — so a future edit can't silently break them.
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _ROOT / "pyproject.toml"


@lru_cache(maxsize=1)
def _project() -> dict[str, object]:
    with _PYPROJECT.open("rb") as fh:
        project: dict[str, object] = tomllib.load(fh)["project"]
    return project


def test_release_docs_exist() -> None:
    # A releasable project ships a changelog and a security policy.
    assert (_ROOT / "CHANGELOG.md").is_file()
    assert (_ROOT / "SECURITY.md").is_file()


def test_dev_extra_includes_sbom_tool() -> None:
    assert any("cyclonedx" in dep for dep in _project()["optional-dependencies"]["dev"])


def test_core_install_has_no_runtime_dependencies() -> None:
    # `pip install viparse` (core) must not pull any parser/OCR binaries.
    assert _project()["dependencies"] == []


def test_extras_isolate_heavy_engines() -> None:
    extras = _project()["optional-dependencies"]
    assert any("python-docx" in dep for dep in extras["office"])
    assert any("pdfplumber" in dep for dep in extras["pdf"])
    assert any("pytesseract" in dep for dep in extras["ocr"])


def test_all_extra_unions_the_engine_extras() -> None:
    # Order- and shape-tolerant: `all` must pull in every engine extra, however written.
    joined = " ".join(_project()["optional-dependencies"]["all"])
    assert "office" in joined
    assert "pdf" in joined
    assert "ocr" in joined


def test_cli_entry_point_is_declared() -> None:
    assert _project()["scripts"]["viparse"] == "viparse.cli:main"
