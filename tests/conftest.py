from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    path = tmp_path / "sample.png"
    image = Image.new("RGB", (32, 24), "#f7f8fc")
    for x in range(8, 18):
        for y in range(6, 16):
            image.putpixel((x, y), (132, 75, 168))
    image.save(path)
    return path


@pytest.fixture
def valid_manifest() -> dict:
    return {
        "schema_version": 1,
        "project": {"name": "case"},
        "canvas": {"width": 32, "height": 24, "background": "#f7f8fc"},
        "source": {"image": "source/original.png", "references": []},
        "style": {"prompt": None, "references": []},
        "review": {"status": "draft", "revision": 0, "approved_manifest_sha256": None},
        "groups": [],
        "texts": [],
        "connectors": [],
        "qa": {"require_pixel_match": True, "rmse_threshold": 0.0},
    }
