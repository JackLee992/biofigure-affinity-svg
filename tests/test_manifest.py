from __future__ import annotations

from pathlib import Path

import pytest

from biofigure_lib.errors import ManifestError
from biofigure_lib.manifest import load_manifest, save_manifest, validate_manifest
from biofigure_lib.project import init_project


def test_init_existing_image_creates_manifest(tmp_path: Path, sample_png: Path) -> None:
    manifest_path = init_project(tmp_path / "case", "case", sample_png, None, None, "#ffffff")
    data = load_manifest(manifest_path)
    assert data["schema_version"] == 1
    assert data["canvas"] == {"width": 32, "height": 24, "background": "#ffffff"}
    assert data["review"]["status"] == "draft"
    assert (tmp_path / "case/source/original.png").is_file()


def test_init_empty_canvas_requires_dimensions(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="width and height"):
        init_project(tmp_path / "case", "case", None, None, None, "#ffffff")


def test_duplicate_group_ids_are_rejected(valid_manifest: dict, tmp_path: Path) -> None:
    valid_manifest["groups"] = [
        {"id": "panel-a.cell", "kind": "biological-asset", "bbox": [0, 0, 4, 4]},
        {"id": "panel-a.cell", "kind": "biological-asset", "bbox": [5, 0, 4, 4]},
    ]
    with pytest.raises(ManifestError, match="duplicate group id"):
        validate_manifest(valid_manifest, tmp_path)


def test_out_of_bounds_group_is_rejected(valid_manifest: dict, tmp_path: Path) -> None:
    valid_manifest["groups"] = [
        {"id": "panel-a.cell", "kind": "biological-asset", "bbox": [30, 20, 8, 8]},
    ]
    with pytest.raises(ManifestError, match="outside canvas"):
        validate_manifest(valid_manifest, tmp_path)


def test_save_manifest_is_round_trippable(valid_manifest: dict, tmp_path: Path) -> None:
    path = tmp_path / "project.yaml"
    save_manifest(path, valid_manifest)
    assert load_manifest(path) == valid_manifest
