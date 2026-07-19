from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from PIL import Image

from .errors import QAError
from .manifest import load_manifest
from .svg import INKSCAPE_NS, LAYER_LABELS, SVG_NS


AFFINITY_CHECKS = (
    "opened_svg",
    "selected_named_group",
    "moved_one_pixel",
    "undo_succeeded",
    "toggled_live_text",
    "toggled_vector_connectors",
    "toggled_clean_assets",
    "edited_live_text",
    "reopened_svg",
)


def compute_rmse(source: Path, preview: Path) -> tuple[float, float]:
    with Image.open(source) as source_image, Image.open(preview) as preview_image:
        source_rgb = source_image.convert("RGB")
        preview_rgb = preview_image.convert("RGB")
        if source_rgb.size != preview_rgb.size:
            raise QAError("source and preview dimensions differ")
        squared = 0
        count = source_rgb.width * source_rgb.height * 3
        for source_pixel, preview_pixel in zip(source_rgb.getdata(), preview_rgb.getdata()):
            squared += sum((left - right) ** 2 for left, right in zip(source_pixel, preview_pixel))
    absolute = math.sqrt(squared / count)
    normalized = absolute / 255.0
    return absolute, normalized


def run_qa(project_dir: Path, require_affinity: bool = False) -> dict[str, Any]:
    project_dir = Path(project_dir)
    data = load_manifest(project_dir / "project.yaml")
    svg_path = project_dir / "exports/affinity.svg"
    preview = project_dir / "exports/preview.png"
    if not svg_path.is_file():
        raise QAError("compiled SVG is missing")
    if not preview.is_file():
        raise QAError("rendered preview is missing")

    tree = ET.parse(svg_path)
    root = tree.getroot()
    expected_viewbox = f"0 0 {data['canvas']['width']} {data['canvas']['height']}"
    if root.get("viewBox") != expected_viewbox:
        raise QAError("SVG viewBox does not match canvas")
    namespace = {"svg": SVG_NS, "inkscape": INKSCAPE_NS}
    label_key = f"{{{INKSCAPE_NS}}}label"
    layers = root.findall("./svg:g", namespace)
    labels = [layer.get(label_key) for layer in layers]
    if labels != LAYER_LABELS:
        raise QAError(f"Affinity layer contract mismatch: {labels}")
    by_label = dict(zip(labels, layers))
    for label in ("40-live-text", "50-vector-connectors", "60-clean-assets", "90-reference"):
        if "display:none" not in by_label[label].get("style", ""):
            raise QAError(f"editable alternative layer must be hidden: {label}")

    ids = [element.get("id") for element in root.iter() if element.get("id")]
    if len(ids) != len(set(ids)):
        raise QAError("SVG contains duplicate object IDs")
    if not root.findall(".//svg:image", namespace):
        raise QAError("SVG does not contain embedded images")

    with Image.open(preview) as preview_image:
        if preview_image.size != (data["canvas"]["width"], data["canvas"]["height"]):
            raise QAError("preview dimensions do not match canvas")
    source = _resolve(project_dir, data["source"]["image"])
    rmse_absolute, rmse_normalized = compute_rmse(source, preview)
    threshold = float(data.get("qa", {}).get("rmse_threshold", 0.0))
    if data.get("qa", {}).get("require_pixel_match") and rmse_normalized > threshold:
        raise QAError(f"fidelity RMSE {rmse_normalized:.8f} exceeds threshold {threshold:.8f}")

    affinity_passed = False
    affinity_report_path = project_dir / "review/affinity-check.json"
    if affinity_report_path.is_file():
        affinity = json.loads(affinity_report_path.read_text(encoding="utf-8"))
        affinity_passed = _validate_affinity_report(affinity)
    if require_affinity and not affinity_passed:
        raise QAError("Affinity import gate has not passed")

    report = {
        "layers": len(layers),
        "layer_labels": labels,
        "objects_with_ids": len(ids),
        "rmse_absolute": rmse_absolute,
        "rmse_normalized": rmse_normalized,
        "affinity_required": require_affinity,
        "affinity_passed": affinity_passed,
    }
    output = project_dir / "review/qa-report.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    return report


def _validate_affinity_report(report: dict[str, Any]) -> bool:
    if not isinstance(report.get("platform"), str) or not report["platform"]:
        return False
    if not isinstance(report.get("affinity_version"), str) or not report["affinity_version"]:
        return False
    if report.get("top_level_layers") != 9:
        return False
    return all(report.get(check) is True for check in AFFINITY_CHECKS)


def _resolve(project_dir: Path, relative: str) -> Path:
    return Path(project_dir) / Path(*relative.split("/"))
