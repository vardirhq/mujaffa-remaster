# Mujaffa Remaster: fidelity and performance contract

The 2003 Norwegian 1.6 SWF is the authority for **content and behavior**, not a mandate to reproduce Flash Player's frame-rate limitations.

## What must match

- Original artwork, visual order, colors, sprite poses, stage composition and category layout.
- Original prices, initial money, unlocks, purchase conditions, scoring and intentional quirks.
- Original animation **duration** and key poses, where recoverable, rather than original frame count as a runtime clock.
- Original controls and game rules. Touch and keyboard may map to equivalent actions.

## What may improve

- Target smooth 60 Hz rendering on capable hardware, without coupling simulation speed to render FPS.
- Sample inputs every update; avoid requiring a button to be held for a whole original Flash frame.
- Advance time-based animations by elapsed seconds. Retain intentionally stepped poses when smoothing would change the art.
- Avoid frame-dependent money, cooldown, movement, collisions, encounters and scoring.
- Maintain the original 500×500 stage coordinate system and composition at every viewport size.
- On devices that cannot sustain 60 FPS, game time and outcomes must remain consistent.

## Verification matrix

| Area | Reference | Acceptance |
| --- | --- | --- |
| Workshop | SWF button scripts and frames | Prices, category positions, state changes, coolness and purchase restrictions match |
| Rendering | SWF timeline and placed shapes | Same layers, palette, alpha and silhouettes |
| Timing | SWF timeline frame rate and action scripts | Equivalent real-time durations, independent of display refresh |
| Controls | Original actions | Equivalent keyboard and touch actions, no double purchases |
| Layout | Original square stage | No stretching, clipping or off-stage buttons on portrait and landscape |
| Performance | Modern browser player | Aim for 60 FPS; measure on desktop and mobile, do not claim without measurements |

## Implementation rules

1. Keep **simulation elapsed time** separate from rendering refresh and SWF source-frame indexing.
2. Preserve source-frame stepping where an animation is intentionally discrete.
3. Record measured timings and source frame references before changing motion.
4. Add a deterministic test for a mechanic before replacing frame-count assumptions.
5. Never adjust purchase prices, artwork or category order merely to improve UX.
6. Record deviations from SWF in the parity backlog; do not silently declare them fixed.

## Known open issues

- Window glass RGB/alpha fidelity remains unresolved after the extractor changes.
- Workshop accessory controls require visual and mobile touch verification.
- A measured 60 FPS baseline and frame-rate-independence audit are still outstanding.

This document is a target and acceptance contract, **not evidence that the runtime already meets it**.
