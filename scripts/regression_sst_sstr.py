#!/usr/bin/env python3
"""Build the original SST/SSTR figure through the generic skill pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional, Union
from xml.etree import ElementTree as ET

from biofigure_lib.assets import extract_project
from biofigure_lib.manifest import load_manifest, save_manifest
from biofigure_lib.project import init_project
from biofigure_lib.qa import run_qa
from biofigure_lib.render import render_svg
from biofigure_lib.review import apply_suggestions, approve_review
from biofigure_lib.svg import compile_affinity_svg


SVG_NS = "http://www.w3.org/2000/svg"
USED_ASSET_IDS = (
    "a-nerve-injury", "a-drg", "a-spinal-cord", "a-brain-s1", "a-brain-mpfc",
    "a-brain-bla", "a-brain-pag-rvm", "a-sst-module-exact",
    "b-skin-needle", "b-mediator-axon", "b-spinal-cord", "b-macrophage",
    "b-microglia", "b-sst-module-exact",
    "c-gut", "c-epithelium", "c-brain", "c-drg", "c-spinal-cord",
    "c-gut-peptides-exact", "c-peptide-module-exact",
    "d-bone-tumor", "d-microenvironment", "d-spinal-cord", "d-brain",
    "d-sst-module-exact", "center-module-exact",
)
CONNECTOR_GROUPS = (
    ("a-connectors", "panel-a.connectors", [76, 214, 600, 238], "#f7f8fc"),
    ("b-connectors", "panel-b.connectors", [1003, 337, 292, 151], "#fdf7f7"),
    ("c-connectors", "panel-c.connectors", [168, 642, 456, 298], "#f7f9f7"),
    ("d-connectors", "panel-d.connectors", [880, 624, 548, 388], "#faf8fc"),
)
REQUIRED_GROUPS = {
    "panel-c.gut",
    "panel-c.epithelium",
    "panel-c.brain",
    "panel-c.drg",
    "panel-c.spinal-cord",
    "panel-c.gut-peptides-exact",
    "panel-c.peptide-module-exact",
    "panel-c.connectors",
    "panel-d.bone-tumor",
    "panel-d.microenvironment",
    "panel-d.spinal-cord",
    "panel-d.brain",
    "panel-d.sst-module-exact",
    "panel-d.connectors",
}
REQUIRED_CONNECTORS = {
    "c-gut-to-drg-afferent",
    "c-epithelium-to-drg-afferent",
    "c-drg-to-spinal-cord",
    "c-brain-gut-axis-left",
    "c-brain-gut-axis-right",
    "c-peptide-to-cord-center",
    "c-peptide-to-cord-left",
    "c-peptide-to-cord-right",
    "d-bone-to-microenvironment",
    "d-microenvironment-to-cord",
    "d-cord-to-brain",
    "d-brain-to-sst",
    "d-cord-to-sst-short",
}


def build_regression(
    source: Path,
    legacy_root: Path,
    project: Path,
    browser: Optional[Path] = None,
) -> dict[str, Any]:
    source = Path(source)
    legacy_root = Path(legacy_root)
    project = Path(project)
    asset_manifest = _read_json(legacy_root / "semantic/asset-manifest.json")
    assets_by_id = {item["id"]: item for item in asset_manifest["assets"]}
    semantic_svg = legacy_root / "exports/SST-SSTR-semantic-layered.svg"
    ocr_path = legacy_root / "ocr/vision-lines.tsv"

    init_project(project, "sst-sstr-real-regression", source, None, None, "#ffffff")
    candidates: list[dict[str, Any]] = []
    for z_index, asset_id in enumerate(USED_ASSET_IDS, start=100):
        item = assets_by_id[asset_id]
        stable_id = _stable_asset_id(asset_id)
        candidates.append({
            "id": stable_id,
            "kind": "biological-asset",
            "label": item["alt"],
            "panel": _panel_name(item["panel"]),
            "bbox": item["crop"],
            "z_index": z_index,
            "background": item.get("background", "#ffffff").lower(),
            "tolerance": int(item.get("fuzz", 8)),
        })
    for z_index, (_legacy_id, stable_id, box, background) in enumerate(CONNECTOR_GROUPS, start=200):
        candidates.append({
            "id": stable_id,
            "kind": "connector",
            "label": f"{stable_id} exact arrows and nerves",
            "panel": stable_id.split(".", 1)[0],
            "bbox": box,
            "z_index": z_index,
            "background": background,
            "tolerance": 8,
        })
    ocr_lines = _read_ocr(ocr_path)
    for item in ocr_lines:
        x, y, width, height = _padded_box(item, 1448, 1086)
        panel, background = _panel_for_point(x + width / 2, y + height / 2)
        candidates.append({
            "id": f"text.{item['index']:02d}",
            "kind": "text",
            "label": item["text"],
            "panel": panel,
            "bbox": [x, y, width, height],
            "z_index": 300 + item["index"],
            "background": background,
            "tolerance": 8,
        })

    apply_suggestions(project, candidates)
    live_texts, connectors = _semantic_alternatives(semantic_svg)
    manifest_path = project / "project.yaml"
    data = load_manifest(manifest_path)
    data["texts"] = live_texts
    data["connectors"] = connectors
    data["style"]["prompt"] = "Original SST/SSTR biomedical mechanism figure regression"
    save_manifest(manifest_path, data)
    approve_review(project)
    rebuilt = extract_project(project)
    svg = compile_affinity_svg(project)
    preview = render_svg(project, browser)
    qa_report = run_qa(project)

    group_ids = {item["id"] for item in load_manifest(manifest_path)["groups"]}
    connector_ids = {item["id"] for item in connectors}
    missing_groups = sorted(REQUIRED_GROUPS - group_ids)
    missing_connectors = sorted(REQUIRED_CONNECTORS - connector_ids)
    report = {
        "project": str(project.resolve()),
        "svg": str(svg.resolve()),
        "preview": str(preview.resolve()),
        "groups": len(group_ids),
        "asset_groups": len(USED_ASSET_IDS),
        "connector_groups": len(CONNECTOR_GROUPS),
        "text_groups": len(ocr_lines),
        "live_texts": len(live_texts),
        "vector_connectors": len(connectors),
        "rebuilt": len(rebuilt),
        "required_groups_present": not missing_groups,
        "required_connectors_present": not missing_connectors,
        "missing_groups": missing_groups,
        "missing_connectors": missing_connectors,
        "qa": qa_report,
    }
    if missing_groups or missing_connectors:
        raise RuntimeError(f"semantic completeness failed: {report}")
    output = project / "review/sst-sstr-regression.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _stable_asset_id(asset_id: str) -> str:
    prefix, suffix = asset_id.split("-", 1)
    return f"{'center' if prefix == 'center' else f'panel-{prefix}'}.{suffix}"


def _panel_name(value: str) -> str:
    lowered = value.lower()
    return "center" if lowered == "center" else f"panel-{lowered}"


def _read_ocr(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8-sig").strip().splitlines()[1:]
    result: list[dict[str, Any]] = []
    for line in lines:
        index, x, y, width, height, confidence, *text = line.split("\t")
        result.append({
            "index": int(index),
            "x": int(x),
            "y": int(y),
            "width": int(width),
            "height": int(height),
            "confidence": float(confidence),
            "text": "\t".join(text),
        })
    return result


def _padded_box(item: dict[str, Any], canvas_width: int, canvas_height: int) -> tuple[int, int, int, int]:
    pad = 2
    x = max(0, item["x"] - pad)
    y = max(0, item["y"] - pad)
    width = min(canvas_width - x, item["width"] + pad * 2)
    height = min(canvas_height - y, item["height"] + pad * 2)
    return x, y, width, height


def _panel_for_point(x: float, y: float) -> tuple[str, str]:
    if y < 95:
        return "header", "#ffffff"
    if y < 590:
        return ("panel-a", "#f7f8fc") if x < 724 else ("panel-b", "#fdf7f7")
    return ("panel-c", "#f7f9f7") if x < 724 else ("panel-d", "#faf8fc")


def _semantic_alternatives(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = ET.parse(path).getroot()
    groups = {element.get("id"): element for element in root.iter() if element.get("id")}
    texts: list[dict[str, Any]] = []
    for element in root.iter(f"{{{SVG_NS}}}text"):
        text_id = element.get("id")
        if not text_id:
            continue
        x = _number(element.get("x"), 0)
        y = _number(element.get("y"), 0)
        panel, _background = _panel_for_point(float(x), float(y))
        texts.append({
            "id": text_id,
            "group": panel,
            "text": "".join(element.itertext()),
            "x": x,
            "y": y,
            "font_size": _number(element.get("font-size"), 16),
            "font_weight": _number(element.get("font-weight"), 400),
            "fill": element.get("fill", "#222222"),
            "text_anchor": element.get("text-anchor", "start"),
        })

    connectors: list[dict[str, Any]] = []
    stable_by_legacy = {legacy: stable for legacy, stable, _box, _background in CONNECTOR_GROUPS}
    for legacy_id, stable_group, _box, _background in CONNECTOR_GROUPS:
        group = groups.get(legacy_id)
        if group is None:
            raise RuntimeError(f"connector group missing from semantic SVG: {legacy_id}")
        for path_element in group.iter(f"{{{SVG_NS}}}path"):
            path_id = path_element.get("id")
            path_data = path_element.get("d")
            if not path_id or not path_data:
                continue
            connectors.append({
                "id": path_id,
                "group": stable_by_legacy[legacy_id],
                "path": path_data,
                "stroke": path_element.get("stroke", group.get("stroke", "#333333")),
                "stroke_width": _number(path_element.get("stroke-width"), 2),
                "dash": path_element.get("stroke-dasharray"),
                "arrow_start": path_element.get("marker-start") is not None,
                "arrow_end": path_element.get("marker-end") is not None,
            })
    return texts, connectors


def _number(value: Optional[str], default: Union[int, float]) -> Union[int, float]:
    if value is None:
        return default
    number = float(value)
    return int(number) if number.is_integer() else number


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--legacy-root", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    report = build_regression(args.source, args.legacy_root, args.project, args.browser)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
