"""Correlation analysis for Champions lineups."""
from __future__ import annotations
from scoring.models import ScoredProp

def calculate_correlation_index(props: list[ScoredProp], penalties: dict[str,float]) -> float:
    if len(props) < 2:
        return 0.0
    total_penalty = 0.0
    comparisons = 0
    for i in range(len(props)):
        for j in range(i + 1, len(props)):
            p1, p2 = props[i], props[j]
            # Simplified: penalty if same sport & same game day
            if p1.sport == p2.sport and p1.game_date == p2.game_date:
                total_penalty += penalties.get("SAME_GAME_PENALTY", 0.25)
            comparisons += 1
    return min(1.0, max(0.0, total_penalty / comparisons)) if comparisons > 0 else 0.0
