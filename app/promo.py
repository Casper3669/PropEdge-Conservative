from __future__ import annotations
from typing import Dict, Any, List, Tuple
import copy
import pandas as pd

def _prod(p: List[float]) -> float:
    out = 1.0
    for x in p: out *= float(x)
    return out

def effective_payouts(cfg: Dict[str,Any]) -> Dict[str,Any]:
    """
    Return payouts after applying any active promo.
    - profit_boost: multiplies winning multipliers (perfect hits). By default we DO NOT boost 'one_miss' refunds.
    """
    base = copy.deepcopy(cfg["PAYOUTS"]["UNDERDOG"])
    promo = (cfg or {}).get("PROMO", {}) or {}
    if not promo.get("active"):
        return base

    ptype = promo.get("type")
    if ptype == "profit_boost":
        boost = float(promo.get("value", 0.0))
        if boost > 0:
            mult = 1.0 + boost
            # STANDARD (pure win multiples)
            for k, v in list(base["STANDARD"].items()):
                base["STANDARD"][k] = float(v) * mult
            # FLEX: boost "perfect" win multiple; do NOT boost "one_miss" unless explicitly allowed
            for k, v in list(base["FLEX"].items()):
                if isinstance(v, dict) and "perfect" in v:
                    v["perfect"] = float(v["perfect"]) * mult
                    if promo.get("boost_protected", False) and "one_miss" in v:
                        v["one_miss"] = float(v["one_miss"]) * mult
                elif isinstance(v, (int, float)):
                    base["FLEX"][k] = float(v) * mult
    return base

def _exactly_two_hits_prob(p1: float, p2: float, p3: float) -> float:
    return (p1*p2*(1-p3) + p1*p3*(1-p2) + p2*p3*(1-p1))

def ev_flex_multiple_3(p: List[float], payouts_flex: Dict[str,Any]) -> float:
    """3-leg flex: 3x for perfect; 1x for exactly two hits."""
    if len(p) < 3: return 0.0
    p1,p2,p3 = p[:3]
    P3 = p1*p2*p3
    P2 = _exactly_two_hits_prob(p1,p2,p3)
    m3 = float(payouts_flex["3"]["perfect"])
    return m3*P3 + 1.0*P2

def ev_standard_multiple_k(p: List[float], payouts_std: Dict[str,Any]) -> float:
    """k-leg standard: only all-correct pays."""
    k = len(p)
    key = str(k)
    mult = float(payouts_std.get(key, 0.0))
    if mult <= 0.0:  # fallback to 3 if unknown
        if "3" in payouts_std and k >= 3:
            k = 3; mult = float(payouts_std["3"])
        else:
            return 0.0
    return mult * _prod(p[:k])

def _threshold(cfg: Dict[str,Any], fmt: str) -> float:
    G = cfg["FILTERS"]["GLOBAL"]
    return float(G["min_p_final_flex"]) if fmt.upper().startswith("FLEX") else float(G["min_p_final_std"])

def promo_haircut_fill(enriched: pd.DataFrame, cfg: Dict[str,Any], fmt: str = "FLEX3") -> Tuple[pd.DataFrame, Dict[str,Any]]:
    """
    If promo is active and we don't have enough passing legs for the target format,
    relax the p_final threshold by a small margin to fill exactly as many legs as needed.
    Only accept if card-level ROI after promo >= min_roi_after_haircut.

    Assumptions:
    - We target 3 legs (FLEX3 or STD3). For >3 legs we do NOT relax (safety).
    - We choose the top missing leg(s) from a near-threshold band.
    """
    promo = (cfg or {}).get("PROMO", {}) or {}
    diag = {"applied": False, "format": fmt}
    if not promo.get("active"):
        diag["reason"] = "promo_inactive"
        return enriched, diag

    min_legs = int(promo.get("min_legs", 3))
    if min_legs != 3:
        diag["reason"] = "only_3_leg_supported_for_haircut"
        return enriched, diag

    # Thresholds and margins
    thr = _threshold(cfg, fmt)
    hc  = (promo.get("HAIRCUT", {}) or {})
    margin_p = float(hc.get("margin_p_final_flex" if fmt.upper().startswith("FLEX") else "margin_p_final_std", 0.01))
    max_relaxed = int(hc.get("max_props_relaxed", 2))
    min_roi_after = float(hc.get("min_roi_after_haircut", 0.01))

    # Pools
    base = enriched[ enriched["p_final"] >= thr ].copy()
    need = max(0, min_legs - len(base))
    if need <= 0:
        diag["reason"] = "enough_legs_already"
        return enriched, diag

    # near-threshold candidates within band [thr - margin_p, thr)
    near = enriched[(enriched["p_final"] >= (thr - margin_p)) & (enriched["p_final"] < thr)].copy()
    if near.empty:
        diag["reason"] = "no_near_threshold_candidates"
        return enriched, diag

    # Try top "need" among top-N near candidates
    near = near.sort_values("p_final", ascending=False).head(max_relaxed)
    add = near.head(need)
    if len(add) < need:
        diag["reason"] = "insufficient_candidates_in_margin"
        return enriched, diag

    # Evaluate EV/ROI with promo-adjusted payouts on the best 3 from (base+add)
    eff = effective_payouts(cfg)
    p_top3 = pd.concat([base, add]).sort_values("p_final", ascending=False).head(3)["p_final"].tolist()
    if len(p_top3) < 3:
        diag["reason"] = "still_short_after_fill"
        return enriched, diag

    if fmt.upper().startswith("FLEX"):
        ev = ev_flex_multiple_3(p_top3, eff["FLEX"])
    else:
        ev = ev_standard_multiple_k(p_top3, eff["STANDARD"])
    roi = ev - 1.0
    if roi < min_roi_after:
        diag["reason"] = f"roi_after_haircut_below_floor({roi:.3f}<{min_roi_after:.3f})"
        return enriched, diag

    # Accept: append the added legs (dedupe on player+market+team)
    out = pd.concat([enriched, add]).drop_duplicates(subset=["player","market","team"], keep="first")
    diag.update({"applied": True, "added": int(len(add)), "thr": thr, "margin_p": margin_p, "roi_after": round(roi,4)})
    return out, diag
