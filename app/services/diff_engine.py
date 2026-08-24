"""Diff engine: compares two text snapshots and produces structured evidence.

Uses difflib.SequenceMatcher on normalized, noise-stripped text to compute a
similarity score plus added/removed text blocks and a concise human-readable
summary. Magnitude is expressed relative to total text volume so a one-line
tweak on a huge page doesn't look identical to a one-line tweak on a small one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.services.extractor import strip_ignored_patterns


@dataclass
class DiffResult:
    similarity_score: float  # 0..1, 1 = identical
    change_magnitude: float  # 0..1, share of text that changed
    added_text: str
    removed_text: str
    diff_summary: str
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)


def _line_diff(old_lines: list[str], new_lines: list[str]) -> tuple[list[str], list[str]]:
    matcher = SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    added: list[str] = []
    removed: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "delete"):
            removed.extend(old_lines[i1:i2])
        if tag in ("replace", "insert"):
            added.extend(new_lines[j1:j2])
    return added, removed


def _summarize(added: list[str], removed: list[str], max_items: int = 3) -> str:
    parts = []
    if added:
        preview = "; ".join(a[:120] for a in added[:max_items])
        more = f" (+{len(added) - max_items} more)" if len(added) > max_items else ""
        parts.append(f"Added: {preview}{more}")
    if removed:
        preview = "; ".join(r[:120] for r in removed[:max_items])
        more = f" (+{len(removed) - max_items} more)" if len(removed) > max_items else ""
        parts.append(f"Removed: {preview}{more}")
    if not parts:
        return "No textual differences detected."
    return " | ".join(parts)


def compute_diff(old_text: str, new_text: str) -> DiffResult:
    """Compute a structured diff between two page-text snapshots."""
    old_clean = strip_ignored_patterns(old_text or "")
    new_clean = strip_ignored_patterns(new_text or "")

    matcher = SequenceMatcher(a=old_clean, b=new_clean, autojunk=False)
    similarity = matcher.ratio()

    old_lines = [line for line in old_clean.splitlines() if line.strip()]
    new_lines = [line for line in new_clean.splitlines() if line.strip()]
    added_lines, removed_lines = _line_diff(old_lines, new_lines)

    total_len = max(len(old_clean) + len(new_clean), 1)
    changed_len = sum(len(a) for a in added_lines) + sum(len(r) for r in removed_lines)
    magnitude = min(changed_len / total_len, 1.0)

    return DiffResult(
        similarity_score=round(similarity, 4),
        change_magnitude=round(magnitude, 4),
        added_text="\n".join(added_lines),
        removed_text="\n".join(removed_lines),
        diff_summary=_summarize(added_lines, removed_lines),
        added_lines=added_lines,
        removed_lines=removed_lines,
    )
