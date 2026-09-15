#!/usr/bin/env python3
"""Canonical workshop catalogue shared by scene-generation tooling."""
CATEGORIES = [
    {"id": "paint", "label": "LAKKERING", "state": "paint"},
    {"id": "audio", "label": "BILSTEREO", "state": "audio"},
    {"id": "spoiler", "label": "SPOILER", "state": "spoiler"},
    {"id": "exhaust", "label": "EKSOSANLEGG", "state": "exhaust"},
    {"id": "rims", "label": "FELGER", "state": "rims"},
    {"id": "tyres", "label": "DEKK", "state": "tyres"},
    {"id": "windows", "label": "RUTER", "state": "windows"},
    {"id": "sunroof", "label": "SOLTAK", "state": "sunroof"},
    {"id": "plate", "label": "NUMMERSKILT", "state": "plate"},
    {"id": "interior", "label": "SETETREKK", "state": "interior"},
    {"id": "trinket", "label": "BILNIPS", "state": "trinket"},
    {"id": "horn", "label": "BÅT-HORN", "state": "horn"},
    {"id": "camera", "label": "BMW CAM", "state": "camera"},
]
BY_ID = {entry["id"]: entry for entry in CATEGORIES}

def labels():
    return [entry["label"] for entry in CATEGORIES]

def validate():
    assert len(CATEGORIES) == 13
    assert len(BY_ID) == 13

if __name__ == "__main__":
    validate()
    print("workshop catalogue: 13 original categories")
