# Original showroom parity target

The main-timeline scene map now confirms that the original garage/showroom is not an abstract dark workshop. At the `showroom` label (frame 730), the SWF places character `934` at depth 92 as the room artwork, with the customizable car root `875` (`bil`) above it at depth 431.

Character 934 is a full vector room composition: turquoise/green walls, a pale floor, a wall poster, and a paint bucket. The remaster should use that composition as the visual baseline before any HD reinterpretation.

## Frame 730 landmarks

- character 934: original showroom room/background
- character 869 (`mujaffa`): Mujaffa character presentation
- character 875 (`bil`): customizable car root
- character 279: original blue information/control panel artwork
- characters 925 / 936 and related definitions: original interactive button groups
- characters 927–932: original text/edit-text presentation around the garage controls

The current responsive mobile controls remain temporary interaction scaffolding while those original UI groups are reconstructed. Responsive adaptation may rearrange controls for phone/desktop, but the art direction should derive from the SWF rather than from invented generic garage graphics.

## Build behavior

`tools/prepare_runtime_art.py` now copies the canonical showroom artwork directly from the lossless SWF vector extraction into `assets/generated/showroom/`. `tools/polish_garage_scene.py` uses that original artwork instead of the previously invented floor, pillars, platform, wall band, and lights.
