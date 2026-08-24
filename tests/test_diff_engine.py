from app.services.diff_engine import compute_diff


def test_identical_text_has_zero_magnitude_and_full_similarity():
    text = "Welcome to our site.\nWe offer great products."
    diff = compute_diff(text, text)
    assert diff.similarity_score == 1.0
    assert diff.change_magnitude == 0.0
    assert diff.added_text == ""
    assert diff.removed_text == ""


def test_added_line_is_captured():
    old = "Welcome to our site."
    new = "Welcome to our site.\nWe just raised a Series B round."
    diff = compute_diff(old, new)
    assert "Series B" in diff.added_text
    assert diff.removed_text == ""
    assert diff.change_magnitude > 0
    assert diff.similarity_score < 1.0


def test_removed_line_is_captured():
    old = "Welcome to our site.\nLegacy notice: service ending soon."
    new = "Welcome to our site."
    diff = compute_diff(old, new)
    assert "Legacy notice" in diff.removed_text
    assert diff.added_text == ""


def test_magnitude_scales_with_relative_change_volume():
    small_base = "Hello world."
    small_change = compute_diff(
        small_base, small_base + "\nBig pricing change announced today across all plans."
    )

    large_base = "Hello world. " * 200
    large_change = compute_diff(
        large_base, large_base + "\nBig pricing change announced today across all plans."
    )

    # The same absolute addition represents a much larger share of a small page.
    assert small_change.change_magnitude > large_change.change_magnitude


def test_diff_summary_is_human_readable_and_nonempty():
    old = "A"
    new = "A\nB"
    diff = compute_diff(old, new)
    assert "Added" in diff.diff_summary
