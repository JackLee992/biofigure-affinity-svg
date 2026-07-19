# QA and release gates

Run automated checks and a real Affinity import check. Neither substitutes for the other.

## Automated QA

Run:

```text
python scripts/biofigure.py compile PROJECT
python scripts/biofigure.py render PROJECT
python scripts/biofigure.py qa PROJECT
```

The automated gate verifies:

- SVG viewBox equals the manifest canvas.
- There are exactly nine ordered top-level layers.
- Editable alternative layers are hidden by default.
- Object IDs are unique.
- Raster assets are embedded.
- Rendered dimensions match the source.
- Normalized RMSE stays within the manifest threshold.

For a pixel-identical reconstruction, set `require_pixel_match: true` and `rmse_threshold: 0.0`.

## Semantic completeness review

Compare the source and compiled preview at full size. Confirm every requested panel includes its small scientific structures, labels, arrows, inhibition bars, DRG/ganglia, neural lines, particles, and receptors. Pixel equality alone does not prove good group boundaries.

## Affinity Designer import check

Use Affinity Designer on the current test platform and record its exact version. Complete all checks:

1. Open `exports/affinity.svg` without an import error.
2. Confirm exactly nine named top-level layers.
3. Select one named semantic group.
4. Move it by one pixel.
5. Undo the move successfully.
6. Toggle `40-live-text` on and off.
7. Toggle `50-vector-connectors` on and off.
8. Toggle `60-clean-assets` on and off.
9. Edit one live text object's characters.
10. Save or close without replacing the source artifact, then reopen the original SVG successfully.

Write `review/affinity-check.json`:

```json
{
  "platform": "Windows 11 24H2",
  "affinity_version": "2.x",
  "top_level_layers": 9,
  "opened_svg": true,
  "selected_named_group": true,
  "moved_one_pixel": true,
  "undo_succeeded": true,
  "toggled_live_text": true,
  "toggled_vector_connectors": true,
  "toggled_clean_assets": true,
  "edited_live_text": true,
  "reopened_svg": true
}
```

Then run:

```text
python scripts/biofigure.py qa PROJECT --require-affinity
```

Do not set a check to true based only on XML inspection. Record only actions actually completed in Affinity.

## Cross-platform CI

The test matrix must run on macOS, Windows, and Ubuntu. Windows validation covers path handling, BOM-tolerant JSON, Microsoft Edge/Chrome discovery, UTF-8 metadata, XML compilation, and the Python CLI. A real Affinity UI check remains a separately recorded release gate because Affinity is not available on hosted CI runners.
