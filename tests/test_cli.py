from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/biofigure.py"


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False,
    )


def test_cli_help_lists_all_commands() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    for command in (
        "doctor", "init", "suggest", "split", "merge", "rename", "approve",
        "extract", "generate", "replace", "compile", "render", "qa", "inspect",
    ):
        assert command in result.stdout


def test_cli_doctor_runs_before_third_party_packages_are_installed() -> None:
    result = subprocess.run(
        [sys.executable, "-S", str(CLI), "--json", "doctor"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["packages"]["Pillow"] is None
    assert report["packages"]["PyYAML"] is None


def test_cli_init_and_inspect_json(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (40, 30), "white").save(source)
    project = tmp_path / "project"
    initialized = run_cli("--json", "init", str(project), "--name", "cli", "--source", str(source))
    assert initialized.returncode == 0, initialized.stderr
    assert json.loads(initialized.stdout)["manifest"].endswith("project.yaml")
    inspected = run_cli("--json", "inspect", str(project))
    assert inspected.returncode == 0
    assert json.loads(inspected.stdout)["project"] == "cli"


def test_cli_suggest_approve_extract_and_compile(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (40, 30), "white").save(source)
    project = tmp_path / "project"
    assert run_cli("init", str(project), "--name", "flow", "--source", str(source)).returncode == 0
    candidates = tmp_path / "candidates.json"
    candidate_payload = json.dumps([{
        "id": "panel-a.cell",
        "kind": "biological-asset",
        "label": "cell",
        "panel": "panel-a",
        "bbox": [5, 5, 15, 15],
        "z_index": 10,
        "background": "#ffffff",
        "tolerance": 8,
    }], ensure_ascii=False)
    candidates.write_bytes(b"\xef\xbb\xbf" + candidate_payload.replace("\n", "\r\n").encode("utf-8"))
    assert run_cli("suggest", str(project), "--candidates", str(candidates)).returncode == 0
    assert run_cli("approve", str(project)).returncode == 0
    assert run_cli("extract", str(project)).returncode == 0
    compiled = run_cli("compile", str(project))
    assert compiled.returncode == 0, compiled.stderr
    assert (project / "exports/affinity.svg").is_file()


def test_cli_manifest_error_uses_exit_code_two(tmp_path: Path) -> None:
    result = run_cli("inspect", str(tmp_path / "missing"))
    assert result.returncode == 2
    assert "manifest" in result.stderr.lower()
