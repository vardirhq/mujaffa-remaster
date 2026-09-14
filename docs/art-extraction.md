# Original art extraction

The original Norwegian 1.6 SWF is overwhelmingly vector artwork. Its 514 shape definitions contain solid fills plus a small number of linear/radial gradients, and no standard bitmap-definition tags. That makes it possible to preserve the original drawing geometry losslessly before doing any remaster work.

`tools/swf_art_extract.py` converts every `DefineShape`, `DefineShape2`, and `DefineShape3` character into:

- an SVG preserving the SWF vector paths, solid colours, gradients, outlines and transparency;
- a transparent high-resolution PNG rasterized from that SVG;
- a manifest linking each output file back to the original SWF character ID, tag type, bounds and style counts.

The default reference build is **4× the original vector bounds**, capped at 2048 px per dimension. Because the SVG remains the canonical extraction, larger PNG variants can be generated later without repeatedly reverse-engineering the SWF.

## Generated artifact

CI creates the temporary `mujaffa-original-vector-art-4x` artifact containing:

```text
reference-art/
  manifest.json
  svg/
    shape-0001.svg
    ...
  png/
    shape-0001.png
    ...
```

The generated files are intentionally not part of the Git repository yet. They are original game artwork and should remain a reference input until the project's distribution/licensing position is settled. The remaster can derive new art from this corpus without coupling runtime code to the SWF itself.

## What this covers

This first pass extracts all **514 raw vector shape definitions**. It does not yet flatten higher-level Flash objects.

The next extraction stages are:

1. **Sprites/movie clips**: reconstruct `DefineSprite` timelines, placement matrices, nested shapes and per-frame compositions. Animated clips should export as numbered PNG frame sequences plus a JSON timing/placement manifest.
2. **Buttons**: render up/over/down/hit states from `DefineButton2` records.
3. **Text/edit text**: preserve source text, font references, colour and placement separately from raster artwork so remastered UI text can stay crisp and localizable.
4. **Scene/timeline captures**: render useful original screens as composition references, not as replacement source assets.

Keeping those layers separate matters. A raw SWF shape is often only one piece of a car, character, sign or interface element; treating every shape as a complete sprite would produce a large pile of technically correct but artistically useless files.

## Rebuilding PNGs locally

With CairoSVG installed:

```bash
python tools/swf_art_extract.py \
  mujaffa_3juni_2003.swf \
  reference-art \
  --scale 4 \
  --max-size 2048
```

The extractor fails if it encounters a bitmap fill type. The preserved Mujaffa file currently contains none, so silently losing bitmap-backed artwork would indicate either a parser regression or a different SWF reference.
