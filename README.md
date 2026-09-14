# Mujaffa Remaster

Private experimental remaster project built with [Sindri Engine](https://github.com/vardirhq/sindri2).

This repository is intentionally separate from the Sindri monorepo. During Sindri's pre-alpha stage it targets one exact engine commit, recorded in `.sindri-engine`, rather than claiming compatibility with a released SDK.

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

The project root is defined by `sindri.toml`; the editor should discover `main.scene.json`, project-local assets, Decay scripts and Weave styles from that root.

## Engine pin

`.sindri-engine` contains the exact Sindri commit this project was last verified against. This is deliberately a development pin, not a semver compatibility promise.

CI checks out that revision independently and verifies that the external project can still be exported by Sindri without living inside the engine repository.

## Reference material

`mujaffa_3juni_2003.swf` is kept as private reference material for parity analysis. It is not part of the authored Sindri scene and should not be copied into distributable builds.

## Status

Bootstrap only. The first milestone is proving the external-project boundary before remaster gameplay work begins.
