# Mujaffa Remaster

A modern remaster/reimplementation of the Norwegian Mujaffa game, built as a
standalone [Sindri Engine](https://github.com/vardirhq/sindri2) project.

The project is currently in **parity-first** development: behaviour from the
Norwegian 1.6 SWF is recovered and reproduced before presentation is redesigned.
The original SWF is reference material and must never be copied into exported
builds.

## Development model

Keep the two repositories as sibling checkouts:

```text
workspace/
├── sindri2/
└── mujaffa-remaster/
```

Open the project from the Sindri checkout with:

```bash
cd sindri2
cargo run --package sindri-editor -- ../mujaffa-remaster
```

The project root is defined by `sindri.toml`; the editor discovers
`main.scene.json`, project-local assets, Decay scripts and future Weave styles
from that root.

## Current playable parity slice

The current development slice is intentionally visualized with simple debug
geometry rather than replacement art.

- `1`, `2`, `3` choose one of the three original level destinations.
- `Space` advances route select -> run -> result -> route select.
- `R` resets the game state.

The slice already reproduces confirmed original initialization values, frame-794
run resets/random encounter ranges and the five frame-529 street-cred status
thresholds. See `docs/first-playable-slice.md` and `docs/parity-fixtures.md` for
the evidence contract.

## Engine pin

`.sindri-engine` contains the exact Sindri commit this project was last verified
against. This is deliberately a development pin, not a semver compatibility
promise.

CI checks out that revision independently and verifies that the external project
can still be exported by Sindri without living inside the engine repository.

## Web build

`main` is exported through Sindri and deployed to GitHub Pages. Pull requests
build the same browser payload without deploying it, including a guard that
fails if a `.swf` reference file enters the exported artifact.

## Reference material

`mujaffa_3juni_2003.swf` is currently kept in the repository as parity reference
material while the project is young. It is not an authored Sindri asset and is
explicitly excluded from distributable exports.
