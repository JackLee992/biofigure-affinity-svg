from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .errors import ManifestError


SCHEMA_VERSION = 1
VALID_KINDS = {"panel", "background", "biological-asset", "connector", "text", "reference"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]*$")


def load_manifest(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise ManifestError(f"manifest not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a mapping")
    validate_manifest(data, path.parent)
    return data


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    path = Path(path)
    validate_manifest(data, path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def manifest_sha256(data: dict[str, Any]) -> str:
    normalized = json.loads(json.dumps(data, ensure_ascii=False))
    normalized.setdefault("review", {})["approved_manifest_sha256"] = None
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_manifest(data: dict[str, Any], project_dir: Path) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"schema_version must be {SCHEMA_VERSION}")
    project = data.get("project")
    if not isinstance(project, dict) or not str(project.get("name", "")).strip():
        raise ManifestError("project.name is required")
    canvas = data.get("canvas")
    if not isinstance(canvas, dict):
        raise ManifestError("canvas must be a mapping")
    width = _positive_int(canvas.get("width"), "canvas.width")
    height = _positive_int(canvas.get("height"), "canvas.height")
    background = canvas.get("background")
    if not isinstance(background, str) or not background:
        raise ManifestError("canvas.background is required")

    review = data.get("review")
    if not isinstance(review, dict) or review.get("status") not in {"draft", "approved"}:
        raise ManifestError("review.status must be draft or approved")
    if not isinstance(review.get("revision"), int) or review["revision"] < 0:
        raise ManifestError("review.revision must be a non-negative integer")

    groups = data.get("groups")
    if not isinstance(groups, list):
        raise ManifestError("groups must be a list")
    seen: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            raise ManifestError("each group must be a mapping")
        group_id = group.get("id")
        if not isinstance(group_id, str) or not ID_PATTERN.fullmatch(group_id):
            raise ManifestError(f"invalid group id: {group_id}")
        if group_id in seen:
            raise ManifestError(f"duplicate group id: {group_id}")
        seen.add(group_id)
        kind = group.get("kind")
        if kind not in VALID_KINDS:
            raise ManifestError(f"invalid kind for {group_id}: {kind}")
        x, y, box_width, box_height = _bbox(group.get("bbox"), group_id)
        if x + box_width > width or y + box_height > height:
            raise ManifestError(f"group {group_id} is outside canvas")
        if "z_index" in group and not isinstance(group["z_index"], int):
            raise ManifestError(f"z_index for {group_id} must be an integer")

    for collection in ("texts", "connectors"):
        if not isinstance(data.get(collection), list):
            raise ManifestError(f"{collection} must be a list")


def _positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ManifestError(f"{field} must be a positive integer")
    return value


def _bbox(value: Any, group_id: str) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4:
        raise ManifestError(f"bbox for {group_id} must contain four integers")
    if any(not isinstance(item, int) or isinstance(item, bool) for item in value):
        raise ManifestError(f"bbox for {group_id} must contain four integers")
    x, y, width, height = value
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ManifestError(f"bbox for {group_id} has invalid geometry")
    return x, y, width, height
