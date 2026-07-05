"""Golden-output snapshot tests (SPEC-6 E6.4).

Canonical synthetic fixtures (built deterministically per run) are rendered to markdown and
JSON and compared against committed golden files, so any unintended change to the RAG-ready
output shape fails loudly. To review and accept an intended change, regenerate the goldens
with ``VIPARSE_UPDATE_SNAPSHOTS=1 pytest tests/test_golden_snapshots.py`` and inspect the diff
before committing.

The fixtures' bytes need not be reproducible (Office/PDF writers embed timestamps); only the
*extracted output* is snapshotted, and the one path-dependent JSON field (``source``) is reset
to a placeholder by re-parsing the JSON — never a fragile path substring replace, which would
miss on Windows where paths are backslash-escaped.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from viparse import load

_GOLDEN = Path(__file__).parent / "golden"
_SOURCE_PLACEHOLDER = "<fixture>"


def _basic_docx(path: Path) -> Path:
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_heading("Báo cáo", level=1)
    document.add_paragraph("Nội dung chính.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Tên"
    table.cell(0, 1).text = "Tuổi"
    table.cell(1, 0).text = "An"
    table.cell(1, 1).text = "30"
    document.save(str(path))
    return path


def _legacy_docx(path: Path) -> Path:
    # TCVN3 surface bytes under a .VnTime font — exercises the moat end to end.
    docx = pytest.importorskip("docx")
    document = docx.Document()
    run = document.add_paragraph().add_run("µ¸¶·¹")
    run.font.name = ".VnTime"
    document.save(str(path))
    return path


def _basic_xlsx(path: Path) -> Path:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Nhân viên"
    ws.append(["Tên", "Điểm"])
    ws.append(["Bình", 9])
    wb.save(str(path))
    return path


def _basic_pdf(path: Path) -> Path:
    pytest.importorskip("pdfplumber")  # the engine's reader
    pytest.importorskip("reportlab")  # the fixture writer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    grid = TableStyle([("GRID", (0, 0), (-1, -1), 1, colors.black)])
    SimpleDocTemplate(str(path)).build(
        [
            Paragraph("Report body paragraph.", styles["Normal"]),
            Spacer(1, 12),
            Table([["Name", "Age"], ["An", "30"]], style=grid),
        ]
    )
    return path


_FIXTURES = {
    "docx_basic": (_basic_docx, "a.docx"),
    "docx_legacy": (_legacy_docx, "legacy.docx"),
    "xlsx_basic": (_basic_xlsx, "a.xlsx"),
    "pdf_basic": (_basic_pdf, "a.pdf"),
}


def _stabilize(text: str, fmt: str) -> str:
    """Normalize the one environment-dependent field (the JSON ``source`` path)."""
    if fmt != "json":
        return text
    payload = json.loads(text)
    payload["source"] = _SOURCE_PLACEHOLDER
    # Same dump options as the renderer, so this round-trips its formatting exactly.
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _check(name: str, generated: str) -> None:
    golden = _GOLDEN / name
    if os.environ.get("VIPARSE_UPDATE_SNAPSHOTS"):  # pragma: no cover - dev-only regeneration
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(generated, encoding="utf-8")
        return
    expected = golden.read_text(encoding="utf-8")
    assert generated == expected, (
        f"snapshot drift in {name} — regenerate with VIPARSE_UPDATE_SNAPSHOTS=1 and review the diff"
    )


@pytest.mark.parametrize("fixture", sorted(_FIXTURES))
def test_output_matches_golden(fixture: str, tmp_path: Path) -> None:
    build, filename = _FIXTURES[fixture]
    path = build(tmp_path / filename)  # build the fixture once, snapshot both formats
    for fmt, suffix in (("markdown", "md"), ("json", "json")):
        _check(f"{fixture}.{suffix}", _stabilize(load(path, output=fmt)[0].text, fmt))
