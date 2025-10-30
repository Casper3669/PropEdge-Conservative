from fastapi import FastAPI
import pandas as pd
from datetime import datetime
from .schemas import OptimizeRequest, OptimizeResponse
from .optimizer import build_entries
from .decision_tree import decide_format, ev_multiple_flex3, ev_multiple_standard3
from .fetch_nba_slate import get_games_by_date_local
from .config import DEFAULT_BANKROLL
import pytz
app = FastAPI(title="PropEdge Lineup API")
@app.get("/healthz")
def health(): return {"ok": True}
@app.get("/nba/slate")
def slate():
    now_local = datetime.now(pytz.timezone("America/Chicago"))
    df = get_games_by_date_local(now_local)
    return {"count": len(df), "games": df.to_dict(orient="records")}
@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest):
    props_df = pd.DataFrame([p.dict() for p in req.props])
    bankroll = req.bankroll or DEFAULT_BANKROLL
    result = build_entries(props_df, bankroll)
    
    
    # Attach promo diagnostics if any
    try:
        if isinstance(result, dict):
            result.setdefault('meta', {})['promo_haircut'] = _PROMO_DIAG
    except Exception: pass
## BEGIN FORMAT DECISION POST
    try:
        # Load CFG for payouts/thresholds
        import os, yaml
        with open(os.path.join(os.path.dirname(__file__),'..','config.yaml'),'r',encoding='utf-8') as _f:
            _CFG = yaml.safe_load(_f)

        # If the optimizer returned entries, annotate each with chosen format
        if isinstance(result, dict) and 'entries' in result and isinstance(result['entries'], list):
            for _e in result['entries']:
                # Try to recover per-leg probabilities
                p_list = []
                legs = _e.get('legs') or _e.get('props') or []
                for _leg in legs:
                    p = (_leg.get('p_final') or _leg.get('prob') or _leg.get('p') or
                         (_leg.get('meta',{}) or {}).get('p_final'))
                    if p is not None:
                        try: p_list.append(float(p))
                        except: pass
                # If not 3 probs found, do a best-effort join from props_df by (player, market)
                if len(p_list) < 3:
                    try:
                        for _leg in legs:
                            _pl = str(_leg.get('player','')).strip().lower()
                            _mk = str(_leg.get('market','')).strip().lower()
                            _cand = props_df.loc[(props_df['player'].str.lower()==_pl) &
                                                 (props_df['market'].str.lower()==_mk)]
                            if not _cand.empty:
                                p_list.append(float(_cand.iloc[0]['p_final']))
                    except Exception:
                        pass

                if len(p_list) == 3:
                    _pick = decide_format(p_list, _CFG, delta=0.02)
                    # Harmonize naming for clients
                    chosen = _pick['format']
                    if chosen == 'STD3':
                        _e['format'] = 'standard'
                    elif chosen == 'FLEX3':
                        _e['format'] = 'flex'
                    else:
                        _e['format'] = _e.get('format','unknown')  # leave as-is if reject

                    # add diagnostics
                    _meta = _e.get('meta',{})
                    _meta['format_decision'] = _pick
                    _meta['p_list'] = p_list
                    _e['meta'] = _meta
    except Exception as _err:
        # Non-fatal: keep original result if annotate failed
        if isinstance(result, dict):
            result.setdefault('meta',{})['format_decision_error'] = str(_err)
    ## END FORMAT DECISION POSTreturn OptimizeResponse(**result)


