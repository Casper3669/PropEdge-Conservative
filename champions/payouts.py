"""Champions payout calculations."""
from __future__ import annotations
from typing import Optional, Dict

def get_payout_multiplier(num_legs: int, wins: int, payout_table: Dict[int, Dict[int, float]]) -> float:
    if num_legs not in payout_table:
        return 0.0
    return payout_table[num_legs].get(wins, 0.0)

def _calculate_outcome_probs(win_probs: list[float]) -> list[float]:
    n = len(win_probs)
    dp = [[0.0 for _ in range(n + 1)] for _ in range(n + 1)]
    dp[0][0] = 1.0
    for i in range(1, n + 1):
        p_win = win_probs[i - 1]; p_lose = 1 - p_win
        for k in range(i + 1):
            if k > 0:
                dp[i][k] += dp[i - 1][k - 1] * p_win
            if k < i:
                dp[i][k] += dp[i - 1][k] * p_lose
    return dp[n]

def calculate_expected_value(win_probs: list[float], payout_table: Dict[int, Dict[int, float]], stake: float = 1.0) -> tuple[float, float]:
    num_legs = len(win_probs)
    if num_legs < 2 or num_legs > 6:
        return 0.0, 0.0
    outcomes = _calculate_outcome_probs(win_probs)
    expected_payout = 0.0
    for wins, prob in enumerate(outcomes):
        mult = get_payout_multiplier(num_legs, wins, payout_table)
        expected_payout += prob * mult * stake
    ev = expected_payout - stake
    base_mult = expected_payout / stake if stake > 0 else 0.0
    return ev, base_mult

def calculate_lineup_metrics(win_probs: list[float], payout_table: Dict[int, Dict[int, float]]) -> tuple[float, float, float]:
    outcomes = _calculate_outcome_probs(win_probs)
    num_legs = len(win_probs)
    # Probability of any positive return based on payout table
    positive_outcomes = [wins for wins, mult in payout_table.get(num_legs, {}).items() if mult > 0]
    win_prob = sum(outcomes[w] for w in positive_outcomes) if positive_outcomes else 0.0
    ev, base_mult = calculate_expected_value(win_probs, payout_table, stake=1.0)
    return win_prob, base_mult, ev
