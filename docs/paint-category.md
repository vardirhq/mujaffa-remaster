# LAKKERING functional slice

The first workshop category is now an actual interaction slice rather than baked decoration.

- `skift` is a visible `sindri.ui.image` + `sindri.ui.button` and cycles the five paint states already used by the layered BMW prototype.
- The five Fartstripe swatches (original buttons 177/168/172/164/160) each cost 250 kr through the shared till, worth 0.1 BMW cred; removing the stripe takes the 0.1 back. The fitted swatch has no button, and its `fartstribe` frame draws the tick.
- The panel pictures, ticks and price tags come from `tools/install_workshop_panels.py` and `scripts/workshop_panel_art.decay`; `workshop.paint.mixing` hides LAKKERING's picture while the RGB mixer is open.
- Paint and stripe selections are mirrored to `Game` as `workshop.paint` and `workshop.stripe` so later showroom/driving work can consume the same BMW state.
- Controls use the same fixed-stage viewport scaling as the category rail and therefore remain aligned on portrait touch screens.
- Paint controls are deactivated whenever another workshop category is selected.

The exact original SWF colour-transform/economy values are intentionally not claimed here. The controller isolates the current five-colour palette so recovered values can replace it without changing the UI or state contract.
