"""Score props based on edge, accuracy, recent performance, DTM."""
from __future__ import annotations
from typing import Literal, List
from scoring.models import ScoredProp
from unify.unify import UnifiedProp

def american_to_implied(odds: int) -> float:
    if odds is None:
        return 0.5
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)

def _calc_edge_score(edge: float) -> float:
    return min(10.0, max(0.0, edge * 100))

def _calc_accuracy_score(sample: int | None, min_sample: int = 10) -> float:
    if sample is None or sample < min_sample:
        return 5.0
    return min(10.0, (sample / 100) * 10)

def _calc_recent_score(l5: float | None, l10: float | None) -> float:
    if l5 is None and l10 is None:
        return 5.0
    l5_score = (l5 * 10) if l5 is not None else 5.0
    l10_score = (l10 * 10) if l10 is not None else 5.0
    return (l5_score * 0.6) + (l10_score * 0.4)

def _calc_dtm_score(dtm: float | None) -> float:
    if dtm is None:
        return 5.0
    return max(0.0, 10.0 - (abs(dtm) * 1.0))

def _assign_tier(score: float, p_blend: float, edge: float, num_signals: int, thresholds: dict) -> str:
    s = thresholds["S"]; a = thresholds["A"]; b = thresholds["B"]
    if (score >= s["MIN_SCORE"] and p_blend >= s["MIN_P"] and edge >= s["MIN_EDGE"] and num_signals >= 2):
        return "S"
    if (score >= a["MIN_SCORE"] and p_blend >= a["MIN_P"] and edge >= a["MIN_EDGE"]):
        return "A"
    if score >= b["MIN_SCORE"]:
        return "B"
    return "B"

def score_prop(unified: UnifiedProp, direction: Literal["OVER","UNDER"], weights: dict[str,float], tier_thresholds: dict, min_accuracy_sample: int = 10) -> ScoredProp:
    # Extract probs & metadata from unified
    if unified.pp_over_prob is not None:
        over_prob = unified.pp_over_prob
        under_prob = unified.pp_under_prob
        l5_rate = unified.pp_l5_over_rate
        l10_rate = unified.pp_l10_over_rate
        dtm = unified.pp_dtm
        accuracy_sample = unified.pp_accuracy_sample
        odds = unified.pp_over_odds if direction == "OVER" else unified.pp_under_odds
    else:
        over_prob = 0.5; under_prob = 0.5; l5_rate=None; l10_rate=None; dtm=None; accuracy_sample=None; odds=-110

    model_prob = over_prob if direction == "OVER" else under_prob
    implied_prob = american_to_implied(odds)
    edge = model_prob - implied_prob
    edge_percent = edge / implied_prob if implied_prob > 0 else 0.0

    if getattr(unified, "single_source", False):
        model_prob *= (1 - getattr(unified, "confidence_penalty", 0.0))
        edge = model_prob - implied_prob
        edge_percent = edge / implied_prob if implied_prob > 0 else 0.0

    edge_score = _calc_edge_score(edge)
    accuracy_score = _calc_accuracy_score(accuracy_sample, min_accuracy_sample)

    if direction == "OVER":
        recent_score = _calc_recent_score(l5_rate, l10_rate)
    else:
        l5_under = (1 - l5_rate) if l5_rate is not None else None
        l10_under = (1 - l10_rate) if l10_rate is not None else None
        recent_score = _calc_recent_score(l5_under, l10_under)

    dtm_score = _calc_dtm_score(dtm)

    total_score = (
        edge_score * weights["EDGE_WEIGHT"] +
        accuracy_score * weights["ACCURACY_WEIGHT"] +
        recent_score * weights["RECENT_WEIGHT"] +
        dtm_score * weights["DTM_WEIGHT"]
    ) * 10

    # Confluence
    signals = [unified.pp_over_prob, unified.pp_l5_over_rate, unified.pp_l10_over_rate]
    signals = [s for s in signals if s]
    p_blend = sum(signals) / len(signals) if signals else 0.5
    num_signals = len(signals)
    tier_edge = abs(p_blend - (unified.pp_over_prob or 0.5))
    tier = _assign_tier(total_score, p_blend, tier_edge, num_signals, tier_thresholds)

    # game date string
    gd = None
    if getattr(unified, "game_date", None):
        try:
            gd = unified.game_date.isoformat()
        except Exception:
            gd = str(unified.game_date)

    return ScoredProp(
        player_name=unified.player_name,
        stat_type=unified.stat_type,
        line=unified.line,
        sport=unified.sport,
        league=getattr(unified, "league", None),
        game_date=gd,
        direction=direction,
        model_prob=model_prob,
        implied_prob=implied_prob,
        edge=edge,
        edge_percent=edge_percent,
        edge_score=edge_score,
        accuracy_score=accuracy_score,
        recent_score=recent_score,
        dtm_score=dtm_score,
        total_score=total_score,
        tier=tier,
        sources=getattr(unified, "sources", []),
        single_source=getattr(unified, "single_source", True),
        confidence_adjusted=getattr(unified, "single_source", True),
        over_prob=over_prob,
        under_prob=under_prob,
        odds=odds,
        l5_rate=l5_rate,
        l10_rate=l10_rate,
        dtm=dtm,
        accuracy_sample=accuracy_sample
    )

def score_all_props(unified_props: List[UnifiedProp], weights: dict[str,float], tier_thresholds: dict, min_accuracy_sample: int = 10) -> List[ScoredProp]:
    scored = []
    for unified in unified_props:
        scored.append(score_prop(unified, "OVER", weights, tier_thresholds, min_accuracy_sample))
        scored.append(score_prop(unified, "UNDER", weights, tier_thresholds, min_accuracy_sample))
    return scored
