"""Validate Champions lineup rules."""
from .models import Pick

def validate_lineup(picks: list[Pick]) -> tuple[bool, str]:
    # 1. 2-8 legs
    if not 2 <= len(picks) <= 8:
        return False, f"Invalid leg count: {len(picks)}"
    # 2. Unique player per lineup
    player_names = [p.player_name for p in picks]
    if len(set(player_names)) != len(player_names):
        return False, "Duplicate player in lineup"
    # 3. No duplicate player/stat/line regardless of direction
    dup_keys = [(p.player_name, p.stat_type, p.line) for p in picks]
    if len(set(dup_keys)) != len(dup_keys):
        return False, "Duplicate player/stat detected (OVER + UNDER)"
    # 4. Min 2 different teams (best-effort; if team unknown, allow)
    teams = [p.team for p in picks if p.team is not None]
    if len(teams) > 0 and len(set(teams)) < 2:
        return False, "Lineup must include at least 2 different teams"
    return True, "Valid"
