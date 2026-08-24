from app.services.classifier import classify_change


def test_classifies_pricing_change():
    primary, matches, is_cosmetic = classify_change(
        added_text="Our new pricing starts at $99 per month with a free trial.",
        removed_text="",
    )
    assert primary == "Pricing / Commercial"
    assert not is_cosmetic
    assert any(m.name == "Pricing / Commercial" for m in matches)


def test_classifies_leadership_change():
    primary, matches, _ = classify_change(
        added_text="We are pleased to announce Jane Doe has been appointed as our new Chief Executive Officer.",
        removed_text="",
    )
    assert primary == "Leadership / Executive"


def test_classifies_hiring_change():
    primary, _, _ = classify_change(
        added_text="We're hiring! Check out our new job openings and apply now.",
        removed_text="",
    )
    assert primary == "Hiring / Careers"


def test_cosmetic_change_flagged():
    primary, _, is_cosmetic = classify_change(
        added_text="We updated our footer links and fixed a typo on this page.",
        removed_text="",
    )
    assert is_cosmetic is True


def test_no_matches_defaults_to_other():
    primary, matches, is_cosmetic = classify_change(added_text="   ", removed_text="   ")
    assert primary == "Other"
    assert matches == []
    assert is_cosmetic is False


def test_multiple_categories_can_match_and_primary_is_highest_confidence():
    primary, matches, _ = classify_change(
        added_text=(
            "We are excited to announce a new strategic partnership and a Series B funding round "
            "of $40M led by a top investor."
        ),
        removed_text="",
    )
    names = {m.name for m in matches}
    assert "Funding / Financial Event" in names
    assert "Partnership / Acquisition" in names
    assert primary in names
