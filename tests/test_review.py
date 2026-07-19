from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from biofigure_lib.manifest import load_manifest, save_manifest
from biofigure_lib.project import init_project
from biofigure_lib.review import (
    apply_suggestions,
    approve_review,
    merge_groups,
    rename_group,
    render_numbered_review,
    split_group,
)


def make_project(tmp_path: Path) -> Path:
    source = tmp_path / "source.png"
    Image.new("RGB", (120, 80), "white").save(source)
    project = tmp_path / "project"
    init_project(project, "review", source, None, None, "#ffffff")
    return project


def candidate(group_id: str, bbox: list[int], kind: str = "biological-asset") -> dict:
    return {
        "id": group_id,
        "kind": kind,
        "label": group_id.rsplit(".", 1)[-1],
        "panel": "panel-a",
        "bbox": bbox,
        "z_index": 10,
        "visible": True,
        "editable": True,
        "background": "#ffffff",
        "tolerance": 12,
    }


def test_apply_suggestions_writes_overlay_and_report(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    added = apply_suggestions(project, [candidate("panel-a.cell", [10, 10, 20, 20])])
    assert added == ["panel-a.cell"]
    overlay = render_numbered_review(project)
    assert overlay.is_file()
    report = json.loads((project / "review/group-report.json").read_text(encoding="utf-8"))
    assert report[0]["id"] == "panel-a.cell"


def test_split_replaces_one_group_and_resets_approval(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    apply_suggestions(project, [candidate("panel-a.composite", [10, 10, 40, 20])])
    approve_review(project)
    split_group(
        project,
        "panel-a.composite",
        [candidate("panel-a.cell", [10, 10, 18, 20]), candidate("panel-a.nerve", [29, 10, 21, 20], "connector")],
    )
    data = load_manifest(project / "project.yaml")
    assert [group["id"] for group in data["groups"]] == ["panel-a.cell", "panel-a.nerve"]
    assert data["review"]["status"] == "draft"


def test_merge_uses_union_bbox_when_replacement_omits_bbox(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    apply_suggestions(project, [candidate("panel-a.one", [10, 10, 10, 10]), candidate("panel-a.two", [25, 12, 10, 12])])
    replacement = candidate("panel-a.merged", [0, 0, 1, 1])
    replacement.pop("bbox")
    merge_groups(project, ["panel-a.one", "panel-a.two"], replacement)
    merged = load_manifest(project / "project.yaml")["groups"][0]
    assert merged["bbox"] == [10, 10, 25, 14]


def test_rename_updates_connector_and_text_references(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    apply_suggestions(project, [candidate("panel-c.drg-old", [10, 10, 20, 20])])
    data = load_manifest(project / "project.yaml")
    data["connectors"] = [{"id": "panel-c.afferent", "from": "panel-c.drg-old", "to": "panel-c.gut", "path": "M10 10 L30 30"}]
    data["texts"] = [{"id": "panel-c.drg-label", "group": "panel-c.drg-old", "text": "DRG", "x": 10, "y": 10}]
    save_manifest(project / "project.yaml", data)
    rename_group(project, "panel-c.drg-old", "panel-c.drg")
    renamed = load_manifest(project / "project.yaml")
    assert renamed["connectors"][0]["from"] == "panel-c.drg"
    assert renamed["texts"][0]["group"] == "panel-c.drg"


def test_approve_records_current_manifest_hash(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    apply_suggestions(project, [candidate("panel-a.cell", [10, 10, 20, 20])])
    approve_review(project)
    data = load_manifest(project / "project.yaml")
    assert data["review"]["status"] == "approved"
    assert len(data["review"]["approved_manifest_sha256"]) == 64
