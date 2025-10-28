"""Build and optimize Champions lineups."""
from itertools import combinations
from scoring.models import ScoredProp
from .models import Lineup, Pick
from .payouts import calculate_lineup_metrics
from .correlation import calculate_correlation_index
from .validate import validate_lineup

def rank_key(lineup):
    return (lineup.expected_value, lineup.expected_win_prob, -lineup.correlation_index)

def build_lineups(
    scored_props: list[ScoredProp],
    payout_table: dict,
    correlation_penalties: dict,
    min_ev_by_leg: dict,
    max_prop_appearances: int = 3,
    max_lineups: int = 1000,
    timeout_seconds: int = 60
) -> list[Lineup]:
    import time
    start_time = time.time()

    # Filter to S and A tier only (drop B by design)
    s_tier = sorted([p for p in scored_props if p.tier == "S"], key=lambda x: x.total_score, reverse=True)
    a_tier = sorted([p for p in scored_props if p.tier == "A"], key=lambda x: x.total_score, reverse=True)
    candidates = s_tier + a_tier

    lineups = []
    prop_usage = {}

    for num_legs in [2, 3, 4, 5, 6]:
        if len(candidates) < num_legs:
            continue
        pool = candidates[:80] if num_legs <= 2 else candidates[:60] if num_legs in [3,4] else candidates
        for i, combo in enumerate(combinations(pool, num_legs)):
            if i >= max_lineups or time.time() - start_time > timeout_seconds:
                break
            # prop usage limit
            skip = False
            for p in combo:
                key = (p.player_name, p.stat_type, p.direction)
                if prop_usage.get(key, 0) >= max_prop_appearances:
                    skip = True; break
            if skip:
                continue
            picks = [Pick(
                player_name=p.player_name,
                stat_type=p.stat_type,
                line=p.line,
                direction=p.direction,
                sport=p.sport,
                team=getattr(p, 'team', None),
                win_prob=p.model_prob,
                score=p.total_score,
                tier=p.tier,
                game_date=p.game_date
            ) for p in combo]

            ok, _ = validate_lineup(picks)
            if not ok:
                continue

            # simple correlation haircut
            win_probs = [p.model_prob for p in combo]
            corr_idx = calculate_correlation_index(combo, correlation_penalties)
            haircut = min(0.30, corr_idx)  # cap
            win_probs = [max(0.01, min(0.99, wp * (1 - haircut))) for wp in win_probs]

            expected_win_prob, base_mult, ev = calculate_lineup_metrics(win_probs, payout_table)
            if ev < min_ev_by_leg.get(num_legs, 0.0):
                continue

            # Determine lineup tier
            counts = {"S":0, "A":0, "B":0}
            for p in combo:
                counts[p.tier] += 1
            if counts["S"] >= num_legs:
                tier = "S"
            elif counts["S"] + counts["A"] >= num_legs:
                tier = "A"
            else:
                tier = "B"

            lineup = Lineup(
                picks=picks,
                num_legs=num_legs,
                expected_win_prob=expected_win_prob,
                expected_base_multiplier=base_mult,
                expected_value=ev,
                tier=tier,
                correlation_index=corr_idx,
                avg_score=sum(p.total_score for p in combo)/len(combo),
                min_score=min(p.total_score for p in combo),
                stake=0.0,
                category="STANDARD"
            )
            lineups.append(lineup)

            for p in combo:
                key = (p.player_name, p.stat_type, p.direction)
                prop_usage[key] = prop_usage.get(key, 0) + 1

    # Sort by EV/Win prob/Low corr
    lineups.sort(key=rank_key, reverse=True)
    # De-duplicate similar lineups (basic overlap filter)
    diversified = []
    for L in lineups:
        picks_set = {(p.player_name, p.stat_type, p.direction) for p in L.picks}
        if any(len(picks_set & {(q.player_name, q.stat_type, q.direction) for q in E.picks}) > 3 for E in diversified):
            continue
        diversified.append(L)
    return diversified
