# Title screen parity

The original Flash title flow and the future remastered title are deliberately separate presentations of the same navigation boundary.

## Classic reference

The classic presentation is a parity target for `mujaffa_3juni_2003.swf`:

- 500 × 500 stage
- 12 FPS timing where the original timeline animation matters
- original vector/text/button artwork recovered from the SWF rather than redrawn from memory
- original `start` → `velkommen` → `speakDone` / navigation flow preserved until the exact button/action mapping has been recovered
- no responsive rearrangement inside the classic presentation

### Visual acceptance reference

The classic reconstruction is judged against the supplied captured 500 × 500 original-player frame, not against a modernized interpretation. The opening composition contains the original `Mujaffa Spillet` wordmark and version label at upper left, the Falafel storefront at upper right, the blue BMW across the lower middle, Mujaffa in the left foreground, the woman on the right pavement, and the cyan navigation strip along the bottom. `START SPILLET` and `INSTRUKSJONER` belong inside that strip.

Do not substitute generic UI controls, a flat placeholder background, approximate typography, or newly drawn character/car silhouettes and call that classic parity. If an original visual cannot yet be recovered faithfully, keep that part explicitly incomplete instead of inventing it.

The browser/page shell around the 500 × 500 movie is not part of the title artwork. Mobile emulator controls, fullscreen/language controls, and the surrounding webpage are reference-player chrome only.

## Evidence pipeline

`tools/swf_title_reference.py` is the title-specific source-of-truth extractor. It now recovers:

- the six known opening timeline labels and their frames
- exported/named character IDs where the SWF exposes names
- title-relevant SWF primitive counts
- main-timeline placement/removal events through the opening flow
- character IDs, depth, move semantics, placement matrices, instance names, ratios, clip depth and color transforms
- resolved display-list snapshots at every opening navigation label
- a character-definition index classifying placed objects as shape, text, edit text, button or sprite
- `DefineSprite` frame counts and nested placement/removal/label timelines

The next extraction boundary is **shape, text and button definition contents**, followed by recursive transform composition from the nested sprite timelines. Once those are decoded, the extractor can emit renderable original-derived title primitives rather than opaque character IDs.

Do not manually transcribe coordinates from the screenshot when the SWF can supply them. The screenshot is for visual acceptance and identifying the intended title state; the SWF remains the authoritative geometry/timeline source.

## Remastered presentation

The remastered title will **not** inherit the 500 × 500 constraint. It will be a responsive full-viewport presentation that can recompose for portrait phones, tablets, desktop, and ultrawide displays. It may replace artwork, typography, animation, and layout while keeping the same semantic navigation actions.

Do not make the classic title responsive merely to reuse it. The shared contract is navigation/state, not coordinates or artwork.

## Implementation boundary

Title-screen code should expose semantic actions such as `start_game`, `instructions`, and any other actions proven by the SWF. Presentation entities should call those actions without owning workshop economy or gameplay state.

The title work must not read or rewrite `reference/original-workshop-data.json`. The workshop economy extractor can therefore evolve independently on its own branch.

## Parity workflow

1. Recover the opening timeline labels, frame ranges, placed characters, text, buttons, and action targets from the SWF.
2. Store recovered title facts in title-specific extractor output.
3. Recursively decode placed sprites and their vector/text/button definitions.
4. Reconstruct the classic 500 × 500 presentation from those facts.
5. Add browser captures/tests against the classic presentation.
6. Only after classic parity is stable, build the responsive remastered presentation against the same semantic navigation contract.

## What the classic title is, as recovered

The opening is not one screen. `swf_title_reference.py` recovers the evidence
and `swf_title_extract.py` composes it into the six screens the original settles
on.

**The title** is main-timeline frame 188, `speakDone`. Frames 187–189 loop there
forever, which is where the original waits for the player. Its preloader sprite
has to be advanced to its own `done` label by hand, because the SWF advances it
from ActionScript once loading finishes rather than from the timeline — and
`done` is the frame that places the two menu buttons.

**The instructions** are frames 330–334: five pages, each reached by the
original's own Next and Previous buttons. Frame 330 stops, and every frame in the
run is a settled screen in its own right.

### Navigation is recovered, not assumed

A control's action comes from disassembling that button's own release handler:

| Original character | Handler | Action |
| --- | --- | --- |
| 49 | `call("gotoGame")` | `start_game` |
| 54 | `call("gotoInstruktioner")` | `instructions` |
| 434 | `nextFrame()` | `next_page` |
| 460 | `prevFrame()` | `previous_page` |
| 491 | `call("gotoGame")` | `start_game` |

`start_game` goes straight to `main.scene.json`. The original plays a driving
sequence between the title and the workshop; that is gameplay presentation
rather than title navigation, and it is deliberately not in the way of reaching
the garage.

### The title moves

Frames 10–188 are Mujaffa's welcome: the main timeline swaps his mouth and his
gesturing arm frame by frame until the loop settles. Inside the preloader, the
"TRYKK PÅ EN KNAPP" prompt fades out and back in forever on its own 21-frame
clip. Both are recovered as sprite-sheet animation at the original 12 FPS rather
than flattened into the backdrop — a title screen that has stopped moving is the
one thing every player of the original would notice.

A clip names one cell per original frame, and cells are deduplicated by the
geometry they draw, so the original's irregular hold times survive exactly
without a sheet full of copies.

Mujaffa's own sprite carries a second copy of that performance on a 66-frame
loop. It is held at its setup frame, because the main timeline draws the moving
mouth and arm over the top of it either way.

**Not yet recovered:** the opening's music and speech audio, and the driving
sequence between the title and the workshop.

### Colour is part of the evidence

A style-change record carrying new styles *replaces* the shape's style arrays,
and every index after it is 1-based into the replacement. `swf_art_extract.py`
used to append instead, which is why the recovered characters came out wearing
the colours of whatever was drawn before their last style reset. Placement
colour transforms and the stage background colour matter for the same reason:
the skyline is black at 60% over white, so dropping either makes it the wrong
colour rather than merely a darker one.

## How the title scene is built

```bash
python tools/swf_art_extract.py mujaffa_3juni_2003.swf reference-art --scale 4
PYTHONPATH=tools python tools/swf_title_extract.py \
  mujaffa_3juni_2003.swf reference-art assets/generated/title --scale 2
python tools/install_title_scene.py --project .
```

The artwork is generated and not committed, for the same licensing reason the
rest of the extracted art is not. `title.scene.json` **is** committed, and CI
regenerates it and fails on any difference: the scene in the repository is the
SWF's opening, not a redraw of it that has drifted.

Each screen is one world sprite on the fixed 500 × 500 stage. Each control is
three sprites — the original's idle, hover-caption and pressed drawings — plus a
transparent UI button carrying that button's own hit-test rect. Hit areas follow
the hit records rather than the artwork, because the original's red hover
captions are wider than their buttons and overlap the neighbour.
