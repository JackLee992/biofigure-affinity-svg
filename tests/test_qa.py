from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from biofigure_lib.errors import QAError
from biofigure_lib.qa import AFFINITY_CHECKS, compute_rmse, run_qa
from biofigure_lib.render import browser_candidates, detect_browser, render_svg
from test_svg import compiled_project


def test_identical_images_have_zero_rmse(sample_png: Path) -> None:
    assert compute_rmse(sample_png, sample_png) == (0.0, 0.0)


def test_rmse_rejects_dimension_mismatch(tmp_path: Path) -> None:
    one = tmp_path / "one.png"
    two = tmp_path / "two.png"
    Image.new("RGB", (10, 10), "white").save(one)
    Image.new("RGB", (11, 10), "white").save(two)
    with pytest.raises(QAError, match="dimensions"):
        compute_rmse(one, two)


def test_windows_browser_candidates_include_edge_and_chrome() -> None:
    candidates = browser_candidates(
        platform_name="win32",
        env={
            "PROGRAMFILES": r"C:\Program Files",
            "PROGRAMFILES(X86)": r"C:\Program Files (x86)",
            "LOCALAPPDATA": r"C:\Users\tester\AppData\Local",
        },
    )
    joined = "\n".join(candidates).lower()
    assert "chrome.exe" in joined
    assert "msedge.exe" in joined


def test_browser_render_preserves_default_pixels(tmp_path: Path) -> None:
    try:
        detect_browser()
    except Exception as exc:
        pytest.skip(str(exc))
    project = compiled_project(tmp_path)
    preview = render_svg(project)
    assert compute_rmse(project / "source/original.png", preview) == (0.0, 0.0)


def test_structural_qa_passes_without_affinity_requirement(tmp_path: Path) -> None:
    project = compiled_project(tmp_path)
    shutil.copy2(project / "source/original.png", project / "exports/preview.png")
    report = run_qa(project)
    assert report["layers"] == 9
    assert report["rmse_absolute"] == 0.0
    assert report["affinity_required"] is False


def test_require_affinity_rejects_missing_report(tmp_path: Path) -> None:
    project = compiled_project(tmp_path)
    shutil.copy2(project / "source/original.png", project / "exports/preview.png")
    with pytest.raises(QAError, match="Affinity import gate"):
        run_qa(project, require_affinity=True)


def test_complete_affinity_report_passes_gate(tmp_path: Path) -> None:
    project = compiled_project(tmp_path)
    shutil.copy2(project / "source/original.png", project / "exports/preview.png")
    affinity = {
        "platform": "macOS",
        "affinity_version": "2",
        **{name: True for name in AFFINITY_CHECKS},
    }
    affinity["top_level_layers"] = 9
    (project / "review/affinity-check.json").write_text(json.dumps(affinity), encoding="utf-8")
    report = run_qa(project, require_affinity=True)
    assert report["affinity_passed"] is True
