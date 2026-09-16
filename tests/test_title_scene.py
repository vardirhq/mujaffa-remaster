import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_title_is_the_project_entry_scene():
    manifest = (ROOT / "sindri.toml").read_text(encoding="utf-8")
    assert 'main_scene = "title.scene.json"' in manifest
    assert 'scenes = ["main.scene.json"]' in manifest


def test_title_scene_owns_navigation_into_gameplay():
    scene = json.loads((ROOT / "title.scene.json").read_text(encoding="utf-8"))
    by_name = {entity["name"]: entity for entity in scene["entities"]}
    assert "Title Start" in by_name
    assert "sindri.ui.button" in by_name["Title Start"]["components"]
    controller = by_name["Title Controller"]["components"]["sindri.script"]
    assert controller["source"] == "scripts/title.decay"
    assert controller["script"] == "Title"

    source = (ROOT / "scripts/title.decay").read_text(encoding="utf-8")
    assert 'Scene.go("main.scene.json")' in source
