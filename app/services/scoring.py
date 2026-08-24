"""Signal scoring: turns a raw diff + classification into a transparent 0-100 score.

The scoring model is intentionally simple and fully explainable so a user can
trust and tune it:

  score = clamp(
      base_from_magnitude
      + category_weight_bonus
      - cosmetic_penalty
      + recency_bonus,
      0, 100
  )

All weights live in `CATEGORY_WEIGHTS` below so they are easy to find and
adjust without touching pipeline logic elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass

# Higher weight = more likely to represent real competitive intelligence.
CATEGORY_WEIGHTS: dict[str, float] = {
    "Pricing / Commercial": 1.0,
    "Funding / Financial Event": 1.0,
    "Leadership / Executive": 0.9,
    "Partnership / Acquisition": 0.9,
    "Product Launch / Product Update": 0.85,
    "Regulatory / Compliance": 0.75,
    "Hiring / Careers": 0.5,
    "Customer / Case Study": 0.45,
    "PR / News / Thought Leadership": 0.4,
    "Other": 0.3,
    "Layout / Cosmetic / Noise": 0.05,
}

COSMETIC_PENALTY = 25.0
MAGNITUDE_WEIGHT = 55.0  # how much of the 0-100 scale comes from raw change volume
CATEGORY_WEIGHT_SCALE = 45.0  # how much comes from category relevance

SIGNAL_LEVEL_THRESHOLDS: list[tuple[float, str]] = [
    (80.0, "critical"),
    (60.0, "high"),
    (35.0, "medium"),
    (15.0, "low"),
    (0.0, "noise"),
]


@dataclass
class ScoringResult:
    signal_score: float
    signal_level: str
    explanation: str


def level_for_score(score: float) -> str:
    for threshold, level in SIGNAL_LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return "noise"


def score_change(
    *,
    change_magnitude: float,
    primary_category: str,
    is_cosmetic: bool,
    recency_boost: float = 0.0,
) -> ScoringResult:
    """Compute a transparent signal score for a detected change.

    Args:
        change_magnitude: 0..1 share of text that changed.
        primary_category: the classifier's top category.
        is_cosmetic: whether the classifier flagged this as cosmetic/noise.
        recency_boost: optional 0..1 extra weight for e.g. an active org.
    """
    category_weight = CATEGORY_WEIGHTS.get(primary_category, CATEGORY_WEIGHTS["Other"])

    magnitude_component = change_magnitude * MAGNITUDE_WEIGHT
    category_component = category_weight * CATEGORY_WEIGHT_SCALE
    recency_component = recency_boost * 5.0

    raw_score = magnitude_component + category_component + recency_component

    penalty = COSMETIC_PENALTY if is_cosmetic else 0.0
    final_score = max(0.0, min(100.0, raw_score - penalty))
    level = level_for_score(final_score)

    explanation = (
        f"Base from change volume: {magnitude_component:.1f} "
        f"(magnitude {change_magnitude:.0%} x weight {MAGNITUDE_WEIGHT:.0f}). "
        f"Category relevance ({primary_category}): +{category_component:.1f} "
        f"(weight {category_weight:.2f} x {CATEGORY_WEIGHT_SCALE:.0f}). "
        + (f"Recency/activity bonus: +{recency_component:.1f}. " if recency_component else "")
        + (f"Cosmetic penalty: -{penalty:.1f}. " if penalty else "")
        + f"Final score: {final_score:.1f}/100 -> {level}."
    )

    return ScoringResult(
        signal_score=round(final_score, 1), signal_level=level, explanation=explanation
    )


def recommendation_for(primary_category: str, signal_level: str) -> str:
    """A short, actionable recommendation shown alongside each alert."""
    if signal_level in ("noise", "low"):
        return "Low priority: log for context but no immediate action needed."

    playbook = {
        "Pricing / Commercial": "Review pricing/packaging positioning and brief sales on the change.",
        "Funding / Financial Event": "Assess competitive funding position; consider investor-facing talking points.",
        "Leadership / Executive": "Track leadership change for strategic direction shifts; update battlecards.",
        "Partnership / Acquisition": "Evaluate ecosystem impact and potential new competitive threats.",
        "Product Launch / Product Update": "Compare against roadmap; brief product team on competitive feature gap/parity.",
        "Regulatory / Compliance": "Check compliance posture; may signal new market entry or risk changes.",
        "Hiring / Careers": "Monitor hiring signal for expansion into new functions or markets.",
        "Customer / Case Study": "Note proof points being used in competitor's sales narrative.",
        "PR / News / Thought Leadership": "Review messaging themes for shifts in market narrative.",
    }
    return playbook.get(
        primary_category,
        "Review the change for competitive relevance and share with stakeholders if material.",
    )
