# Mujaffa parity specification

This document is the implementation contract for the first remaster milestone.
It deliberately separates **confirmed original behaviour**, **strong inference**,
and **still-to-verify details** so we do not accidentally turn guesses into game
rules simply because they were written down once.

The source of truth remains `mujaffa_3juni_2003.swf`. The analysis tools under
`tools/` exist to make facts from that file reproducible.

## Goal

The first playable version should reproduce the Norwegian 1.6 game's behaviour
before changing its design. New graphics, higher resolution, modern input and a
modern shell are allowed; game rules are not.

A parity implementation is successful when the same authored starting state and
the same deterministic random stream produce the same route decisions, upgrade
state, score/status result and end state as the original.

## Evidence levels

- **Confirmed**: directly observable in SWF structure or ActionScript metadata.
- **Inferred**: strongly indicated by control flow, naming or repeated patterns,
  but still needs runtime confirmation against the original.
- **Unknown**: deliberately not specified yet.

Unknown values must not be filled with "reasonable" replacements. That is how a
faithful remaster slowly becomes somebody's memory of a game from 2003.

## Global game state

### Confirmed fields

| Original name | Meaning | Remaster representation |
| --- | --- | --- |
| `cool` | current style/cool score | integer game-state field |
| `cool_old` | cool before the current gameplay segment | integer snapshot |
| `energi` | energy/health-like run resource | integer game-state field |
| `penge` | money | integer currency field |
| `respect` | respect/street-cred state | integer game-state field |
| `level` | selected gameplay level | explicit enum/string |
| `bane` | route/track state | explicit enum/string |
| `koert` | driven/progress state | integer/boolean pending confirmation |
| `topTime` | time threshold/reference | numeric field pending unit confirmation |

The implementation may use English internal names, but the original names must
remain documented aliases in tests and reference data.

## Car / garage state

The original independently stores the selected variant and a cool contribution
for most cosmetic upgrades. The remaster should model each upgrade as data, not
as bespoke button code.

Confirmed categories:

| Category | Original value | Original cool contribution |
| --- | --- | --- |
| Paint | `farve` | `farve_cool` |
| Tyres | `daek` | `daek_cool` |
| Wheel covers/rims | `hjulkapsel` | `hjulkapsel_cool` |
| Spoiler | `spoiler` | `spoiler_cool` |
| Exhaust | `udstodning` | `udstodning_cool` |
| Windows | `vinduer` | `vinduer_cool` |
| Sunroof | `soltag` | `soltag_cool` |
| Windscreen | `forrude` | `forrude_cool` |
| Interior | `indtraek` | `indtraek_cool` |
| Horn | `horn` | `horn_cool_` |
| Number plate | `nummerplade` | `nummerplade_cool` |
| Front speakers | `speaker_front` | `speaker_front_cool` |
| Side speakers | `speaker_side` | `speaker_side_cool` |
| Rear speakers | `speaker_rear` | `speaker_rear_cool` |
| Woofer | `speaker_woofer` | `speaker_woofer_cool` |

### Required model

Each authored upgrade entry must eventually provide at least:

```text
id
category
original_value
price
cool_delta
visual_variant
availability/rule
```

`price`, `cool_delta` and availability values remain **unknown until extracted or
verified**. No placeholder balance values should ship in a parity build.

## Main state machine

### Confirmed top-level flow

```text
boot
  -> welcome/instructions
  -> game initialization
  -> route selection / route traversal
  -> gameplay level
  -> crash | incomplete | complete
  -> status result
  -> garage/showroom
  -> continue/next route or ending
```

The SWF also contains credits, advertisement/card screens and high-score flow.
Those are secondary to the first gameplay parity slice but are part of full
parity.

### Route labels

Route 1:

```text
bane1_start
bane1_grønland
bane1_grunerløkka
bane1_sinsen
```

Route 2:

```text
bane2_start
bane2_grønland
bane2_rådhusplassen
bane2_bislett
bane2_sinsen
```

Route 3:

```text
bane3_start
bane3_grønland
bane3_rådhusplassen
bane3_frogner
bane3_holmenkollen
bane3_sinsen
```

The original SWF contains the typo-like frame label `abne3_grønland` while the
ActionScript vocabulary contains `bane3_grønland`. Preserve that discrepancy in
reference notes; do not silently normalize source evidence.

## Level routing

**Confirmed:** the original uses `level1`, `level2` and `level3` labels and has a
late routing block at frame 809 which sends those values to separate gameplay
sections. Unknown/invalid values fall through to another frame rather than being
accepted as a fourth level.

**Inferred:** level selection and route selection are distinct dimensions. Do not
collapse them into a single stage ID until runtime verification proves that is
safe.

## Gameplay initialization

Frame 794 resets a large set of per-run/per-road fields before gameplay. The
confirmed vocabulary includes:

```text
gummiSafe
pickup
speed
cool_old
bil
dansk_pige
fetter
kondom
person
domi
danskpige
fettercount
vej_over
vej_over2
vej_kondom
vej_person
vej_dyr
vej_nr
vej_domi
koert
fetter_1..4
pige_1..3
```

The same block performs random-number operations for several encounter/person
variables. Exact ranges and their gameplay effects remain to be extracted.

### Deterministic randomness requirement

The remaster must route gameplay randomness through one injectable RNG service.
Parity tests need to be able to provide a fixed sequence. Calling a platform
random function directly from scene or UI code is not acceptable.

## Score and status

**Confirmed:** frame 529 performs score/status calculation and frames 530-549
represent five status tiers, matching the labels `1` through `5`.

**Unknown:** exact thresholds and formula.

The first implementation should expose score calculation as a pure/testable
function or Decay-equivalent state transition. Status text/rendering must not own
the formula.

## Garage behaviour

**Confirmed:** frames 721-743 contain garage exit, insufficient-money/repair
handling and cool updates. Frames 582, 597 and 745 build or apply car appearance
and description state.

### Required separation

```text
Garage catalogue data
        |
        v
Purchase rules ----> Game state
        |                |
        v                v
UI presentation     Car visual state
```

A button must not contain the price or cool value as its own private rule.
Otherwise every future art/UI replacement risks changing gameplay.

## High scores

The original contains NRK-era network endpoints and player/email fields.

For parity development:

- no historical endpoint may be contacted;
- the score-service boundary must be replaceable;
- local/offline storage is the default substitute;
- network parity is explicitly out of scope unless a new authorized service is
  created later.

## Rendering independence

Gameplay state must not depend on whether the game is using classic/reference
visuals or remastered visuals. The intended boundary is:

```text
Original-compatible game state + rules
                 |
          scene/view model
          /              \
 classic/reference     remastered
    renderer            renderer
```

This is what will eventually make side-by-side parity captures and a classic /
remastered presentation toggle possible without maintaining two games.

## First vertical-slice acceptance criteria

Before expanding into the whole game, one slice should prove the architecture:

1. project opens and exports while living outside `sindri2`;
2. one route/level can be entered from an initialized game state;
3. run state is initialized through one state owner rather than scattered scene
   values;
4. randomness can be seeded/injected for tests;
5. the run can finish into one of the original result states;
6. result calculation is independent from result-screen presentation;
7. the garage can read at least one authored upgrade category without embedding
   its balance values in UI code;
8. changing presentation assets does not change any state-transition test;
9. the original SWF is never copied to an exported build.

## Things we explicitly refuse to invent yet

The following remain blocked on deeper extraction/runtime confirmation:

- starting money, energy, cool and respect values;
- upgrade prices and cool deltas;
- score/status thresholds;
- encounter probabilities and random ranges;
- speed/timing values and their units;
- exact crash/incomplete/complete conditions;
- repair costs and insufficient-money behaviour;
- route unlock/progression rules.

That list is intentional. Every item removed from it should be accompanied by
source evidence or a reproducible observation from the original game.
