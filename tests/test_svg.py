from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

from biofigure_lib.assets import extract_project
from biofigure_lib.manifest import load_manifest, save_manifest
from biofigure_lib.project import init_project
from biofigure_lib.review import apply_suggestions, approve_review
from biofigure_lib.svg import LAYER_LABELS, compile_affinity_svg


SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
NS = {"svg": SVG_NS, "inkscape": INKSCAPE_NS}
LABEL = f"{{{INKSCAPE_NS}}}label"


def group(group_id: str, kind: str, bbox: list[int], z_index: int) -> dict:
    return {
        "id": group_id,
        "kind": kind,
        "label": group_id,
        "panel": "panel-a",
        "bbox": bbox,
        "z_index": z_index,
        "background": "#ffffff",
        "tolerance": 8,
    }


def compiled_project(tmp_path: Path) -> Path:
    source = tmp_path / "source.png"
    image = Image.new("RGBA", (80, 60), "white")
    for x in range(8, 25):
        for y in range(8, 25):
            image.putpixel((x, y), (120, 70, 170, 255))
    image.save(source)
    project = tmp_path / "project"
    init_project(project, "svg", source, None, None, "#ffffff")
    apply_suggestions(project, [
        group("panel-a.cell", "biological-asset", [6, 6, 22, 22], 10),
        group("panel-a.nerve", "connector", [28, 10, 30, 20], 20),
        group("panel-a.label-exact", "text", [8, 32, 25, 12], 30),
    ])
    data = load_manifest(project / "project.yaml")
    data["texts"] = [{
        "id": "panel-a.label",
        "group": "panel-a.label-exact",
        "text": "细胞 Cell",
        "x": 8,
        "y": 42,
        "font_size": 12,
        "fill": "#222222",
        "font_weight": 400,
    }]
    data["connectors"] = [{
        "id": "panel-a.nerve-vector",
        "group": "panel-a.nerve",
        "from": "panel-a.cell",
        "to": "panel-a.label-exact",
        "path": "M 28 20 C 38 10 48 30 58 20",
        "stroke": "#7b3fa0",
        "stroke_width": 2,
        "dash": None,
        "arrow_start": True,
        "arrow_end": True,
    }]
    save_manifest(project / "project.yaml", data)
    approve_review(project)
    extract_project(project)
    compile_affinity_svg(project)
    return project


def test_compiler_emits_affinity_layer_contract(tmp_path: Path) -> None:
    project = compiled_project(tmp_path)
    root = ET.parse(project / "exports/affinity.svg").getroot()
    labels = [node.attrib[LABEL] for node in root.findall("./svg:g", NS)]
    assert labels == LAYER_LABELS


def test_editable_alternative_layers_are_hidden(tmp_path: Path) -> None:
    project = compiled_project(tmp_path)
    root = ET.parse(project / "exports/affinity.svg").getroot()
    by_label = {node.attrib[LABEL]: node for node in root.findall("./svg:g", NS)}
    for label in ("40-live-text", "50-vector-connectors", "60-clean-assets", "90-reference"):
        assert "display:none" in by_label[label].attrib["style"]


def test_compiler_embeds_exact_and_clean_images_with_stable_ids(tmp_path: Path) -> None:
    project = compiled_project(tmp_path)
    source = (project / "exports/affinity.svg").read_text(encoding="utf-8")
    assert 'id="exact-panel-a.cell"' in source
    assert 'id="clean-panel-a.cell"' in source
    assert "data:image/png;base64," in source
    assert "细胞 Cell" in source
    assert "M 28 20 C 38 10 48 30 58 20" in source
    assert 'marker-start="url(#bio-arrow)"' in source
    assert 'marker-end="url(#bio-arrow)"' in source


def test_compiler_refuses_stale_approval(tmp_path: Path) -> None:
    project = compiled_project(tmp_path)
    data = load_manifest(project / "project.yaml")
    data["groups"][0]["label"] = "changed"
    data["review"]["status"] = "draft"
    data["review"]["approved_manifest_sha256"] = None
    save_manifest(project / "project.yaml", data)
    try:
        compile_affinity_svg(project)
    except Exception as exc:
        assert "approved" in str(exc)
    else:
        raise AssertionError("compile should reject a draft manifest")
