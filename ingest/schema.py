"""
Canonical schema for PropEdge ingestion.
All data sources (PlayerProps.ai) normalize to this structure.
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Type aliases
Probability = float  # 0.0 to 1.0
Direction = Literal["Over", "Under"]
Source = Literal["PlayerPropsAI"]


class CanonicalProp(BaseModel):
    """Unified prop bet representation across all data sources."""
    # ===== Source Identification =====
    source: Source
    sport: str  # "NFL", "NBA", "NCAAB", "NCAAF", etc.
    league: Optional[str] = None  # For future expansion

    # ===== Game Context =====
    game: Optional[str] = None  # e.g., "DET @ KC"
    game_time_cdt: Optional[datetime] = None

    # ===== Player Identification =====
    player: str = Field(..., min_length=1, description="Player name")
    team: Optional[str] = None
    opponent: Optional[str] = None
    position: Optional[str] = None

    # ===== Prop Details =====
    stat: str = Field(..., min_length=1, description="Normalized stat name")
    line: float = Field(..., gt=0, description="Prop line value")
    direction: Optional[Direction] = None

    # ===== Probability Metrics (all 0-1 floats) =====
    implied_prob: Optional[Probability] = Field(None, ge=0, le=1, description="From odds (no-vig if available)")
    p_model: Optional[Probability] = Field(None, ge=0, le=1, description="Model's probability estimate")
    market_prob: Optional[Probability] = Field(None, ge=0, le=1, description="Market consensus probability")
    p_blend: Optional[Probability] = Field(None, ge=0, le=1, description="Blended probability")

    # ===== Model Metadata =====
    accuracy_sample: Optional[int] = Field(None, ge=0, description="Sample size for accuracy metrics")
    projection: Optional[float] = Field(None, gt=0, description="Model projection for stat value")
    dtm_pct: Optional[Probability] = Field(None, ge=0, le=1, description="Distance to market")
    diff_pct: Optional[Probability] = Field(None, ge=0, le=1, description="Difference percentage")

    # ===== Historical Performance (0-1 floats) =====
    l5: Optional[Probability] = Field(None, ge=0, le=1, description="Last 5 games hit rate")
    l10: Optional[Probability] = Field(None, ge=0, le=1, description="Last 10 games hit rate")
    szn: Optional[Probability] = Field(None, ge=0, le=1, description="Season hit rate")
    h2h: Optional[Probability] = Field(None, ge=0, le=1, description="Head-to-head hit rate")

    # ===== Odds and Signals =====
    odds_american: Optional[int] = Field(None, description="American odds (e.g., -110, +150)")
    smart_signal: Optional[bool] = Field(None, description="Flags from source if any")
    recommended: Optional[bool] = Field(None, description="Flags from source if any")

    # ===== Audit Trail =====
    raw_text: Optional[str] = Field(None, description="Original text for traceability")
    ingested_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of ingestion")
    
    @field_validator('projection', mode='before')
    @classmethod
    def validate_projection(cls, v):
        if v is not None:
            v_float = float(v) if not isinstance(v, float) else v
            if v_float < 0 or v_float > 10000:
                raise ValueError(f"Projection value seems invalid: {v_float}")
            return v_float
        return v
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        validate_assignment=True,
        str_strip_whitespace=True
    )


# ===== Canonical Stat Name Mappings =====
CANONICAL_STATS: dict[str, str] = {
    # Football - Passing
    "passing yards": "Passing Yards",
    "pass yds": "Passing Yards",
    "pass yards": "Passing Yards",
    "passing_yards": "Passing Yards",
    "passing tds": "Pass TDs",
    "pass tds": "Pass TDs",
    "completions": "Completions",
    "pass attempts": "Pass Attempts",
    "interceptions": "Interceptions",

    # Football - Rushing
    "rushing yards": "Rushing Yards",
    "rush yds": "Rushing Yards",
    "rushing tds": "Rush TDs",
    "rush attempts": "Rush Attempts",

    # Football - Receiving
    "receiving yards": "Receiving Yards",
    "receptions": "Receptions",
    "receiving tds": "Receiving TDs",
    "targets": "Targets",

    # Basketball
    "points": "Points",
    "assists": "Assists",
    "rebounds": "Rebounds",
    "steals": "Steals",
    "blocks": "Blocks",
    "turnovers": "Turnovers",
    "3-pointers": "3-Pointers",

    # Basketball - combos
    "pra": "PRA",
    "points + assists": "Points + Assists",
    "points + rebounds": "Points + Rebounds",
    "rebounds + assists": "Rebounds + Assists",
}


def normalize_stat_name(stat: str) -> str:
    if not stat:
        return ""
    normalized = stat.strip().lower()
    return CANONICAL_STATS.get(normalized, stat.strip().title())
