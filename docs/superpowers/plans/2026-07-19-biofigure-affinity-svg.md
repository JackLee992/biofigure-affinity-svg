# Biofigure Affinity SVG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, install, and publish a Codex skill that compiles existing or generated biomedical figures into manifest-driven, dual-state SVG files verified for Affinity import.

**Architecture:** A Python CLI owns the project manifest, review operations, extraction, SVG compilation, rendering, and QA. Codex supplies visual grouping proposals and generated images; deterministic scripts preserve stable IDs, rebuild only affected groups, and emit the fixed Affinity layer contract.

**Tech Stack:** Python 3.11+, Pillow, PyYAML, pytest, SVG/XML, Chrome-compatible headless rendering, ImageMagick diagnostics, Affinity desktop validation, GitHub Actions.

## Global Constraints

- Affinity import is a release gate, not best-effort compatibility.
- Support existing-image reconstruction, group-first generation, and whole-image generation followed by decomposition.
- Require automatic group suggestions followed by human confirmation for release builds.
- Preserve stable dotted IDs and never regenerate unrelated groups during a replacement.
- Emit the nine top-level layers defined in the design specification in the specified order.
- Keep exact layers visible and live-text, vector-connector, clean-asset, and reference layers hidden by default.
- Never overwrite user-provided source or group assets.
- Do not write native `.afdesign` files or bundle a segmentation/image-generation provider.
- Keep manifests, generated SVG, and CLI behavior portable across macOS and Windows; never persist machine-specific absolute paths.
- Run the automated suite on macOS, Windows, and Linux; perform Affinity desktop validation on macOS now and preserve the same checklist for Windows.

---

### Task 1: Manifest model and project initialization

**Files:**
- Create: `requirements.txt`
- Create: `scripts/biofigure_lib/__init__.py`
- Create: `scripts/biofigure_lib/errors.py`
- Create: `scripts/biofigure_lib/manifest.py`
- Create: `scripts/biofigure_lib/project.py`
- Create: `tests/test_manifest.py`

**Interfaces:**
- Produces: `load_manifest(path: Path) -> dict`, `save_manifest(path: Path, data: dict) -> None`, `validate_manifest(data: dict, project_dir: Path) -> None`, `init_project(project_dir: Path, name: str, source: Path | None, width: int | None, height: int | None, background: str) -> Path`.

- [ ] **Step 1: Write failing manifest and initialization tests**

```python
def test_init_existing_image_creates_manifest(tmp_path, sample_png):
    manifest_path = init_project(tmp_path / "case", "case", sample_png, None, None, "#ffffff")
    data = load_manifest(manifest_path)
    assert data["schema_version"] == 1
    assert data["canvas"] == {"width": 32, "height": 24, "background": "#ffffff"}
    assert data["review"]["status"] == "draft"

def test_duplicate_group_ids_are_rejected(valid_manifest, tmp_path):
    valid_manifest["groups"] = [{"id": "panel-a.cell", "kind": "biological-asset", "bbox": [0, 0, 4, 4]}, {"id": "panel-a.cell", "kind": "biological-asset", "bbox": [5, 0, 4, 4]}]
    with pytest.raises(ManifestError, match="duplicate group id"):
        validate_manifest(valid_manifest, tmp_path)
```

- [ ] **Step 2: Run the tests and confirm missing-module failure**

Run: `python3 -m pytest tests/test_manifest.py -v`

Expected: import failure for `biofigure_lib.manifest`.

- [ ] **Step 3: Implement strict manifest validation and atomic writes**

Implement schema version, canvas, group-kind, stable-ID, bounding-box, file-reference, z-index, and duplicate-ID checks. Write YAML through a sibling temporary file and `Path.replace()` only after validation.

- [ ] **Step 4: Implement project initialization**

Copy an existing source image into `source/original.png`, or create an empty canvas from explicit dimensions. Create `groups/clean`, `groups/generated`, `review`, `build/exact`, `build/masks`, and `exports` without overwriting existing files.

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m pytest tests/test_manifest.py -v`

Expected: all manifest tests pass.

Commit: `git commit -m 'feat: add biofigure project manifest'`

### Task 2: Review operations and numbered overlay

**Files:**
- Create: `scripts/biofigure_lib/review.py`
- Create: `tests/test_review.py`
- Modify: `scripts/biofigure_lib/manifest.py`

**Interfaces:**
- Consumes: manifest loading, validation, and atomic saving from Task 1.
- Produces: `apply_suggestions(project_dir: Path, candidates: list[dict]) -> list[str]`, `split_group(project_dir: Path, source_id: str, replacements: list[dict]) -> None`, `merge_groups(project_dir: Path, source_ids: list[str], replacement: dict) -> None`, `rename_group(project_dir: Path, old_id: str, new_id: str) -> None`, `approve_review(project_dir: Path) -> None`, `render_numbered_review(project_dir: Path) -> Path`.

- [ ] **Step 1: Write failing split, merge, rename, approval, and overlay tests**

```python
def test_rename_updates_connector_references(project):
    rename_group(project, "panel-c.drg-old", "panel-c.drg")
    data = load_manifest(project / "project.yaml")
    assert data["connectors"][0]["from"] == "panel-c.drg"

def test_release_approval_records_manifest_hash(project):
    approve_review(project)
    data = load_manifest(project / "project.yaml")
    assert data["review"]["status"] == "approved"
    assert len(data["review"]["approved_manifest_sha256"]) == 64
```

- [ ] **Step 2: Run the review tests and confirm failure**

Run: `python3 -m pytest tests/test_review.py -v`

Expected: import failure for `biofigure_lib.review`.

- [ ] **Step 3: Implement deterministic review operations**

Every modifying operation increments `review.revision`, sets status to `draft`, validates the full manifest, and then saves atomically. Rename updates text, connector, parent, and dependency references.

- [ ] **Step 4: Implement the numbered review image and JSON report**

Draw stable index labels and kind-specific colors with Pillow. Save `review/numbered.png` and `review/group-report.json` containing index, ID, kind, label, panel, and bounding box.

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m pytest tests/test_review.py -v`

Expected: all review tests pass.

Commit: `git commit -m 'feat: add semantic group review workflow'`

### Task 3: Exact crops, clean assets, punched base, and incremental state

**Files:**
- Create: `scripts/biofigure_lib/assets.py`
- Create: `scripts/biofigure_lib/state.py`
- Create: `tests/test_assets.py`

**Interfaces:**
- Consumes: approved manifest and project paths.
- Produces: `extract_project(project_dir: Path, draft: bool = False) -> list[str]`, `replace_group_asset(project_dir: Path, group_id: str, asset_path: Path, prompt: str | None) -> list[str]`, `load_build_state(project_dir: Path) -> dict`.

- [ ] **Step 1: Write failing extraction and incremental-replacement tests**

```python
def test_extract_writes_exact_clean_and_punched_base(approved_project):
    rebuilt = extract_project(approved_project)
    assert rebuilt == ["panel-a.cell"]
    assert (approved_project / "build/exact/panel-a.cell.png").is_file()
    assert (approved_project / "groups/clean/panel-a.cell.png").is_file()
    assert (approved_project / "build/base.png").is_file()

def test_replace_rebuilds_only_target_group(two_group_project, replacement_png):
    rebuilt = replace_group_asset(two_group_project, "panel-a.cell", replacement_png, "purple cell")
    assert rebuilt == ["panel-a.cell"]
```

- [ ] **Step 2: Run the asset tests and confirm failure**

Run: `python3 -m pytest tests/test_assets.py -v`

Expected: import failure for `biofigure_lib.assets`.

- [ ] **Step 3: Implement exact crops and overlap-safe punched base**

Use the source image for exact opaque crops. Clear each approved crop interior from a copy of the source while keeping a two-pixel same-source overlap. Reject release extraction when review approval hash no longer matches the manifest.

- [ ] **Step 4: Implement edge-connected background removal**

Flood-fill from crop borders using the group tolerance and panel/canvas background color. Preserve non-edge-connected interior pixels and write transparent PNG output. Prefer a registered generated/clean asset over automatic background removal.

- [ ] **Step 5: Implement build hashes and incremental scope**

Record manifest, source, group input, and output SHA-256 values in `build/state.json`. A changed group rebuilds its crop, clean asset, base, SVG, and preview while leaving unrelated generated group files untouched.

- [ ] **Step 6: Run tests and commit**

Run: `python3 -m pytest tests/test_assets.py -v`

Expected: all asset tests pass.

Commit: `git commit -m 'feat: extract dual-state biological assets'`

### Task 4: Affinity SVG compiler

**Files:**
- Create: `scripts/biofigure_lib/svg.py`
- Create: `tests/test_svg.py`

**Interfaces:**
- Consumes: manifest, exact crops, clean assets, punched base, text objects, and connector paths.
- Produces: `compile_affinity_svg(project_dir: Path, draft: bool = False) -> Path`.

- [ ] **Step 1: Write a failing SVG contract test**

```python
def test_compiler_emits_affinity_layer_contract(compiled_project):
    root = ET.parse(compiled_project / "exports/affinity.svg").getroot()
    labels = [node.attrib[INKSCAPE_LABEL] for node in root.findall("./svg:g", NS)]
    assert labels == ["00-background", "01-exact-base", "10-exact-assets", "20-exact-connectors", "30-exact-text", "40-live-text", "50-vector-connectors", "60-clean-assets", "90-reference"]
```

- [ ] **Step 2: Run the SVG tests and confirm failure**

Run: `python3 -m pytest tests/test_svg.py -v`

Expected: import failure for `biofigure_lib.svg`.

- [ ] **Step 3: Implement portable embedded-image SVG output**

Embed PNGs as data URIs. Use `inkscape:groupmode="layer"`, stable labels, stable object IDs, integer coordinates, `preserveAspectRatio="none"`, and the manifest z-order. Use a temporary SVG and replace the export only after parsing it successfully.

- [ ] **Step 4: Implement exact/editable dual states**

Route groups by kind to exact asset, exact connector, or exact text layers. Emit live `<text>` with the specified font chain, vector `<path>` connectors, clean transparent images, and the complete hidden reference image.

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m pytest tests/test_svg.py -v`

Expected: all SVG contract tests pass.

Commit: `git commit -m 'feat: compile affinity dual-state svg'`

### Task 5: Rendering, fidelity QA, and Affinity checklist

**Files:**
- Create: `scripts/biofigure_lib/render.py`
- Create: `scripts/biofigure_lib/qa.py`
- Create: `tests/test_qa.py`

**Interfaces:**
- Consumes: compiled SVG, source image, manifest, and optional `review/affinity-check.json`.
- Produces: `render_svg(project_dir: Path, browser: Path | None = None) -> Path`, `compute_rmse(source: Path, preview: Path) -> tuple[float, float]`, `run_qa(project_dir: Path, require_affinity: bool = False) -> dict`.

- [ ] **Step 1: Write failing structural, RMSE, and Affinity-report tests**

```python
def test_identical_images_have_zero_rmse(sample_png):
    assert compute_rmse(sample_png, sample_png) == (0.0, 0.0)

def test_require_affinity_rejects_pending_report(compiled_project):
    with pytest.raises(QAError, match="Affinity import gate"):
        run_qa(compiled_project, require_affinity=True)
```

- [ ] **Step 2: Run the QA tests and confirm failure**

Run: `python3 -m pytest tests/test_qa.py -v`

Expected: import failure for `biofigure_lib.qa`.

- [ ] **Step 3: Implement browser rendering and fidelity metrics**

Detect Chrome, Chromium, or Edge through platform-specific candidate paths and `PATH`. Render with device scale factor 1 and the exact canvas dimensions using `shell=False`. Terminate the browser after the screenshot exists. Compute absolute and normalized RMSE with Pillow and reject dimension mismatches.

- [ ] **Step 4: Implement structural and Affinity report validation**

Validate layer order, hidden states, unique object IDs, embedded image presence, live text, vector connectors, and preview size. When required, accept only a report recording open, nine layers, selected group, one-pixel move, undo, layer toggles, live-text edit, and reopen checks as passed.

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m pytest tests/test_qa.py -v`

Expected: all QA tests pass.

Commit: `git commit -m 'feat: add rendering and affinity qa gates'`

### Task 6: CLI, doctor, and skill instructions

**Files:**
- Create: `scripts/biofigure.py`
- Create: `tests/test_cli.py`
- Modify: `SKILL.md`
- Modify: `agents/openai.yaml`
- Create: `references/manifest-schema.md`
- Create: `references/affinity-contract.md`
- Create: `references/generation-workflows.md`
- Create: `references/qa.md`

**Interfaces:**
- Consumes: all library functions from Tasks 1–5.
- Produces: the `doctor`, `init`, `suggest`, `split`, `merge`, `rename`, `approve`, `extract`, `generate`, `replace`, `compile`, `render`, `qa`, and `inspect` commands.

- [ ] **Step 1: Write failing CLI smoke tests**

```python
def test_cli_help_lists_all_commands():
    result = subprocess.run([sys.executable, "scripts/biofigure.py", "--help"], text=True, capture_output=True)
    assert result.returncode == 0
    for command in ("doctor", "init", "suggest", "split", "merge", "rename", "approve", "extract", "generate", "replace", "compile", "render", "qa", "inspect"):
        assert command in result.stdout
```

- [ ] **Step 2: Run the CLI test and confirm failure**

Run: `python3 -m pytest tests/test_cli.py -v`

Expected: command file missing.

- [ ] **Step 3: Implement argparse routing and JSON result output**

Every command returns a concise human-readable summary and supports `--json` for machine-readable results. Exit codes are `0` success, `2` usage/manifest error, `3` missing required dependency, and `4` QA failure.

- [ ] **Step 4: Write concise SKILL.md and routed references**

SKILL.md must tell another Codex instance to inspect the input, initialize a project, create grouping candidates, request confirmation, run deterministic scripts, use image generation only for requested groups, compile, render, perform structural QA, and use Computer Use for the real Affinity gate. Detailed manifest, generation, SVG, and QA rules live in the four references.

- [ ] **Step 5: Regenerate agents/openai.yaml and validate**

Run: `python3 /Users/jacklee/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py . --interface 'display_name=Biofigure Affinity SVG' --interface 'short_description=生成、拆分并编辑 Affinity 生物医学 SVG' --interface 'default_prompt=Use $biofigure-affinity-svg to turn this biomedical figure into a grouped, editable Affinity SVG.'`

Run: `python3 /Users/jacklee/.codex/skills/.system/skill-creator/scripts/quick_validate.py .`

Expected: `Skill is valid!`

- [ ] **Step 6: Run CLI tests and commit**

Run: `python3 -m pytest tests/test_cli.py -v`

Expected: all CLI tests pass.

Commit: `git commit -m 'feat: package biofigure affinity skill'`

### Task 7: Synthetic and SST/SSTR end-to-end regression

**Files:**
- Create: `tests/fixtures/synthetic-source.png`
- Create: `tests/fixtures/synthetic-candidates.json`
- Create: `tests/test_integration.py`
- Create: `scripts/regression_sst_sstr.py`

**Interfaces:**
- Consumes: public CLI and an optional local SST/SSTR source/repository path.
- Produces: a synthetic release-build smoke test and a real-project regression report.

- [ ] **Step 1: Add a generated synthetic fixture and end-to-end test**

The test initializes a project, imports candidates, approves, extracts, compiles, renders, and runs QA. Assert nine layers, stable IDs, a 1:1 preview, and zero RMSE.

- [ ] **Step 2: Run the integration test**

Run: `python3 -m pytest tests/test_integration.py -v`

Expected: synthetic workflow passes without Affinity.

- [ ] **Step 3: Implement the local SST/SSTR regression adapter**

Accept `--source`, `--existing-repo`, and `--output`. Convert the approved SST asset manifest and text/connector metadata into the generalized schema, compile with the new skill, render, and write JSON metrics. Do not copy the source image into the skill repository.

- [ ] **Step 4: Run the real regression**

Run: `python3 scripts/regression_sst_sstr.py --source '/Users/jacklee/Downloads/微信图片_20260717220545_408_1.png' --existing-repo /Users/jacklee/develop/daillyTasks/sst-sstr-editable --output /private/tmp/biofigure-sst-regression`

Expected: RMSE `0 (0)`, C/D assets and DRG connector IDs present, and Affinity SVG produced.

- [ ] **Step 5: Perform the Affinity import gate and record the report**

Open the regression SVG in Affinity; verify the nine layers, select and move a group one pixel, undo, toggle layers 40/50/60, select live text, and reopen. Save the pass report under the regression project and run `biofigure.py qa --require-affinity`.

- [ ] **Step 6: Commit regression support**

Commit: `git commit -m 'test: add biofigure end-to-end regression'`

### Task 8: CI, installation, GitHub publication, and fresh-clone proof

**Files:**
- Create: `.github/workflows/validate.yml`
- Create: `.gitignore`

**Interfaces:**
- Produces: reproducible checkout validation, installed-skill path, GitHub repository, and fresh-clone evidence.

- [ ] **Step 1: Add CI and ignore generated projects**

CI uses a `macos-latest`, `windows-latest`, and `ubuntu-latest` matrix. Each runner installs `requirements.txt`, runs `quick_validate.py`, compiles Python files, runs all unit tests, and executes the synthetic end-to-end workflow. Ignore caches, virtual environments, generated projects, and local regression output.

- [ ] **Step 2: Run the full local verification**

Run:

```bash
python3 -m py_compile scripts/biofigure.py scripts/biofigure_lib/*.py
python3 -m pytest tests -v
python3 /Users/jacklee/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
git diff --check
```

Expected: all commands return zero and validator prints `Skill is valid!`.

- [ ] **Step 3: Install as the single source of truth**

Create `/Users/jacklee/.codex/skills/biofigure-affinity-svg` as a symlink to `/Users/jacklee/develop/daillyTasks/biofigure-affinity-svg`. Verify with `test -L` and `readlink`.

Document Windows installation at `%USERPROFILE%\.codex\skills\biofigure-affinity-svg`, preferring a directory junction or symlink and falling back to a synchronized copy when developer mode is unavailable.

- [ ] **Step 4: Publish the standalone GitHub repository**

Create `JackLee992/biofigure-affinity-svg`, push `main`, and verify local and remote SHAs match.

- [ ] **Step 5: Verify a fresh clone**

Clone the GitHub repository into a temporary directory, install requirements in an isolated virtual environment, run quick validation, unit tests, and the synthetic workflow.

- [ ] **Step 6: Verify GitHub Actions and commit final evidence**

Confirm the validation workflow succeeds. Leave the working tree clean and the installed symlink pointing at the published checkout.
