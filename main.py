"""CLI for PropEdge Champions pipeline (conservative strategy)."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime
import yaml

from ingest.ingest_any import ingest_playerprops
from unify.unify import merge_sources
from scoring.scoring import score_all_props
from champions.builder import build_lineups
from bankroll.bankroll import allocate_stakes

def load_config(config_path: str = "config.yaml") -> dict:
    cfg = Path(config_path)
    if not cfg.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return yaml.safe_load(cfg.read_text())

def run_pipeline(playerprops_file: str, bankroll: float | None = None, config_path: str = "config.yaml") -> dict:
    config = load_config(config_path)
    if bankroll:
        config.setdefault("BANKROLL", {})["BASE"] = bankroll

    # 1) Ingest
    pp_props = ingest_playerprops(playerprops_file)
    if not pp_props:
        return {"error": "no props loaded"}

    # 2) Unify
    unified = merge_sources(pp_props)

    # 3) Score (S/A only downstream)
    scored = score_all_props(
        unified,
        weights={
            "EDGE_WEIGHT": config["SCORING"]["EDGE_WEIGHT"],
            "ACCURACY_WEIGHT": config["SCORING"]["ACCURACY_WEIGHT"],
            "RECENT_WEIGHT": config["SCORING"]["RECENT_WEIGHT"],
            "DTM_WEIGHT": config["SCORING"]["DTM_WEIGHT"],
        },
        tier_thresholds=config["SCORING"]["TIER_THRESHOLDS"],
        min_accuracy_sample=config["SCORING"]["MIN_ACCURACY_SAMPLE"]
    )
    scored = [s for s in scored if s.tier in ("S","A")]

    # 4) Build lineups using STANDARD payouts for candidate generation
    lineups = build_lineups(
        scored,
        payout_table=config["CHAMPIONS"]["PAYOUT_TABLE_STANDARD"],
        correlation_penalties=config["CORRELATION"],
        min_ev_by_leg=config["RISK"]["MIN_EV_BY_LEG"],
        max_prop_appearances=config["RISK"]["MAX_PROP_APPEARANCES"]
    )

    # 5) Allocate bankroll and decide FLEX vs STANDARD for lotto
    allocated = allocate_stakes(lineups, config)

    result = {
        "timestamp": datetime.now().isoformat(),
        "bankroll": config["BANKROLL"]["BASE"],
        "daily_budget_fraction": config["RISK"]["DAILY_BUDGET_FRACTION"],
        "num_allocated": len(allocated),
        "lineups": [
            {
                "mode": L.category,
                "tier": L.tier,
                "num_legs": L.num_legs,
                "stake": round(L.stake, 2),
                "win_prob": round(L.expected_win_prob, 4),
                "ev": round(L.expected_value, 4),
                "picks": [{"player": p.player_name, "stat": p.stat_type, "line": p.line, "dir": p.direction} for p in L.picks],
            }
            for L in allocated
        ],
    }
    return result

def main():
    ap = argparse.ArgumentParser(description="PropEdge v3 (conservative two-play strategy)")
    ap.add_argument("--playerprops", required=True, help="Path to PlayerProps.ai CSV/XLSX")
    ap.add_argument("--bankroll", type=float, default=None, help="Override bankroll base")
    ap.add_argument("--config", default="config.yaml", help="Config path")
    ap.add_argument("--output", default=None, help="Optional JSON output path")
    args = ap.parse_args()

    plan = run_pipeline(args.playerprops, bankroll=args.bankroll, config_path=args.config)
    if args.output:
        out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, indent=2))
        print(f"Saved plan to {out}")
    else:
        print(json.dumps(plan, indent=2))

if __name__ == "__main__":
    main()
