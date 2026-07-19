from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw

from .errors import ManifestError
from .manifest import load_manifest, manifest_sha256, save_manifest


KIND_COLORS = {
    "panel": "#808080",
    "background": "#555555",
    "biological-asset": "#0077cc",
    "connector": "#e67e22",
    "text": "#8e44ad",
    "reference": "#16a085",
}


def apply_suggestions(project_dir: Path, candidates: list[dict[str, Any]]) -> list[str]:
    data, path = _load(project_dir)
    existing = {group["id"] for group in data["groups"]}
    added: list[str] = []
    for candidate in candidates:
        group = _normalize_group(candidate)
        if group["id"] in existing:
            raise ManifestError(f"duplicate group id: {group['id']}")
        data["groups"].append(group)
        existing.add(group["id"])
        added.append(group["id"])
    _mark_draft(data)
    save_manifest(path, data)
    render_numbered_review(project_dir)
    return added


def split_group(project_dir: Path, source_id: str, replacements: list[dict[str, Any]]) -> None:
    if len(replacements) < 2:
        raise ManifestError("split requires at least two replacement groups")
    data, path = _load(project_dir)
    index = _group_index(data, source_id)
    normalized = [_normalize_group(group) for group in replacements]
    data["groups"][index:index + 1] = normalized
    _replace_references(data, source_id, None)
    _mark_draft(data)
    save_manifest(path, data)
    render_numbered_review(project_dir)


def merge_groups(project_dir: Path, source_ids: list[str], replacement: dict[str, Any]) -> None:
    if len(source_ids) < 2:
        raise ManifestError("merge requires at least two source groups")
    data, path = _load(project_dir)
    unique_ids = list(dict.fromkeys(source_ids))
    indexes = [_group_index(data, group_id) for group_id in unique_ids]
    source_groups = [data["groups"][index] for index in indexes]
    merged = dict(replacement)
    if "bbox" not in merged:
        merged["bbox"] = _union_bbox(group["bbox"] for group in source_groups)
    merged = _normalize_group(merged)
    insert_at = min(indexes)
    data["groups"] = [group for group in data["groups"] if group["id"] not in set(unique_ids)]
    data["groups"].insert(insert_at, merged)
    for source_id in unique_ids:
        _replace_references(data, source_id, merged["id"])
    _mark_draft(data)
    save_manifest(path, data)
    render_numbered_review(project_dir)


def rename_group(project_dir: Path, old_id: str, new_id: str) -> None:
    data, path = _load(project_dir)
    index = _group_index(data, old_id)
    if any(group["id"] == new_id for group in data["groups"]):
        raise ManifestError(f"duplicate group id: {new_id}")
    data["groups"][index]["id"] = new_id
    _replace_references(data, old_id, new_id)
    _mark_draft(data)
    save_manifest(path, data)
    render_numbered_review(project_dir)


def approve_review(project_dir: Path) -> None:
    data, path = _load(project_dir)
    data["review"]["status"] = "approved"
    data["review"]["approved_manifest_sha256"] = None
    data["review"]["approved_manifest_sha256"] = manifest_sha256(data)
    save_manifest(path, data)


def render_numbered_review(project_dir: Path) -> Path:
    project_dir = Path(project_dir)
    data = load_manifest(project_dir / "project.yaml")
    source = project_dir / data["source"]["image"]
    with Image.open(source) as input_image:
        image = input_image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    report: list[dict[str, Any]] = []
    for index, group in enumerate(data["groups"], start=1):
        x, y, width, height = group["bbox"]
        color = KIND_COLORS.get(group["kind"], "#ff0000")
        draw.rectangle((x, y, x + width - 1, y + height - 1), outline=color, width=2)
        label = f"{index:02d}"
        label_box = draw.textbbox((x, y), label)
        label_width = label_box[2] - label_box[0] + 6
        label_height = label_box[3] - label_box[1] + 4
        draw.rectangle((x, y, x + label_width, y + label_height), fill=color)
        draw.text((x + 3, y + 1), label, fill="white")
        report.append({
            "index": index,
            "id": group["id"],
            "kind": group["kind"],
            "label": group.get("label", group["id"]),
            "panel": group.get("panel"),
            "bbox": group["bbox"],
        })
    review_dir = project_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    overlay = review_dir / "numbered.png"
    image.save(overlay)
    (review_dir / "group-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return overlay


def _load(project_dir: Path) -> tuple[dict[str, Any], Path]:
    path = Path(project_dir) / "project.yaml"
    return load_manifest(path), path


def _mark_draft(data: dict[str, Any]) -> None:
    data["review"]["revision"] += 1
    data["review"]["status"] = "draft"
    data["review"]["approved_manifest_sha256"] = None


def _group_index(data: dict[str, Any], group_id: str) -> int:
    for index, group in enumerate(data["groups"]):
        if group["id"] == group_id:
            return index
    raise ManifestError(f"group not found: {group_id}")


def _normalize_group(candidate: dict[str, Any]) -> dict[str, Any]:
    group = dict(candidate)
    group.setdefault("label", group.get("id", ""))
    group.setdefault("panel", None)
    group.setdefault("z_index", 0)
    group.setdefault("visible", True)
    group.setdefault("editable", True)
    group.setdefault("background", "#ffffff")
    group.setdefault("tolerance", 12)
    group.setdefault("source", "source/original.png")
    group.setdefault("asset", f"groups/clean/{group.get('id', 'group')}.png")
    group.setdefault("exact_crop", f"build/exact/{group.get('id', 'group')}.png")
    group.setdefault("generation", {"prompt": None, "style_refs": []})
    return group


def _replace_references(data: dict[str, Any], old_id: str, new_id: Any) -> None:
    keys = ("from", "to", "group", "parent")
    for collection in (data.get("texts", []), data.get("connectors", []), data.get("groups", [])):
        for item in collection:
            for key in keys:
                if item.get(key) == old_id:
                    item[key] = new_id
            if isinstance(item.get("dependencies"), list):
                item["dependencies"] = [new_id if value == old_id else value for value in item["dependencies"] if value != old_id or new_id is not None]


def _union_bbox(boxes: Iterable[list[int]]) -> list[int]:
    materialized = list(boxes)
    min_x = min(box[0] for box in materialized)
    min_y = min(box[1] for box in materialized)
    max_x = max(box[0] + box[2] for box in materialized)
    max_y = max(box[1] + box[3] for box in materialized)
    return [min_x, min_y, max_x - min_x, max_y - min_y]
