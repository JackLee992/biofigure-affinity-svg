---
name: biofigure-affinity-svg
description: Create, decompose, and incrementally edit biomedical or scientific figures as manifest-driven dual-state SVG projects for Affinity Designer and Adobe Illustrator. Use when reconstructing a raster figure into named editable groups; generating a new biomedical diagram group-by-group; generating a whole figure and reverse-segmenting it; splitting, merging, renaming, or replacing biological assets, text, arrows, nerves, receptors, particles, or panels; preserving a pixel-identical default state while keeping hidden live text, vector connectors, and transparent assets; or validating Affinity import on macOS and Windows.
---

# Biofigure Affinity SVG

Build a reviewed semantic manifest first, then compile one SVG with two coordinated states:

- The visible exact state reproduces the approved source image.
- Hidden editable layers expose live text, vector connectors, and transparent biological assets.

Use `python scripts/biofigure.py` from this skill directory on Windows. Use either `python` or `python3` on macOS/Linux.

Install the pinned dependency ranges once per checkout. Prefer a local virtual environment:

```text
# Windows PowerShell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# macOS/Linux
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Use the virtual-environment Python in the remaining commands when the host Python does not already provide Pillow and PyYAML.

## Route the request

Choose one workflow before editing:

1. Existing raster reconstruction: initialize from the source image, suggest groups, obtain human confirmation, extract, and compile.
2. Group-first generation: design and generate each biological asset independently, place it through the manifest, then compile.
3. Whole-image generation: generate the complete figure as a visual reference, then reverse-segment it through the same review workflow.
4. Incremental edit: inspect the existing manifest, change only named groups, and rebuild only affected outputs.

Read [generation-workflows.md](references/generation-workflows.md) for generation routing. Read [manifest-schema.md](references/manifest-schema.md) before creating or editing manifest data directly.

## Execute the workflow

### 1. Diagnose and initialize

Run:

```text
python scripts/biofigure.py doctor
python scripts/biofigure.py init PROJECT --name NAME --source SOURCE.png
```

For a blank figure, replace `--source` with `--width WIDTH --height HEIGHT --background '#ffffff'`.

Keep every path stored in `project.yaml` relative to the project directory and written with `/`. The compiler resolves these paths portably on macOS and Windows.

### 2. Suggest semantic groups

Create a UTF-8 JSON candidate list. Prefer stable dotted IDs such as:

- `panel-c.gut`
- `panel-c.drg`
- `panel-c.brain-gut-nerve`
- `panel-d.tumor-microenvironment`
- `panel-a.title-text`

Do not collapse distinct semantic objects merely because their pixels touch. Keep arrowheads with their connector unless the user specifically needs separate arrowhead editing.

Apply the candidates:

```text
python scripts/biofigure.py suggest PROJECT --candidates candidates.json
```

Show `PROJECT/review/numbered.png` and the numbered group report to the user. Treat suggestions as provisional until the user confirms them.

### 3. Refine and confirm

Use the narrow commands needed by the feedback:

```text
python scripts/biofigure.py split PROJECT panel-c.network --replacements split.json
python scripts/biofigure.py merge PROJECT panel-c.drg panel-c.nerve --replacement merged.json
python scripts/biofigure.py rename PROJECT panel-c.line panel-c.brain-gut-nerve
python scripts/biofigure.py approve PROJECT
```

Any split, merge, rename, or replacement returns the manifest to draft state. Reconfirm and approve after the last change.

### 4. Extract or replace assets

Extract exact crops and transparent clean assets:

```text
python scripts/biofigure.py extract PROJECT
```

For generated or externally prepared PNG assets:

```text
python scripts/biofigure.py generate PROJECT panel-c.drg generated-drg.png --prompt "PROMPT"
python scripts/biofigure.py replace PROJECT panel-c.drg corrected-drg.png
```

These commands update only the named group and its dependent build state. Reapprove before a release compile.

### 5. Compile, render, and validate

Run:

```text
python scripts/biofigure.py compile PROJECT
python scripts/biofigure.py render PROJECT
python scripts/biofigure.py qa PROJECT
```

The release SVG must contain exactly the ordered nine layers defined in [affinity-contract.md](references/affinity-contract.md). The source-faithful layers are visible by default; editable alternatives remain hidden so the initial canvas stays pixel-identical.

Read [qa.md](references/qa.md) before claiming completion.

## Perform the Affinity release gate

Treat successful Affinity Designer import as a goal, not a best-effort note.

Use the `computer-use` skill to open `PROJECT/exports/affinity.svg` in Affinity Designer and perform every manual check in [qa.md](references/qa.md). Test on the platform available in the current environment and record its platform and Affinity version in `PROJECT/review/affinity-check.json`.

Then run:

```text
python scripts/biofigure.py qa PROJECT --require-affinity
```

Do not report Affinity compatibility until this command passes.

## Preserve Windows compatibility

- Use `pathlib`-based CLI paths; never introduce POSIX-only path joins into manifest data.
- Invoke the CLI with `python`, not executable-bit assumptions.
- Use Chrome, Chromium, or Microsoft Edge for rendering. The runtime auto-detects standard Windows installations.
- Keep live SVG text on the shared font fallback chain: Arial, Microsoft YaHei, PingFang SC, Hiragino Sans GB, sans-serif.
- Never rely on `shell=True`, Bash, symlinks, case-sensitive filenames, or Unix-only utilities in the project workflow.
- Save JSON, YAML, and SVG as UTF-8. The JSON loader accepts UTF-8 with or without BOM.
- Re-run the Windows CI job after changes to the compiler, renderer, manifest model, or CLI.

## Inspect before changing

Use:

```text
python scripts/biofigure.py inspect PROJECT
python scripts/biofigure.py inspect PROJECT --group panel-c.drg
```

Prefer a named group replacement to a full regeneration. Preserve unrelated user edits and stable IDs.
