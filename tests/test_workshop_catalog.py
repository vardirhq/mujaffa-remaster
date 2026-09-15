from tools.workshop_catalog import CATEGORIES, BY_ID, labels

def test_original_workshop_catalog():
    assert len(CATEGORIES) == 13
    assert len(BY_ID) == 13
    assert labels() == [
        "LAKKERING", "BILSTEREO", "SPOILER", "EKSOSANLEGG", "FELGER", "DEKK",
        "RUTER", "SOLTAK", "NUMMERSKILT", "SETETREKK", "BILNIPS", "BÅT-HORN", "BMW CAM",
    ]
