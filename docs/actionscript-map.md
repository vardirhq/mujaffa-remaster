# Original ActionScript map

This is the first behaviour map extracted from the Norwegian 1.6 SWF. It is
based on metadata disassembly only. `tools/swf_actions.py` does **not** execute
ActionScript, so everything marked as an inference still needs to be confirmed
against the original game before it becomes remaster behaviour.

## Scale of the original logic

The main timeline contains:

- 67 `DoAction` blocks
- 3,051 ActionScript 1/2 action records
- 340 unique literal strings
- 1,008 `Push` actions
- 378 `GetVariable` and 333 `SetVariable` actions
- 200 conditional `If` actions and 72 unconditional `Jump` actions
- 36 `RandomNumber` actions
- 60 direct `GotoFrame` actions and 9 `GoToLabel` actions

So the original is not just a long animation with a few click handlers. A
substantial amount of game state lives in timeline ActionScript.

## Confirmed state vocabulary

The action blocks expose a useful set of original state names. These should be
preserved in the parity specification even if the new implementation eventually
uses nicer internal names.

### Player / run state

- `cool`
- `cool_old`
- `energi`
- `penge`
- `respect`
- `level`
- `bane`
- `koert`
- `topTime`

### Car state

The original tracks most upgrades as both a selected value and a `_cool`
contribution:

- `farve`, `farve_cool`
- `daek`, `daek_cool`
- `hjulkapsel`, `hjulkapsel_cool`
- `spoiler`, `spoiler_cool`
- `udstodning`, `udstodning_cool`
- `vinduer`, `vinduer_cool`
- `soltag`, `soltag_cool`
- `forrude`, `forrude_cool`
- `indtraek`, `indtraek_cool`
- `horn`, `horn_cool_`
- `nummerplade`, `nummerplade_cool`
- `speaker_front`, `speaker_front_cool`
- `speaker_side`, `speaker_side_cool`
- `speaker_rear`, `speaker_rear_cool`
- `speaker_woofer`, `speaker_woofer_cool`

This strongly suggests that the garage can be modelled as authored upgrade data
rather than hard-coded one-off buttons in the remaster.

## High-value timeline landmarks

These frames contain especially dense or recognisable logic and are good first
targets for deeper decompilation:

| Frame | Nearby label | What the literals indicate |
| ---: | --- | --- |
| 1 | — | version initialization (`version 1.6`) |
| 188 | `speakDone` | welcome/loading transition |
| 200 | — | `initGame` dispatch |
| 202 | — | large game-state/car initialization block |
| 338 | `nørrebro` | level completion routing |
| 368 | — | route/level label selection for all three routes |
| 529 | — | score/status calculation and street-cred result text |
| 530–549 | — | status tiers 1–5 |
| 582 | — | car-card / serialized car appearance state |
| 597 | — | human-readable car description builder |
| 616–694 | — | high-score loading, display and submission |
| 721–743 | — | garage exit, broke/repair handling and cool updates |
| 745 | — | second car-description/update block |
| 794 | — | large live-game state blocks, car pieces and encounters |
| 806–809 | — | gameplay object initialization and level-label routing |

Frame numbers are main-timeline frames, starting at 1.

## Original online services

The SWF contains hard-coded NRK-era score endpoints:

- `vis_laveste_poeng.asp`
- `vis_plassering.asp`
- `lagre_plassering_ny.asp`

It also contains a `veldig_hemmelig_kode` field and old player/high-score
variables such as `spillernavn`, `spillerEpost`, `poeng`, `laveste_poeng`,
`score1`–`score5`, `navn1`–`navn5` and `email1`–`email5`.

The remaster must **not** contact these historical endpoints. They are reference
behaviour only. For initial parity work, high scores should be local/offline and
the network boundary should be represented explicitly so it can be replaced by
a new service only if that is ever wanted and legally appropriate.

## What to reverse-engineer next

The next useful step is not rendering yet. It is to turn the dense action blocks
at frames 202, 368, 529, 597, 674, 721, 794 and 809 into small behaviour tables:
inputs, variables read, variables written, random choices and destination
frames/labels. Once those tables exist we can implement the same state machine
in Decay and test it independently of graphics.
