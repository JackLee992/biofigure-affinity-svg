# Generation workflows

Use image generation only for requested biological or scientific content. Keep semantic grouping, coordinates, text, connectors, and release QA controlled by the manifest compiler.

## Group-first generation

Choose this route when the user needs maximum control over organs, cells, receptors, neural structures, arrows, or panel-specific replacement.

1. Define the canvas and panel layout.
2. Create semantic candidate groups before generation.
3. Ask the user to confirm group granularity from the numbered review.
4. Generate one transparent or plain-background asset per confirmed biological group with the image generation tool.
5. Register each PNG with `generate` and store the exact prompt in the manifest.
6. Draw text and connectors through live SVG alternatives.
7. Approve, extract, compile, render, and run QA.

Keep prompts specific to one object. Include viewpoint, scientific structure, palette, line weight, background treatment, and exclusion of labels/arrows unless those belong to that group.

## Whole-image then reverse-segment

Choose this route when visual composition or style discovery matters more than immediate object control.

1. Generate the full figure as a reference image.
2. Initialize the project from that image.
3. Propose groups for panels, biological assets, connectors, and text.
4. Show the numbered review and refine through split, merge, and rename.
5. Extract exact crops and transparent assets.
6. Add live text and vector connector alternatives.
7. Compile and validate the dual-state SVG.

Do not claim a whole generated image is semantically editable until the review, extraction, and layer compilation are complete.

## Existing raster reconstruction

Use the source as the immutable pixel baseline. Group according to meaning, not a fixed grid. Pay special attention to small but meaningful structures:

- DRG and ganglia
- afferent and efferent nerve lines
- arrowheads and inhibition bars
- cytokine particles and neurotransmitters
- receptor clusters
- cell subtypes
- panel labels and multiline titles

Missing a small neural link or arrow changes the scientific meaning even when the global RMSE remains low. Include semantic completeness checks in addition to pixel QA.

## Incremental edits

Inspect the named group, replace only that group, and preserve stable IDs. Generated replacements go under `groups/generated/`; extracted clean assets stay under `groups/clean/`. The build-state hash determines which group outputs require regeneration.
