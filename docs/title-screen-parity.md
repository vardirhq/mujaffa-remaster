# Title screen parity

The original Flash title flow and the future remastered title are deliberately separate presentations of the same navigation boundary.

## Classic reference

The classic presentation is a parity target for `mujaffa_3juni_2003.swf`:

- 500 × 500 stage
- 12 FPS timing where the original timeline animation matters
- original vector/text/button artwork recovered from the SWF rather than redrawn from memory
- original `start` → `velkommen` → `speakDone` / navigation flow preserved until the exact button/action mapping has been recovered
- no responsive rearrangement inside the classic presentation

The SWF reference map already confirms `start`, `velkommen`, `speakDone`, `gotoInstruktioner`, `gotoGame`, and `initGame` as the opening navigation labels. Those labels are the source of truth for the classic state machine.

### Visual acceptance reference

The classic reconstruction is judged against a captured 500 × 500 original-player frame, not against a modernized interpretation. The opening composition contains the original `Mujaffa Spillet` wordmark and version label at upper left, the Falafel storefront at upper right, the blue BMW across the lower middle, Mujaffa in the left foreground, the woman on the right pavement, and the cyan navigation strip along the bottom. `START SPILLET` and `INSTRUKSJONER` belong inside that strip.

Do not substitute generic UI controls, a flat placeholder background, approximate typography, or newly drawn character/car silhouettes and call that classic parity. If an original visual cannot yet be recovered faithfully, keep that part of the reconstruction explicitly incomplete instead of inventing it.

The browser/page shell around the 500 × 500 movie is not part of the title artwork. Mobile emulator controls, fullscreen/language controls, and the surrounding webpage are reference-player chrome only.

## Remastered presentation

The remastered title will **not** inherit the 500 × 500 constraint. It will be a responsive full-viewport presentation that can recompose for portrait phones, tablets, desktop, and ultrawide displays. It may replace artwork, typography, animation, and layout while keeping the same semantic navigation actions.

Do not make the classic title responsive merely to reuse it. The shared contract is navigation/state, not coordinates or artwork.

## Implementation boundary

Title-screen code should expose semantic actions such as `start_game`, `instructions`, and any other actions proven by the SWF. Presentation entities should call those actions without owning workshop economy or gameplay state.

The title work must not read or rewrite `reference/original-workshop-data.json`. The workshop economy extractor can therefore evolve independently on its own branch.

## Parity workflow

1. Recover the opening timeline labels, frame ranges, placed characters, text, buttons, and action targets from the SWF.
2. Store recovered title facts in a title-specific reference file/tool output.
3. Reconstruct the classic 500 × 500 presentation from those facts.
4. Add browser captures/tests against the classic presentation.
5. Only after classic parity is stable, build the responsive remastered presentation against the same semantic navigation contract.
