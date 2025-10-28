"""CSV loaders for PlayerProps.ai raw text format."""
from pathlib import Path
from typing import Optional, List
import re
from .schema import CanonicalProp, normalize_stat_name

def load_playerprops_csv(path: str | Path, sport_hint: Optional[str] = None) -> List[CanonicalProp]:
    """Load PlayerProps.ai raw text export."""
    path = Path(path)
    props = []
    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.lower().startswith('player'):
                continue
            prop = _parse_raw_line(line, sport_hint)
            if prop:
                props.append(prop)
    return props

def _parse_raw_line(text: str, sport_hint: Optional[str]) -> Optional[CanonicalProp]:
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
    if direction == "Over":
        edge = (projection - line) / line
        p_model = min(0.95, implied_prob + (edge * 0.3))
    else:
        edge = (line - projection) / line
        p_model = min(0.95, implied_prob + (edge * 0.3))
    stat = normalize_stat_name(stat_raw)
    sport = sport_hint or ('NFL')
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
        raw_text=text
    )

def _american_to_probability(odds: int) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)
