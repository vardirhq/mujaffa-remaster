# Registered showroom composition

The original `showroom` frame is now reconstructed as stage-registered layers rather than as separately cropped images.

`tools/swf_showroom_extract.py` renders each supported original object onto a transparent 500×500 canvas using the exact main-timeline placement matrix from frame 730. This means the resulting PNGs can all be stacked at the same origin in Sindri without hand-tuned offsets.

Current reconstructed layers:

- character 934: room/background, main-timeline depth 92
- character 869: Mujaffa presentation, main-timeline depth 93
- character 279: original information/control panel, main-timeline depth 287

The customizable car remains a live layered object rather than a flattened showroom layer.

## Playable showroom

`tools/install_showroom.py` puts frame 730 in the game beside the frame-722
workshop. Run it after `install_workshop_interactivity.py`; Pages CI does.

- The workshop-only layers move under `Workshop View`; room 934, Mujaffa 869
  and panel 279 go under a disabled `Showroom View`. The VERKSTED and SHOWROOM
  tabs switch between them, and `workshop.view` on the game board says which
  is showing.
- The car is not copied. Frame 730 places character 875 at (259.4, 180.95)
  instead of frame 722's (329.65, 193.9) at the same scale, so
  `Garage.refresh_layout` moves the live car by that offset and hides the
  UTSTYR rail.
- Entering the showroom runs `describe()` in
  `scripts/showroom_controller.decay`, a port of frame 745 (`makeDescription`)
  into edit-text 935 (`beskrivelse`). It keeps the original's strings and
  quirks: the white stripe has no comma, the medium spoiler has two spaces,
  racer rims read as chrome and krom rims as sport, and the `forude` typo means
  the tyres are always followed by ", ".
- The header numbers are live text, not pixels in the chrome: PENGER is
  `workshop.money` (edit-text 928, `penge`), BMW is 1 plus
  `workshop.street_cred` (931, `bil_cool`, which frame 202 starts at 1), and
  STREET CRED is `game.cool` (927, `cool`).

World text (`sindri.text`) needs Sindri `2510aac8` or later, which is why the
pin moved with this change.

Still not reconstructed: the KJØR! button and the driving it leads to.
