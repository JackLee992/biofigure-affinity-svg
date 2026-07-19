# Affinity dual-state SVG contract

The compiled SVG is one portable file with embedded PNG data. It opens in Affinity Designer and Adobe Illustrator without linked-image dependencies.

## Required top-level layer order

1. `00-background` — editable canvas color.
2. `01-exact-base` — source image with semantic regions punched out.
3. `10-exact-assets` — visible exact biological-asset crops.
4. `20-exact-connectors` — visible exact arrow and nerve crops.
5. `30-exact-text` — visible exact text crops.
6. `40-live-text` — hidden editable SVG text.
7. `50-vector-connectors` — hidden editable SVG paths and arrowheads.
8. `60-clean-assets` — hidden transparent biological assets.
9. `90-reference` — hidden full original source.

The order and labels are a release contract. Do not add another top-level layer. Place new objects inside the correct layer.

## Default and editable states

Default state:

- Layers 00 through 30 are visible.
- Layers 40, 50, 60, and 90 are hidden.
- The rendered pixels match the source at or below the manifest RMSE threshold.

Editable state:

- Hide an exact layer for the object category being edited.
- Show its paired editable layer.
- Edit live text, vector connectors, or transparent PNG groups.
- Preserve each named group and stable object ID.

The exact state is the fidelity baseline. The editable state is a semantic editing surface, not a promise that every original raster pixel becomes a vector path.

## Text portability

Live text uses:

```text
Arial,'Microsoft YaHei','PingFang SC','Hiragino Sans GB',sans-serif
```

This chain favors fonts commonly available on both Windows and macOS. Font substitution can change live-text geometry; therefore exact text crops remain visible in the default state.

## Embedded assets

Every SVG `<image>` must use a `data:image/png;base64,...` URI. Do not use `file:` URLs or paths outside the SVG. Affinity import must not depend on the project directory remaining beside the exported file.
