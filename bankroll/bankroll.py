"""Conservative bankroll allocation: 20% daily budget, 80/20 split."""
from typing import List
from champions.models import Lineup, Pick
from champions.payouts import calculate_lineup_metrics

def allocate_stakes(lineups: List[Lineup], config: dict) -> List[Lineup]:
    BR = config["BANKROLL"]["BASE"]
    daily_budget = BR * config["RISK"]["DAILY_BUDGET_FRACTION"]
    top_share = config["RISK"]["TOP_PLAY_SHARE"]
    parlay_share = config["RISK"]["PARLAY_PLAY_SHARE"]
    min_stake = config["RISK"]["MIN_STAKE"]

    # Filter: exclude any B-tier lineups entirely
    valid = [l for l in lineups if l.tier in ("S","A")]

    # Best 2-leg (Tier S preferred)
    two_candidates = [l for l in valid if l.num_legs == 2 and l.tier == "S"]
    if not two_candidates:
        two_candidates = [l for l in valid if l.num_legs == 2]
    best_two = max(two_candidates, key=lambda l: (l.expected_value, l.expected_win_prob), default=None)

    # Best 4–6-leg (S/A) as lotto
    parlay_candidates = [l for l in valid if 4 <= l.num_legs <= 6]
    best_parlay = max(parlay_candidates, key=lambda l: (l.expected_value, l.expected_win_prob), default=None)

    out = []
    if best_two:
        best_two.stake = max(min_stake, daily_budget * top_share)
        best_two.category = "STANDARD"
        out.append(best_two)

    if best_parlay:
        # Decide FLEX vs STANDARD by EV using payout tables
        std_table = config["CHAMPIONS"]["PAYOUT_TABLE_STANDARD"]
        flex_table = config["CHAMPIONS"]["PAYOUT_TABLE_FLEX"]
        win_probs = [p.win_prob for p in best_parlay.picks]
        std_wp, std_mult, std_ev = calculate_lineup_metrics(win_probs, std_table)
        flex_wp, flex_mult, flex_ev = calculate_lineup_metrics(win_probs, flex_table)
        if flex_ev > std_ev:
            best_parlay.expected_win_prob = flex_wp
            best_parlay.expected_base_multiplier = flex_mult
            best_parlay.expected_value = flex_ev
            best_parlay.category = "FLEX"
        else:
            best_parlay.expected_win_prob = std_wp
            best_parlay.expected_base_multiplier = std_mult
            best_parlay.expected_value = std_ev
            best_parlay.category = "STANDARD"
        best_parlay.stake = max(min_stake, daily_budget * parlay_share)
        out.append(best_parlay)
    return out
