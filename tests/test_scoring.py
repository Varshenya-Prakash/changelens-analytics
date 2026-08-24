from app.services.scoring import level_for_score, score_change


def test_high_magnitude_pricing_change_scores_high():
    result = score_change(
        change_magnitude=0.8, primary_category="Pricing / Commercial", is_cosmetic=False
    )
    assert result.signal_score > 60
    assert result.signal_level in ("high", "critical")
    assert "Pricing / Commercial" in result.explanation


def test_cosmetic_change_is_penalized_to_noise_or_low():
    result = score_change(
        change_magnitude=0.1, primary_category="Layout / Cosmetic / Noise", is_cosmetic=True
    )
    assert result.signal_level in ("noise", "low")
    assert result.signal_score < 40


def test_zero_magnitude_other_category_is_low_signal():
    result = score_change(change_magnitude=0.0, primary_category="Other", is_cosmetic=False)
    assert result.signal_level in ("noise", "low")


def test_score_is_clamped_between_0_and_100():
    result = score_change(
        change_magnitude=1.0, primary_category="Funding / Financial Event", is_cosmetic=False
    )
    assert 0.0 <= result.signal_score <= 100.0


def test_level_thresholds_are_monotonic():
    assert level_for_score(0) == "noise"
    assert level_for_score(20) == "low"
    assert level_for_score(40) == "medium"
    assert level_for_score(65) == "high"
    assert level_for_score(90) == "critical"
