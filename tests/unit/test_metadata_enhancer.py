"""Tests for the deterministic metadata merge."""

from backend.agent.metadata_enhancer import MetadataEnhancer

VALID_UPC = "673799371011"  # check digit verified


def merge(existing, new, confidence=0.8):
    return MetadataEnhancer().enhance_metadata(existing, new, confidence)


def test_empty_new_metadata_returns_existing():
    existing = {"artist": "A", "title": "T"}
    merged, confidence, changes = merge(existing, {})
    assert merged == existing and confidence == 0.8 and changes == []


def test_artist_and_title_keep_existing_on_conflict():
    merged, confidence, changes = merge(
        {"artist": "Die Sterne", "title": "Für Anfänger"},
        {"artist": "Die Sterne", "title": "Was hat dich bloß so ruiniert"},
    )
    assert merged["title"] == "Für Anfänger"
    assert any("conflict" in change for change in changes)
    assert confidence < 0.8


def test_agreement_raises_confidence_and_capitalisation_is_not_a_conflict():
    _, confidence, changes = merge(
        {"artist": "Dimitri From Paris", "title": "After The Playboy Mansion", "year": 2002, "label": "Virgin"},
        {"artist": "Dimitri from Paris", "title": "After the Playboy Mansion", "year": 2002, "label": "Virgin"},
    )
    assert confidence > 0.8
    assert not any("conflict" in change for change in changes)


def test_year_and_label_only_fill_gaps():
    merged, _, _ = merge({"year": 2006, "label": "Verve"}, {"year": 1961, "label": "Other"})
    assert (merged["year"], merged["label"]) == (2006, "Verve")
    merged, _, _ = merge({"year": None, "label": "Unknown"}, {"year": 2012, "label": "Materie Records"})
    assert (merged["year"], merged["label"]) == (2012, "Materie Records")


def test_catalog_number_is_appended_once():
    merged, _, _ = merge({"catalog_number": "63881-27001-1"}, {"catalog_number": "S160"})
    assert merged["catalog_number"] == "63881-27001-1 / S160"
    again, _, _ = merge(merged, {"catalog_number": "S160"})
    assert again["catalog_number"] == merged["catalog_number"]
    same, _, _ = merge({"catalog_number": "MAT 04110 MLP"}, {"catalog_number": "MAT04110MLP"})
    assert same["catalog_number"] == "MAT 04110 MLP"


def test_barcode_needs_valid_check_digit():
    merged, _, _ = merge({"artist": "A"}, {"barcode": VALID_UPC})
    assert merged["barcode"] == VALID_UPC
    merged, _, _ = merge({"artist": "A"}, {"barcode": "6737991371011"})
    assert not merged.get("barcode")


def test_invalid_stored_barcode_is_replaced_or_dropped():
    merged, _, _ = merge({"barcode": "4019593737993"}, {"barcode": VALID_UPC})
    assert merged["barcode"] == VALID_UPC
    merged, _, _ = merge({"barcode": "4019593737993"}, {"barcode": None})
    assert merged["barcode"] is None


def test_valid_stored_barcode_is_kept():
    merged, _, _ = merge({"barcode": "724384260729"}, {"barcode": VALID_UPC})
    assert merged["barcode"] == "724384260729"


def test_genres_are_merged_without_duplicates():
    merged, _, _ = merge({"genres": ["Rock", "Indie Rock"]}, {"genres": ["rock", "Alternative"]})
    assert merged["genres"] == ["Rock", "Indie Rock", "Alternative"]


def test_condition_takes_worst_assessment_with_its_notes():
    merged, _, _ = merge(
        {"condition": "Near Mint (NM)", "condition_notes": "clean"},
        {"condition": "Very Good Plus (VG+)", "condition_notes": "light ring wear"},
    )
    assert merged["condition"] == "Very Good Plus (VG+)"
    assert merged["condition_notes"] == "light ring wear"
    merged, _, _ = merge(
        {"condition": "Very Good (VG)", "condition_notes": "scuffs"},
        {"condition": "Mint (M)", "condition_notes": "perfect"},
    )
    assert merged["condition"] == "Very Good (VG)"
    assert merged["condition_notes"] == "scuffs"


def test_first_condition_is_taken_when_missing():
    merged, _, _ = merge({"artist": "A"}, {"condition": "Near Mint (NM)", "condition_notes": "sealed"})
    assert merged["condition"] == "Near Mint (NM)"
    assert merged["condition_notes"] == "sealed"


def test_does_not_mutate_inputs():
    existing = {"artist": "A", "genres": ["Rock"]}
    new = {"genres": ["Jazz"]}
    merge(existing, new)
    assert existing == {"artist": "A", "genres": ["Rock"]}
    assert new == {"genres": ["Jazz"]}
