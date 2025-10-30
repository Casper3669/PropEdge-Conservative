"""
Decision tree for choosing 3-Standard vs 3-Flex per lineup.

Logic (payouts from config.yaml):
- 3-Standard EV multiple:   EV_std  = 6 * (p1*p2*p3)
- 3-Flex EV multiple:       EV_flex = 3*P3 + 1*P2
  where P3 = p1*p2*p3 and P2 = sum of exactly-two-hits.
- ROI = EV - 1

Decision rule:
1) If both ROIs < 0, reject.
2) If ROI_std >= min_roi_std AND (EV_std >= EV_flex + delta), choose STANDARD.
3) Else if ROI_flex >= min_roi_flex, choose FLEX.
4) Else if any ROI > 0, choose the higher-ROI format.
5) Else reject.

Default delta = 0.02 (2% EV margin required for STANDARD).
"""

from __future__ import annotations
from typing import Dict, List, Any, Tuple
import math, os, yaml

def _exactly_two_hits_prob(p1: float, p2: float, p3: float) -> float:
    return (p1*p2*(1-p3) + p1*p3*(1-p2) + p2*p3*(1-p1))

def ev_multiple_flex3(p: List[float], payouts_flex: Dict[str, Any]) -> float:
    p1,p2,p3 = p
    P3 = p1*p2*p3
    P2 = _exactly_two_hits_prob(p1,p2,p3)
    m3 = float(payouts_flex["3"]["perfect"])
    return m3*P3 + 1.0*P2

def ev_multiple_standard3(p: List[float], payouts_std: Dict[str, Any]) -> float:
    p1,p2,p3 = p
    m3 = float(payouts_std["3"])
    return m3*(p1*p2*p3)

def _roi(ev_mult: float) -> float:
    return ev_mult - 1.0

def decide_format(p: List[float], cfg: Dict[str,Any], delta: float = 0.02) -> Dict[str,Any]:
    """Return dict: {format, ev_std, ev_flex, roi_std, roi_flex, reason} or {format: 'REJECT', ...}"""
    payouts = cfg["PAYOUTS"]["UNDERDOG"]
    ev_std  = ev_multiple_standard3(p, payouts["STANDARD"])
    ev_flex = ev_multiple_flex3(p, payouts["FLEX"])
    roi_std, roi_flex = _roi(ev_std), _roi(ev_flex)

    min_roi_std  = float(cfg["FILTERS"]["GLOBAL"]["min_roi_std"])
    min_roi_flex = float(cfg["FILTERS"]["GLOBAL"]["min_roi_flex"])

    # 1) both negative → reject
    if roi_std < 0 and roi_flex < 0:
        return {"format":"REJECT","ev_std":ev_std,"ev_flex":ev_flex,"roi_std":roi_std,"roi_flex":roi_flex,
                "reason":"both ROI < 0"}

    # 2) prefer STANDARD only if it clears its ROI floor and beats FLEX by margin delta
    if roi_std >= min_roi_std and (ev_std >= ev_flex + delta):
        return {"format":"STD3","ev_std":ev_std,"ev_flex":ev_flex,"roi_std":roi_std,"roi_flex":roi_flex,
                "reason":f"std_ev >= flex_ev + {delta:.2f} and ROI_std >= {min_roi_std:.2f}"}

    # 3) else FLEX if it clears its ROI floor
    if roi_flex >= min_roi_flex:
        return {"format":"FLEX3","ev_std":ev_std,"ev_flex":ev_flex,"roi_std":roi_std,"roi_flex":roi_flex,
                "reason":f"roi_flex >= {min_roi_flex:.2f}"}

    # 4) fallback: whichever has positive ROI & is higher
    if roi_std > 0 or roi_flex > 0:
        fmt = "STD3" if roi_std >= roi_flex else "FLEX3"
        return {"format":fmt,"ev_std":ev_std,"ev_flex":ev_flex,"roi_std":roi_std,"roi_flex":roi_flex,
                "reason":"fallback to higher positive ROI"}

    # 5) negative fallback
    return {"format":"REJECT","ev_std":ev_std,"ev_flex":ev_flex,"roi_std":roi_std,"roi_flex":roi_flex,
            "reason":"no format meets ROI floors or positive ROI"}
