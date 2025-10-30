from fastapi import FastAPI
import pandas as pd
from datetime import datetime
from .schemas import OptimizeRequest, OptimizeResponse
from .optimizer import build_entries
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
    return OptimizeResponse(**result)
