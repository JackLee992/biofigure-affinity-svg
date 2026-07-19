from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from biofigure_lib.assets import extract_project, replace_group_asset
from biofigure_lib.errors import ManifestError
from biofigure_lib.manifest import load_manifest
from biofigure_lib.project import init_project
from biofigure_lib.review import apply_suggestions, approve_review
from biofigure_lib.state import load_build_state


def make_group(group_id: str, bbox: list[int], z_index: int = 10) -> dict:
    return {
        "id": group_id,
        "kind": "biological-asset",
        "label": group_id,
        "panel": "panel-a",
        "bbox": bbox,
        "z_index": z_index,
        "background": "#ffffff",
        "tolerance": 8,
    }


def make_project(tmp_path: Path, two_groups: bool = False, approved: bool = True) -> Path:
    source = tmp_path / "source.png"
    image = Image.new("RGBA", (40, 30), "white")
    for x in range(8, 18):
        for y in range(6, 16):
            image.putpixel((x, y), (130, 70, 170, 255))
    if two_groups:
        for x in range(24, 32):
            for y in range(8, 18):
                image.putpixel((x, y), (30, 140, 80, 255))
    image.save(source)
    project = tmp_path / "project"
    init_project(project, "assets", source, None, None, "#ffffff")
    groups = [make_group("panel-a.cell", [6, 4, 14, 14])]
    if two_groups:
        groups.append(make_group("panel-a.nerve", [22, 6, 12, 14], 11))
    apply_suggestions(project, groups)
    if approved:
        approve_review(project)
    return project


def test_extract_writes_exact_clean_and_punched_base(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    rebuilt = extract_project(project)
    assert rebuilt == ["panel-a.cell"]
    exact = project / "build/exact/panel-a.cell.png"
    clean = project / "groups/clean/panel-a.cell.png"
    base = project / "build/base.png"
    assert exact.is_file() and clean.is_file() and base.is_file()
    assert Image.open(exact).size == (14, 14)
    assert Image.open(clean).getpixel((0, 0))[3] == 0
    assert Image.open(clean).getpixel((5, 5))[3] == 255
    assert Image.open(base).getpixel((10, 10))[3] == 0


def test_release_extract_rejects_unapproved_manifest(tmp_path: Path) -> None:
    project = make_project(tmp_path, approved=False)
    with pytest.raises(ManifestError, match="approved"):
        extract_project(project)


def test_reextract_unchanged_project_reports_no_rebuilt_groups(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    extract_project(project)
    assert extract_project(project) == []


def test_replace_rebuilds_only_target_group(tmp_path: Path) -> None:
    project = make_project(tmp_path, two_groups=True)
    extract_project(project)
    replacement = tmp_path / "replacement.png"
    Image.new("RGBA", (14, 14), (220, 30, 70, 255)).save(replacement)
    rebuilt = replace_group_asset(project, "panel-a.cell", replacement, "red cell")
    assert rebuilt == ["panel-a.cell"]
    data = load_manifest(project / "project.yaml")
    cell = next(group for group in data["groups"] if group["id"] == "panel-a.cell")
    assert cell["generation"]["prompt"] == "red cell"
    assert cell["asset"] == "groups/generated/panel-a.cell.png"
    assert (project / cell["asset"]).is_file()
    assert Image.open(project / cell["exact_crop"]).getpixel((5, 5))[:3] == (220, 30, 70)
    state = load_build_state(project)
    assert "panel-a.cell" in state["groups"]
    assert "panel-a.nerve" in state["groups"]
