# First playable parity slice

This slice is intentionally a mechanics proof, not the remaster presentation.
It exists to prove that a standalone Mujaffa project can reproduce confirmed
Norwegian 1.6 state transitions in Decay and run through Sindri's browser export.

## Controls

- `1`, `2`, `3`: choose one of the three original level destinations while in
  route-select state.
- `Space`: advance the slice: route select -> run -> result -> route select.
- `R`: reset to the original frame-202 starting state.

The coloured rectangles and result dots are temporary debug geometry. They are
not proposed replacement art.

## Confirmed values implemented

### Frame 202 initialization

The symbolic SWF report now recovers these exact starting values:

| Original variable | Value |
| --- | ---: |
| `level` | 1 |
| `goto_label` | `bane1_start` |
| `topTime` | 0 |
| `cool` | 0 |
| `speed` | 20 |
| `energi` | 1 |
| `bil_cool` | 1 |
| `koster` | 200 |
| `penge` | 5000 |

The slice currently carries the values that participate in its state machine.
Garage catalogue values will move into authored upgrade data rather than being
copied into UI code.

### Frame 794 run initialization

The original resets `bane`, encounter flags, road flags and `koert` before a run.
The slice reproduces those resets and the recovered encounter positions:

```text
fetter_1 = random(100) + 200
fetter_2 = random(200) + 500
fetter_3 = random(200) + 800
fetter_4 = random(200) + 900
pige_1   = random(200) + 200
pige_2   = random(150) + 600
pige_3   = random(100) + 900
```

Flash `RandomNumber(n)` returns an integer from `0` through `n - 1`. The Decay
port therefore uses inclusive `Random.int(0, n - 1)` calls rather than changing
the original range by one.

The run uses an authored deterministic seed for parity development. The seed is
a test boundary, not a claim that the 2003 game used a fixed seed.

### Frame 529 status tiers

The original result block maps `cool` directly into five tiers:

| Tier | Cool |
| ---: | --- |
| 1 | `< 200` |
| 2 | `200..599` |
| 3 | `600..1199` |
| 4 | `1200..2499` |
| 5 | `>= 2500` |

`tools/swf_variables.py` now preserves ActionScript boolean `And`/`Or`
expressions so these ranges appear in the generated analysis rather than being
hand-maintained folklore.

## Architecture proven by this slice

`GameState` remains the authoritative owner of parity state. The temporary
shapes are presentation only: changing or replacing them does not change route,
run initialization, random draws or result classification.

The slice also establishes the intended browser-development loop:

```text
original SWF evidence
       -> Decay parity state
       -> standalone Sindri project
       -> sindri-export
       -> GitHub Pages
```

## Still deliberately missing

This is not yet the original driving game. Encounter behaviour, route traversal,
energy effects, money rewards/costs, upgrades, repair behaviour and actual
street-cred gains still need to be recovered and implemented. `respect` also
remains unresolved as an initial value.

Those gaps stay gaps until the SWF gives us an answer. Filling them with values
that merely feel plausible would be quicker, and would also defeat the entire
point of doing a parity remaster.
