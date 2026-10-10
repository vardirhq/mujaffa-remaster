from pathlib import Path

CONTROLLERS = (
    "workshop_audio_controller.decay",
    "workshop_spoiler_controller.decay",
    "workshop_exhaust_controller.decay",
    "workshop_wheels_controller.decay",
)


def test_shared_ticket_sequence_is_initialized():
    state = Path("scripts/workshop_state.decay").read_text(encoding="utf-8")
    assert 'Game.set("workshop.buy.ticket", 0.0)' in state
    assert 'Game.set("workshop.buy.settled", 0.0)' in state
    assert 'Game.set("workshop.buy.granted", 0.0)' in state


def test_all_purchase_controllers_allocate_globally():
    for filename in CONTROLLERS:
        source = Path("scripts", filename).read_text(encoding="utf-8")
        assert 'this.ticket = Game.get("workshop.buy.ticket", 0.0) + 1.0;' in source, filename
        assert 'this.ticket = this.ticket + 1.0;' not in source, filename
        assert 'Game.set("workshop.buy.ticket", this.ticket);' in source, filename
        assert 'Game.get("workshop.buy.settled", 0.0) != this.ticket' in source, filename


def test_transaction_is_only_settled_once():
    state = Path("scripts/workshop_state.decay").read_text(encoding="utf-8")
    assert 'if ticket > this.settled {' in state
    assert 'this.settled = ticket;' in state
