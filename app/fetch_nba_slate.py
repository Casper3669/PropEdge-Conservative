import pandas as pd, pytz, requests
from datetime import datetime
from .config import BALLDONTLIE_API_KEY, TZ_LOCAL
API = "https://api.balldontlie.io/v1"
HDRS = {"Authorization": f"Bearer {BALLDONTLIE_API_KEY}"} if BALLDONTLIE_API_KEY else {}
def get_games_by_date_local(d_local: datetime) -> pd.DataFrame:
    params = {"dates[]": d_local.date().isoformat(), "per_page": 100}
    r = requests.get(f"{API}/games", params=params, headers=HDRS, timeout=30)
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        return pd.DataFrame()
    df = pd.json_normalize(data)
    df["game_time_utc"] = pd.to_datetime(df["date"], utc=True)
    local_tz = pytz.timezone(TZ_LOCAL)
    df["game_time_local"] = df["game_time_utc"].dt.tz_convert(local_tz)
    def abbr(row, keys):
        for k in keys:
            if k in row and pd.notnull(row[k]): return row[k]
        return "UNK"
    df["away"] = df.apply(lambda r: abbr(r, ["visitor_team.abbreviation","visitor_team.abbr"]), axis=1)
    df["home"] = df.apply(lambda r: abbr(r, ["home_team.abbreviation","home_team.abbr"]), axis=1)
    df["event_id"] = df["game_time_utc"].dt.strftime("NBA%Y%m%d-") + df["away"] + "@" + df["home"]
    return df[["event_id","game_time_local","game_time_utc","away","home"]]
