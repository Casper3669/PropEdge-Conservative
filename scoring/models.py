"""Scoring models for PropEdge."""
from __future__ import annotations
from typing import Literal, Optional, List
from pydantic import BaseModel, Field

class ScoredProp(BaseModel):
    """Scored prop with edge calculations and tier assignment."""
    player_name: str
    stat_type: str
    line: float
    sport: str
    league: Optional[str] = None
    game_date: Optional[str] = None

    # Direction and probabilities
    direction: Literal["OVER", "UNDER"]
    model_prob: float  # Combined probability from sources
    implied_prob: float  # From odds

    # Edge metrics
    edge: float  # model_prob - implied_prob
    edge_percent: float  # edge / implied_prob

    # Component scores (0-10 each)
    edge_score: float
    accuracy_score: float
    recent_score: float
    dtm_score: float

    # Final metrics
    total_score: float = Field(ge=0, le=100)
    tier: Literal["S", "A", "B"]

    # Metadata
    sources: List[str]
    single_source: bool
    confidence_adjusted: bool = False

    # Raw data preserved
    over_prob: float
    under_prob: float
    odds: int
    l5_rate: Optional[float] = None
    l10_rate: Optional[float] = None
    dtm: Optional[float] = None
    accuracy_sample: Optional[int] = None
