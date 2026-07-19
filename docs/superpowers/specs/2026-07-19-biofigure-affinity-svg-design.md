# Biofigure Affinity SVG Skill Design

## Goal

Build a reusable Codex skill that can reconstruct an existing biomedical figure or create a new one, manage every biological element through a stable semantic manifest, and compile the project into an SVG that imports into Affinity with selectable named groups.

Affinity import is a release gate, not a best-effort compatibility target.

## Supported workflows

### Existing figure to editable SVG

1. Read the source image and canvas size.
2. Suggest groups for panels, organs, cells, nerves, receptors, particles, connectors, labels, and backgrounds.
3. Produce a numbered review image and manifest.
4. Apply requested split, merge, rename, and bounding-box changes.
5. Extract an exact opaque crop and a transparent clean asset for every approved biological group.
6. Compile the dual-state Affinity SVG.
7. Render at the original dimensions and compare against the source.
8. Import into Affinity and verify selection, visibility toggling, movement, undo, and live text/vector editing.

### Group-first generation

1. Convert the scientific brief into a layout and group manifest.
2. Define global style anchors and per-group generation prompts.
3. Generate biological assets separately, preserving transparent backgrounds where possible.
4. Normalize assets, positions, and z-order.
5. Compile the dual-state Affinity SVG.
6. Verify visual consistency and Affinity behavior.

### Whole-image generation followed by decomposition

1. Generate a complete reference figure from the scientific brief.
2. Treat the generated image as an existing figure.
3. Run the same suggestion, confirmation, extraction, compilation, and Affinity verification flow.

## Project structure

```text
biofigure-project/
├── project.yaml
├── source/
│   ├── original.png
│   └── references/
├── groups/
│   ├── clean/
│   └── generated/
├── review/
│   ├── numbered.png
│   └── group-report.json
├── build/
│   ├── exact/
│   ├── masks/
│   ├── base.png
│   └── render.png
└── exports/
    ├── affinity.svg
    └── preview.png
```

The skill repository is separate from generated projects. The CLI accepts an explicit project directory and never relies on the skill checkout as a working directory.

## Manifest contract

`project.yaml` is the project source of truth. It contains:

- `schema_version`
- canvas width, height, and background
- source image and optional reference images
- global style anchors
- ordered panels
- ordered semantic groups
- live text objects
- vector connectors
- fidelity and Affinity QA settings

Every semantic group has a stable dotted ID and the following fields:

```yaml
id: panel-c.drg
kind: biological-asset
label: DRG
panel: panel-c
bbox: [318, 765, 60, 76]
z_index: 42
source: source/original.png
asset: groups/clean/panel-c.drg.png
exact_crop: build/exact/panel-c.drg.png
visible: true
editable: true
generation:
  prompt: null
  style_refs: []
```

Valid kinds are `panel`, `background`, `biological-asset`, `connector`, `text`, and `reference`. IDs remain stable across recompilation. Replacing one group must not regenerate or reposition unrelated groups.

## Human confirmation

Automatic grouping produces suggestions, not silent final decisions. The skill writes a numbered overlay and a JSON report. The user can request operations such as:

- split `panel-c.drg-composite` into `panel-c.drg` and `panel-c.gut-afferent`
- merge `panel-b.cytokines-1` and `panel-b.cytokines-2`
- rename `panel-d.asset-03` to `panel-d.microenvironment`
- expand the bounding box for `panel-a.spinal-cord`

The CLI applies these changes deterministically and regenerates the review image. Compilation only proceeds after the manifest records `review.status: approved` unless the user explicitly requests a draft build.

## Affinity SVG contract

The compiler emits these top-level named layers in this order:

1. `00-background`
2. `01-exact-base`
3. `10-exact-assets`
4. `20-exact-connectors`
5. `30-exact-text`
6. `40-live-text`
7. `50-vector-connectors`
8. `60-clean-assets`
9. `90-reference`

The exact layers are visible by default. The live text, vector connector, clean asset, and reference layers are hidden by default.

Each layer uses `inkscape:groupmode="layer"` and a stable `inkscape:label`. Each object uses a named `<g>` wrapper and stable `id`. Raster assets are embedded as PNG data URIs so the SVG remains portable.

Existing-figure builds use opaque exact crops with a small same-pixel overlap above a punched base. This prevents transparent interpolation seams while preserving the original appearance. Clean transparent assets are stored separately for background-free movement.

Live text uses this fallback chain:

```text
Arial,'Microsoft YaHei','PingFang SC','Hiragino Sans GB',sans-serif
```

Exact text crops preserve the default appearance. Live text is the editable alternative and may render with small platform-dependent width or antialiasing differences.

## CLI contract

The skill exposes one Python entry point:

```bash
python3 scripts/biofigure.py <command> [options]
```

Commands:

- `doctor`: verify Python, Pillow, PyYAML, ImageMagick, browser renderer, and optional Affinity availability.
- `init`: create a project from an existing image or an empty canvas.
- `suggest`: add candidate groups supplied by the agent and render the numbered review image.
- `split`: replace one group with two or more approved groups.
- `merge`: replace multiple groups with one group.
- `rename`: change an ID while updating references.
- `approve`: mark the current manifest revision approved.
- `extract`: build exact crops, masks, transparent assets, and punched base.
- `generate`: register one or more externally generated assets and their prompts.
- `replace`: replace one group asset without touching unrelated groups.
- `compile`: build the dual-state SVG.
- `render`: render the SVG to a 1:1 PNG using a supported browser.
- `qa`: validate manifest structure, SVG layers, object IDs, preview dimensions, fidelity metrics, and Affinity checklist state.
- `inspect`: report group metadata and dependent objects.

Image generation is orchestrated by Codex through the available image generation tool. The CLI records prompts and files but does not hard-code a remote image provider.

## Incremental rebuild rules

- Manifest-only rename: rewrite SVG metadata and labels.
- Text change: rebuild live text and exact text only when a replacement raster is provided.
- Connector change: rebuild vector connector and exact connector layers.
- Asset replacement: rebuild that group, punched base overlap, SVG, and preview.
- Canvas or panel geometry change: perform a full rebuild.

The CLI writes a build-state file containing source hashes, manifest hash, generated file hashes, and the last command. It reports which groups were rebuilt.

## Error handling

- Reject duplicate IDs, out-of-bounds boxes, negative sizes, missing files, invalid z-index values, and unresolved references before extraction.
- Refuse a release build when review status is not approved.
- Refuse a fidelity claim when the source and preview dimensions differ.
- Report missing optional tools separately from missing required tools.
- Preserve the previous successful export by writing to a temporary file and replacing the final SVG only after validation.
- Never overwrite user-provided source or group assets.
- Keep failed intermediate output under `build/failed/<timestamp>/` for diagnosis.

## Verification and acceptance

### Automated tests

- Manifest schema and stable-ID validation.
- Split, merge, rename, and reference-update behavior.
- Exact crop and clean asset extraction.
- Layer order, labels, hidden-state flags, live text, connector paths, and embedded image checks.
- Incremental rebuild scope.
- Fidelity metric computation.
- Fresh-project and existing-project CLI smoke tests.

### SST/SSTR regression

Use the existing 1448 × 1086 SST/SSTR figure as the primary regression fixture without committing the source image into the skill repository. The test accepts a local fixture path and proves:

- all approved C and D biological content remains present
- DRG and nerve connector groups are independently represented
- arrow groups and editable text alternatives exist
- the rendered default state matches the source with RMSE `0 (0)` for the approved manifest

### Affinity release gate

For release validation on a machine with Affinity installed:

1. Open the compiled SVG in Affinity.
2. Confirm all nine top-level layers are present.
3. Select a named exact asset group.
4. Move it by one pixel and undo.
5. Toggle the clean asset, live text, and vector connector layers.
6. Select and edit one live text object.
7. Reopen the unchanged SVG and confirm default visibility and appearance.

Automated structural checks do not replace this real import gate.

## Skill packaging

- Repository root is the skill root.
- `SKILL.md` contains the concise workflow and routes detailed behavior to references.
- `scripts/` contains the deterministic CLI and tests.
- `references/` contains the manifest schema, Affinity contract, generation workflow, and QA guide.
- `agents/openai.yaml` supplies UI metadata.
- The development repository is the source of truth.
- `/Users/jacklee/.codex/skills/biofigure-affinity-svg` is a symlink to the repository.
- GitHub Actions runs the skill validator, unit tests, and a synthetic project smoke test.

## Out of scope for version 1

- Writing native `.afdesign` files.
- A standalone browser-based group editor.
- Training or bundling a segmentation model.
- Hard-coding a commercial image-generation provider.
- Claiming that modified live text remains pixel-identical to the source raster.
