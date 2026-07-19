from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .errors import ManifestError
from .manifest import load_manifest, manifest_sha256


SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
FONT_FAMILY = "Arial,'Microsoft YaHei','PingFang SC','Hiragino Sans GB',sans-serif"
LAYER_LABELS = [
    "00-background",
    "01-exact-base",
    "10-exact-assets",
    "20-exact-connectors",
    "30-exact-text",
    "40-live-text",
    "50-vector-connectors",
    "60-clean-assets",
    "90-reference",
]


def compile_affinity_svg(project_dir: Path, draft: bool = False) -> Path:
    project_dir = Path(project_dir)
    data = load_manifest(project_dir / "project.yaml")
    if not draft:
        _require_approval(data)
    width = data["canvas"]["width"]
    height = data["canvas"]["height"]
    groups = sorted(data["groups"], key=lambda item: (item.get("z_index", 0), item["id"]))
    base = project_dir / "build/base.png"
    reference = _resolve(project_dir, data["source"]["image"])
    if not base.is_file():
        raise ManifestError("punched base is missing; run extract first")

    exact_assets = _exact_group_markup(project_dir, groups, "biological-asset")
    exact_connectors = _exact_group_markup(project_dir, groups, "connector")
    exact_text = _exact_group_markup(project_dir, groups, "text")
    clean_assets = _clean_group_markup(project_dir, groups)
    live_text = "\n".join(_live_text_markup(item) for item in data["texts"])
    vector_connectors = "\n".join(_connector_markup(item) for item in data["connectors"])

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="{SVG_NS}" xmlns:inkscape="{INKSCAPE_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <title>{_esc(data["project"]["name"])}</title>
  <desc>Manifest-driven dual-state biomedical figure for Affinity</desc>
  <defs>
    <marker id="bio-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L8,4 L0,8 z" fill="context-stroke"/>
    </marker>
  </defs>
  {_layer("layer-background", LAYER_LABELS[0], _background_markup(width, height, data["canvas"]["background"]))}
  {_layer("layer-exact-base", LAYER_LABELS[1], _image_markup("exact-base-image", base, 0, 0, width, height))}
  {_layer("layer-exact-assets", LAYER_LABELS[2], exact_assets)}
  {_layer("layer-exact-connectors", LAYER_LABELS[3], exact_connectors)}
  {_layer("layer-exact-text", LAYER_LABELS[4], exact_text)}
  {_layer("layer-live-text", LAYER_LABELS[5], live_text, hidden=True)}
  {_layer("layer-vector-connectors", LAYER_LABELS[6], vector_connectors, hidden=True)}
  {_layer("layer-clean-assets", LAYER_LABELS[7], clean_assets, hidden=True)}
  {_layer("layer-reference", LAYER_LABELS[8], _image_markup("reference-original", reference, 0, 0, width, height), hidden=True)}
</svg>
'''
    output = project_dir / "exports/affinity.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".svg.tmp")
    temporary.write_text(svg, encoding="utf-8")
    try:
        ET.parse(temporary)
    except ET.ParseError as exc:
        raise ManifestError(f"compiled SVG is invalid: {exc}") from exc
    temporary.replace(output)
    return output


def _layer(layer_id: str, label: str, body: str, hidden: bool = False) -> str:
    style = ' style="display:none"' if hidden else ""
    return f'<g id="{layer_id}" inkscape:groupmode="layer" inkscape:label="{_esc(label)}"{style}>\n{body}\n</g>'


def _background_markup(width: int, height: int, background: str) -> str:
    return f'<rect id="clean-canvas" x="0" y="0" width="{width}" height="{height}" fill="{_esc(background)}"/>'


def _exact_group_markup(project_dir: Path, groups: list[dict[str, Any]], kind: str) -> str:
    markup: list[str] = []
    for group in groups:
        if group["kind"] != kind:
            continue
        exact = _resolve(project_dir, group.get("exact_crop", f"build/exact/{group['id']}.png"))
        if not exact.is_file():
            raise ManifestError(f"exact crop missing for {group['id']}: {exact}")
        x, y, width, height = group["bbox"]
        image = _image_markup(f"exact-image-{group['id']}", exact, x, y, width, height)
        markup.append(
            f'<g id="exact-{_esc(group["id"])}" inkscape:label="{_esc(group.get("label", group["id"]))}" data-role="exact-{kind}">\n{image}\n</g>'
        )
    return "\n".join(markup)


def _clean_group_markup(project_dir: Path, groups: list[dict[str, Any]]) -> str:
    markup: list[str] = []
    for group in groups:
        if group["kind"] != "biological-asset":
            continue
        asset = _resolve(project_dir, group.get("asset", f"groups/clean/{group['id']}.png"))
        if not asset.is_file():
            raise ManifestError(f"clean asset missing for {group['id']}: {asset}")
        x, y, width, height = group["bbox"]
        image = _image_markup(f"clean-image-{group['id']}", asset, x, y, width, height)
        markup.append(
            f'<g id="clean-{_esc(group["id"])}" inkscape:label="{_esc(group.get("label", group["id"]))}" data-role="clean-biological-asset">\n{image}\n</g>'
        )
    return "\n".join(markup)


def _live_text_markup(item: dict[str, Any]) -> str:
    attributes = {
        "id": item["id"],
        "x": item.get("x", 0),
        "y": item.get("y", 0),
        "font-family": FONT_FAMILY,
        "font-size": item.get("font_size", 16),
        "font-weight": item.get("font_weight", 400),
        "fill": item.get("fill", "#222222"),
        "text-anchor": item.get("text_anchor", "start"),
    }
    rendered = " ".join(f'{key}="{_esc(value)}"' for key, value in attributes.items())
    return f'<text {rendered} data-group="{_esc(item.get("group", ""))}">{_esc(item.get("text", ""))}</text>'


def _connector_markup(item: dict[str, Any]) -> str:
    dash = item.get("dash")
    dash_attribute = f' stroke-dasharray="{_esc(dash)}"' if dash else ""
    marker_start = ' marker-start="url(#bio-arrow)"' if item.get("arrow_start", False) else ""
    marker_end = ' marker-end="url(#bio-arrow)"' if item.get("arrow_end", True) else ""
    return (
        f'<path id="{_esc(item["id"])}" d="{_esc(item["path"])}" fill="none" '
        f'stroke="{_esc(item.get("stroke", "#333333"))}" stroke-width="{_esc(item.get("stroke_width", 2))}"'
        f'{dash_attribute}{marker_start}{marker_end} data-group="{_esc(item.get("group", ""))}"/>'
    )


def _image_markup(image_id: str, path: Path, x: int, y: int, width: int, height: int) -> str:
    return (
        f'<image id="{_esc(image_id)}" x="{x}" y="{y}" width="{width}" height="{height}" '
        f'preserveAspectRatio="none" href="{_data_uri(path)}"/>'
    )


def _data_uri(path: Path) -> str:
    encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _resolve(project_dir: Path, relative: str) -> Path:
    return Path(project_dir) / Path(*relative.split("/"))


def _require_approval(data: dict[str, Any]) -> None:
    review = data["review"]
    if review.get("status") != "approved" or not review.get("approved_manifest_sha256"):
        raise ManifestError("manifest review must be approved before release compile")
    if review["approved_manifest_sha256"] != manifest_sha256(data):
        raise ManifestError("approved manifest hash is stale")


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)
