from __future__ import annotations

from pathlib import Path

from regression_sst_sstr import (
    _panel_for_point,
    _read_ocr,
    _semantic_alternatives,
    _stable_asset_id,
)


def test_regression_asset_ids_are_stable_and_semantic() -> None:
    assert _stable_asset_id("c-drg") == "panel-c.drg"
    assert _stable_asset_id("center-module-exact") == "center.module-exact"


def test_regression_panel_routing_covers_header_and_four_panels() -> None:
    assert _panel_for_point(100, 50)[0] == "header"
    assert _panel_for_point(100, 300)[0] == "panel-a"
    assert _panel_for_point(1000, 300)[0] == "panel-b"
    assert _panel_for_point(100, 800)[0] == "panel-c"
    assert _panel_for_point(1000, 800)[0] == "panel-d"


def test_ocr_reader_accepts_windows_utf8_bom_and_crlf(tmp_path: Path) -> None:
    ocr = tmp_path / "vision-lines.tsv"
    ocr.write_bytes(
        b"\xef\xbb\xbfindex\tx\ty\twidth\theight\tconfidence\ttext\r\n"
        b"1\t10\t20\t30\t40\t0.99\tDRG\r\n"
    )
    assert _read_ocr(ocr) == [{
        "index": 1,
        "x": 10,
        "y": 20,
        "width": 30,
        "height": 40,
        "confidence": 0.99,
        "text": "DRG",
    }]


def test_semantic_alternatives_preserve_bidirectional_arrows(tmp_path: Path) -> None:
    svg = tmp_path / "semantic.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg">
        <g id="a-connectors">
          <path id="a-link" d="M 1 2 L 3 4" stroke="#123456"
                stroke-width="2" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
        </g>
        <g id="b-connectors"/><g id="c-connectors"/><g id="d-connectors"/>
        <text id="a-label" x="20" y="200" font-size="12">DRG</text>
        </svg>""",
        encoding="utf-8",
    )
    texts, connectors = _semantic_alternatives(svg)
    assert texts[0]["text"] == "DRG"
    assert connectors[0]["arrow_start"] is True
    assert connectors[0]["arrow_end"] is True
    assert connectors[0]["group"] == "panel-a.connectors"
