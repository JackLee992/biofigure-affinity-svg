# Manifest schema

`project.yaml` is the source of truth for semantic identity, geometry, editable alternatives, and QA policy. Schema version 1 is intentionally small and portable.

## Top-level fields

```yaml
schema_version: 1
project:
  name: figure-name
canvas:
  width: 1448
  height: 1086
  background: "#ffffff"
source:
  image: source/original.png
  references: []
style:
  prompt: null
  references: []
review:
  status: draft
  revision: 0
  approved_manifest_sha256: null
groups: []
texts: []
connectors: []
qa:
  require_pixel_match: true
  rmse_threshold: 0.0
```

All stored file paths are project-relative `/`-separated strings. Do not store absolute macOS or Windows paths.

## Semantic groups

Required group fields:

```json
{
  "id": "panel-c.drg",
  "kind": "biological-asset",
  "label": "DRG",
  "panel": "panel-c",
  "bbox": [308, 746, 64, 62],
  "z_index": 40
}
```

`bbox` is `[x, y, width, height]` in source-image pixels. Values must be integers, positive in size, and fully inside the canvas.

Valid kinds:

- `panel`
- `background`
- `biological-asset`
- `connector`
- `text`
- `reference`

Normalized optional fields include `visible`, `editable`, `background`, `tolerance`, `source`, `asset`, `exact_crop`, and `generation`.

Use lowercase stable IDs containing letters, digits, dots, and hyphens. Treat IDs as public API: other groups, text items, connectors, reports, and downstream edits may reference them.

## Live text alternatives

```yaml
texts:
  - id: live-panel-c-drg-label
    group: panel-c.drg-label
    text: DRG
    x: 320
    y: 742
    font_size: 18
    font_weight: 600
    fill: "#222222"
    text_anchor: start
```

The compiler always applies the cross-platform font fallback chain. Keep the exact source text crop as the visible default and place live text in hidden layer `40-live-text`.

## Vector connector alternatives

```yaml
connectors:
  - id: vector-panel-c-brain-gut-nerve
    group: panel-c.brain-gut-nerve
    path: M 180 780 C 245 690 330 690 410 735
    stroke: "#14833b"
    stroke_width: 3
    dash: null
    arrow_end: true
```

Use SVG path data in canvas coordinates. Keep the exact connector crop visible by default and the vector alternative in hidden layer `50-vector-connectors`.

## Approval invariant

Approval stores a hash of the complete normalized manifest with the approval hash field cleared. Any semantic change clears approval. Release extraction and compilation reject draft or stale manifests unless `--draft` is explicitly used for inspection.
