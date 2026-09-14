# Original SWF reference map

This document records facts extracted from `mujaffa_3juni_2003.swf` by
`tools/swf_inventory.py`. It is a parity aid, not a design document: the
remaster should first reproduce the original behaviour before deliberately
changing any of it.

## Container facts

- SHA-256: `5c154dfd129f73027d5098b146c377a535e1d94038845d72c2e8cc4368a04e4e`
- SWF signature: `FWS` (uncompressed)
- Flash version: 6
- File size: 763,238 bytes
- Stage: 500 × 500
- Frame rate: 12 FPS
- Main timeline: 811 frames
- Main-timeline tags: 3,813
- Defined characters: 1,330

## Asset structure

The movie is unusually favourable for a remaster because the standard SWF
bitmap-definition tags do not appear at all. The inventory finds:

- 514 vector shape definitions
- 258 sprite definitions
- 379 text/edit-text definitions
- 157 button definitions
- 20 defined sounds
- 67 ActionScript action blocks
- 62 frame labels
- 0 standard bitmap definitions

That does **not** prove that every visible pixel can already be treated as a
modern vector asset. It does prove that the original movie is overwhelmingly
structured Flash content rather than one flattened bitmap animation.

## Main timeline labels

The labels below are kept in original order. They are useful landmarks when we
start matching Flash behaviour to Sindri scenes and state transitions.

### Boot and navigation

`start`, `velkommen`, `speakDone`, `gotoInstruktioner`, `gotoGame`, `initGame`

### City / route setup

`nørrebro`, `vesterbro`, `østerbro`

### Route 1

`bane1_start`, `bane1_grønland`, `bane1_grunerløkka`, `bane1_sinsen`

### Route 2

`bane2_start`, `bane2_grønland`, `bane2_rådhusplassen`, `bane2_bislett`,
`bane2_sinsen`

### Route 3

`bane3_start`, `abne3_grønland`, `bane3_rådhusplassen`, `bane3_frogner`,
`bane3_holmenkollen`, `bane3_sinsen`

### Gameplay / result states

`level1`, `level2`, `level3`, `crash`, `incomplete`, `complete`, `status`, `1`,
`2`, `3`, `4`, `5`

### Extras and high score flow

`reklame`, `reklame2`, `credits`, `bimmerkort`, `sendBimmerkort`,
`makeGameOverDescription`, `gameoverprint`, `OnHiScore`, `showHi`, `hiError`,
`reimportHi`, `resetVars`, `checkload`, `setFaces`, `checkScore`, `sendHi`

### Car / shop / ending flow

`køb`, `showroom`, `kør`, `load`, `makeDescription`, `tellCar`, `slut`,
`afslut1`, `afslut`, `slutbane`

## What this gives us next

The frame labels give us the first real skeleton of the original state machine.
The next reverse-engineering step is to inspect the 67 `DoAction` blocks and
associate their constants, jumps and frame targets with these landmarks. That
should let us write a behaviour/parity specification before recreating the
logic in Decay.
