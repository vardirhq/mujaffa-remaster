# Registered showroom composition

The original `showroom` frame is now reconstructed as stage-registered layers rather than as separately cropped images.

`tools/swf_showroom_extract.py` renders each supported original object onto a transparent 500×500 canvas using the exact main-timeline placement matrix from frame 730. This means the resulting PNGs can all be stacked at the same origin in Sindri without hand-tuned offsets.

Current reconstructed layers:

- character 934: room/background, main-timeline depth 92
- character 869: Mujaffa presentation, main-timeline depth 93
- character 279: original information/control panel, main-timeline depth 287

The customizable car remains a live layered object rather than a flattened showroom layer.

The next parity work is the remaining foreground UI from frame 730:

- button definitions 925 and 936
- text/edit-text definitions 927–932
- exact purchase/category interaction behavior

Those definitions need button/text-aware SWF reconstruction rather than being guessed from screenshots or replaced with generic UI art.
