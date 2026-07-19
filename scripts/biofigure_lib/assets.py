from __future__ import annotations

import shutil
from collections import deque
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageColor

from .errors import ManifestError
from .manifest import load_manifest, manifest_sha256, save_manifest
from .review import render_numbered_review
from .state import load_build_state, save_build_state, sha256_file, sha256_json


EXTRACTABLE_KINDS = {"biological-asset", "connector", "text"}


def extract_project(project_dir: Path, draft: bool = False) -> list[str]:
    project_dir = Path(project_dir)
    manifest_path = project_dir / "project.yaml"
    data = load_manifest(manifest_path)
    if not draft:
        _require_current_approval(data)

    source_path = _resolve(project_dir, data["source"]["image"])
    if not source_path.is_file():
        raise ManifestError(f"source image not found: {source_path}")
    source_hash = sha256_file(source_path)
    state = load_build_state(project_dir)
    previous_groups = state.get("groups", {})
    next_groups: dict[str, Any] = dict(previous_groups)
    rebuilt: list[str] = []

    with Image.open(source_path) as opened:
        source = opened.convert("RGBA")
    if source.size != (data["canvas"]["width"], data["canvas"]["height"]):
        raise ManifestError("source image dimensions do not match canvas")

    for group in _extractable_groups(data):
        group_id = group["id"]
        input_hash = _group_input_hash(project_dir, group, source_hash)
        exact_path = _resolve(project_dir, group.get("exact_crop", f"build/exact/{group_id}.png"))
        clean_path = _resolve(project_dir, group.get("asset", f"groups/clean/{group_id}.png"))
        previous = previous_groups.get(group_id, {})
        if previous.get("input_sha256") == input_hash and exact_path.is_file() and clean_path.is_file():
            continue

        x, y, width, height = group["bbox"]
        crop = source.crop((x, y, x + width, y + height))
        exact_path.parent.mkdir(parents=True, exist_ok=True)

        registered_asset = group.get("asset")
        if registered_asset and registered_asset.startswith("groups/generated/"):
            generated = _resolve(project_dir, registered_asset)
            if not generated.is_file():
                raise ManifestError(f"generated asset not found for {group_id}: {generated}")
            clean_output = generated
            with Image.open(generated) as opened:
                opened.convert("RGBA").save(exact_path)
        else:
            crop.save(exact_path)
            clean_output = project_dir / f"groups/clean/{group_id}.png"
            clean_output.parent.mkdir(parents=True, exist_ok=True)
            _remove_edge_background(
                crop,
                clean_output,
                group.get("background", data["canvas"]["background"]),
                int(group.get("tolerance", 12)),
            )
            group["asset"] = clean_output.relative_to(project_dir).as_posix()
        group["exact_crop"] = exact_path.relative_to(project_dir).as_posix()
        next_groups[group_id] = {
            "input_sha256": input_hash,
            "exact_sha256": sha256_file(exact_path),
            "asset_sha256": sha256_file(clean_output),
        }
        rebuilt.append(group_id)

    base_path = project_dir / "build/base.png"
    if rebuilt or not base_path.is_file():
        _write_punched_base(source, _extractable_groups(data), base_path)

    state = {
        "manifest_sha256": manifest_sha256(data),
        "source_sha256": source_hash,
        "groups": next_groups,
        "last_command": "extract",
    }
    save_manifest(manifest_path, data)
    save_build_state(project_dir, state)
    return rebuilt


def replace_group_asset(
    project_dir: Path,
    group_id: str,
    asset_path: Path,
    prompt: Optional[str],
) -> list[str]:
    project_dir = Path(project_dir)
    asset_path = Path(asset_path)
    if not asset_path.is_file():
        raise ManifestError(f"replacement asset not found: {asset_path}")
    manifest_path = project_dir / "project.yaml"
    data = load_manifest(manifest_path)
    group = next((item for item in data["groups"] if item["id"] == group_id), None)
    if group is None:
        raise ManifestError(f"group not found: {group_id}")
    _, _, width, height = group["bbox"]
    destination = project_dir / f"groups/generated/{group_id}.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".png.tmp")
    with Image.open(asset_path) as opened:
        normalized = opened.convert("RGBA")
        if normalized.size != (width, height):
            normalized = normalized.resize((width, height), Image.Resampling.LANCZOS)
        normalized.save(temporary, format="PNG")
    temporary.replace(destination)
    group["asset"] = destination.relative_to(project_dir).as_posix()
    generation = dict(group.get("generation") or {})
    generation["prompt"] = prompt
    generation.setdefault("style_refs", [])
    group["generation"] = generation
    data["review"]["status"] = "draft"
    data["review"]["revision"] += 1
    data["review"]["approved_manifest_sha256"] = None
    save_manifest(manifest_path, data)
    render_numbered_review(project_dir)
    rebuilt = extract_project(project_dir, draft=True)
    return [group_id] if group_id in rebuilt else []


def _require_current_approval(data: dict[str, Any]) -> None:
    review = data["review"]
    approved_hash = review.get("approved_manifest_sha256")
    if review.get("status") != "approved" or not approved_hash:
        raise ManifestError("manifest review must be approved before release extraction")
    if approved_hash != manifest_sha256(data):
        raise ManifestError("approved manifest hash is stale")


def _extractable_groups(data: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (group for group in data["groups"] if group["kind"] in EXTRACTABLE_KINDS),
        key=lambda group: (group.get("z_index", 0), group["id"]),
    )


def _group_input_hash(project_dir: Path, group: dict[str, Any], source_hash: str) -> str:
    payload = {"group": group, "source_sha256": source_hash}
    asset = group.get("asset")
    if asset and asset.startswith("groups/generated/"):
        asset_path = _resolve(project_dir, asset)
        payload["registered_asset_sha256"] = sha256_file(asset_path) if asset_path.is_file() else None
    return sha256_json(payload)


def _write_punched_base(source: Image.Image, groups: list[dict[str, Any]], output: Path) -> None:
    base = source.copy()
    alpha = base.getchannel("A")
    overlap = 2
    for group in groups:
        x, y, width, height = group["bbox"]
        left = x + overlap
        top = y + overlap
        right = x + width - overlap
        bottom = y + height - overlap
        if right > left and bottom > top:
            alpha.paste(0, (left, top, right, bottom))
    base.putalpha(alpha)
    output.parent.mkdir(parents=True, exist_ok=True)
    base.save(output)


def _remove_edge_background(image: Image.Image, output: Path, background: str, tolerance: int) -> None:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    target = ImageColor.getrgb(background)
    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()
    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        red, green, blue, _ = pixels[x, y]
        if max(abs(red - target[0]), abs(green - target[1]), abs(blue - target[2])) > tolerance:
            continue
        pixels[x, y] = (red, green, blue, 0)
        if x > 0:
            queue.append((x - 1, y))
        if x + 1 < width:
            queue.append((x + 1, y))
        if y > 0:
            queue.append((x, y - 1))
        if y + 1 < height:
            queue.append((x, y + 1))
    rgba.save(output)


def _resolve(project_dir: Path, relative: str) -> Path:
    return project_dir / Path(*relative.split("/"))
