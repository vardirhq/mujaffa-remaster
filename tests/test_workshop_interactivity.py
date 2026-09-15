from tools.workshop_catalog import CATEGORIES

def test_interactivity_foundation():
    ids = [f"workshop-category-{entry['id']}" for entry in CATEGORIES]
    assert len(ids) == len(set(ids)) == 13
    assert all("price" not in entry for entry in CATEGORIES)
