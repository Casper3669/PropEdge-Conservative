from pydantic import BaseModel
from typing import List, Optional
class PropRow(BaseModel):
    source: str
    platform: str = "underdog"
    sport: str
    game_datetime_utc: str
    player: str
    team: Optional[str] = None
    opponent: Optional[str] = None
    market: str
    line: float
    side: str
    proj_mean: Optional[float] = None
    proj_dist: Optional[str] = None
    prob_over: Optional[float] = None
    prob_under: Optional[float] = None
    odds_american: Optional[float] = None
    confidence_tag: Optional[str] = None
    meta: Optional[str] = None
    event_id: Optional[str] = None
    player_id: Optional[str] = None
    source_id: Optional[str] = None
class OptimizeRequest(BaseModel):
    bankroll: float
    props: List[PropRow]
    team_trends_csv_path: Optional[str] = None
    promos_csv_path: Optional[str] = None
class OptimizeResponse(BaseModel):
    entries: list
    totals: dict
