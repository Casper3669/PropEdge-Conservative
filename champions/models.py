"""Champions lineup models."""
from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

class Pick(BaseModel):
    """Single pick in a Champions lineup."""
    player_name: str
    stat_type: str
    line: float
    direction: Literal["OVER", "UNDER"]
    sport: str
    game_date: str | None = None
    team: str | None = None
    win_prob: float = Field(ge=0, le=1)
    score: float
    tier: Literal["S", "A", "B"]
    start_time: Optional[datetime] = None
    ingested_at: Optional[datetime] = None

class Lineup(BaseModel):
    """Complete Champions lineup."""
    picks: list[Pick] = Field(min_length=2, max_length=8)
    num_legs: int = Field(ge=2, le=8)
    tier: Literal["S", "A", "B"]
    expected_win_prob: float = Field(ge=0, le=1)
    expected_base_multiplier: float
    expected_value: float
    avg_score: float
    min_score: float
    correlation_index: float = 0.0
    stake: float = 0.0
    category: str = "STANDARD"  # repurposed: STANDARD or FLEX

    @property
    def player_names(self) -> list[str]:
        return [p.player_name for p in self.picks]

    @property
    def teams(self) -> list[str]:
        return [p.team for p in self.picks if p.team]
