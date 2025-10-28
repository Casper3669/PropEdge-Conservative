# PropEdge (Conservative v3)

**What’s inside**
- Ingestion for PlayerProps.ai exports (CSV/XLSX)
- Scoring & tiering (S/A only downstream)
- Champions lineup builder (2–6 legs)
- Bankroll allocator: fixed 20% daily budget, 80% to best 2-leg, 20% to one 4–6 leg lotto
- Automatic EV-based decision for FLEX vs STANDARD on the lotto
- `config.yaml` with stricter tier thresholds and payout tables (STANDARD & FLEX)

**Daily use**
1. Export your props from PlayerProps.ai (CSV/XLSX).
2. Run:
   ```bash
   python main.py --playerprops path/to/export.xlsx --output plan.json
   ```
3. Read `plan.json` for the two recommended lineups with stake, EV, and win probability.
4. After games, log outcomes using `results_log_template.csv` columns.

**Notes**
- Only Tier S/A props are used to build entries.
- Correlation haircut & EV floors are applied per leg size.
- FLEX vs STANDARD is chosen by expected value for the lotto entry.
