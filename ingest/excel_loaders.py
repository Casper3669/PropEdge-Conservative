"""Excel loader for PlayerProps.ai .xlsx exports."""
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import pandas as pd
from .schema import CanonicalProp, normalize_stat_name

def load_playerprops_excel(path: str | Path, sport_hint: Optional[str] = None) -> List[CanonicalProp]:
    path = Path(path)
    if not sport_hint:
        filename = path.stem.upper()
        if 'NFL' in filename:
            sport_hint = 'NFL'
        elif 'NCAA' in filename or 'NCAAF' in filename or 'COLLEGE' in filename:
            sport_hint = 'NCAAF'
        elif 'NBA' in filename:
            sport_hint = 'NBA'
        elif 'NCAAB' in filename:
            sport_hint = 'NCAAB'
        else:
            sport_hint = 'NFL'
    df = pd.read_excel(path)
    ingested_at = datetime.now()
    props = []
    if len(df.columns) == 1:
        for idx, row in df.iterrows():
            text = str(row.iloc[0])
            prop = _parse_raw_text(text, sport_hint, ingested_at)
            if prop:
                props.append(prop)
    else:
        for idx, row in df.iterrows():
            prop = _parse_structured_row(row, sport_hint, ingested_at)
            if prop:
                props.append(prop)
    return props

def _parse_raw_text(text: str, sport: str, ingested_at: datetime) -> Optional[CanonicalProp]:
    import re
    pattern = r'(\w+(?:\s+\w+)?)\s+(\w+)\s+.*?\(\s*\w+\s*\).*?(\w+)\s+@\s+(\w+).*?(Receiving Yards|Rushing Yards|Passing Yards|Receptions|Passing TDs|Rushing TDs|Receiving TDs)\s+([\d.]+)\s+(Over|Under).*?(-?\d+).*?Implied.*?([\d.]+)%.*?Projection\s+([\d.]+).*?L5\s*:\s*([\d.]+|N/A)%.*?L10\s*:\s*([\d.]+|N/A)%.*?SZN\s*:\s*([\d.]+|N/A)%'
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    player = match.group(1).strip()
    team = match.group(2).strip()
    opp = match.group(4).strip()
    stat_raw = match.group(5).strip()
    line = float(match.group(6))
    direction = match.group(7).strip()
    odds = int(match.group(8))
    implied = float(match.group(9))
    projection = float(match.group(10))
    l5_str = match.group(11).strip()
    l10_str = match.group(12).strip()
    szn_str = match.group(13).strip()
    l5 = float(l5_str) / 100 if l5_str != 'N/A' else None
    l10 = float(l10_str) / 100 if l10_str != 'N/A' else None
    szn = float(szn_str) / 100 if szn_str != 'N/A' else None
    implied_prob = implied / 100
    edge = (projection - line) / line if direction == "Over" else (line - projection) / line
    p_model = min(0.95, implied_prob + (edge * 0.3))
    stat = normalize_stat_name(stat_raw)
    market_prob = _american_to_probability(odds)
    diff_pct = min(1.0, abs((projection - line) / line)) if line > 0 else 0.0
    return CanonicalProp(
        source="PlayerPropsAI",
        sport=sport,
        player=player,
        team=team,
        opponent=opp,
        stat=stat,
        line=line,
        direction=direction,
        p_model=p_model,
        implied_prob=implied_prob,
        market_prob=market_prob,
        projection=projection,
        diff_pct=diff_pct,
        l5=l5,
        l10=l10,
        szn=szn,
        h2h=None,
        odds_american=odds,
        accuracy_sample=50,
        ingested_at=ingested_at,
        game_time_cdt=None,
        raw_text=text
    )

def _parse_structured_row(row: "pd.Series", sport: str, ingested_at: datetime) -> Optional[CanonicalProp]:
    import pandas as pd
    try:
        player = str(row.get('Player', '')).strip()
        stat_raw = str(row.get('Stat', '')).strip()
        line = float(row.get('Line', 0))
        if not player or not stat_raw or not line:
            return None
        stat = normalize_stat_name(stat_raw)
        direction = str(row.get('Direction', 'Over')).strip()
        implied = float(row.get('Implied', 0))
        implied_prob = implied if implied <= 1 else implied / 100
        l5 = float(row.get('L5', 0)) if pd.notna(row.get('L5')) else None
        l10 = float(row.get('L10', 0)) if pd.notna(row.get('L10')) else None
        szn = float(row.get('SZN', 0)) if pd.notna(row.get('SZN')) else None
        h2h = float(row.get('H2H', 0)) if pd.notna(row.get('H2H')) else None
        projection = float(row.get('Projection', 0)) if pd.notna(row.get('Projection')) else None
        odds = int(row.get('Odds', -110))
        game_time_cdt = None
        if 'GameTimeCDT' in row.index and pd.notna(row.get('GameTimeCDT')):
            time_str = str(row.get('GameTimeCDT')).replace(' CDT', '').replace(' EST', '').replace(' PST', '').replace(' MST', '')
            try:
                game_time_cdt = pd.to_datetime(time_str, errors='coerce')
            except Exception:
                game_time_cdt = None
        if projection and line:
            if direction == "Over":
                edge = (projection - line) / line
            else:
                edge = (line - projection) / line
            p_model = min(0.95, max(0.05, implied_prob + (edge * 0.3)))
        else:
            p_model = implied_prob
        market_prob = _american_to_probability(odds)
        diff_pct = min(1.0, abs((projection - line) / line)) if projection and line > 0 else 0.0
        return CanonicalProp(
            source="PlayerPropsAI",
            sport=sport,
            player=player,
            team=str(row.get('Team', '')).strip() or None,
            opponent=str(row.get('Opp', '')).strip() or None,
            stat=stat,
            line=line,
            direction=direction,
            p_model=p_model,
            implied_prob=implied_prob,
            market_prob=market_prob,
            projection=projection,
            diff_pct=diff_pct,
            l5=l5,
            l10=l10,
            szn=szn,
            h2h=h2h,
            odds_american=odds,
            accuracy_sample=50,
            ingested_at=ingested_at,
            game_time_cdt=game_time_cdt,
            raw_text=str(row.to_dict())
        )
    except Exception:
        return None

def _american_to_probability(odds: int) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)
