from typing import List
from ingest.schema import CanonicalProp

class UnifiedProp:
    def __init__(self, player_name, stat_type, line, sport, league="", game_date="",
                 pp_over_prob=None, pp_under_prob=None, pp_over_odds=None, pp_under_odds=None,
                 pp_l5_over_rate=None, pp_l10_over_rate=None, pp_dtm=None, pp_accuracy_sample=None,
                 sources=None, single_source=True, confidence_penalty=0.0):
        self.player_name = player_name
        self.stat_type = stat_type
        self.line = line
        self.sport = sport
        self.league = league
        self.game_date = game_date
        self.pp_over_prob = pp_over_prob
        self.pp_under_prob = pp_under_prob
        self.pp_over_odds = pp_over_odds
        self.pp_under_odds = pp_under_odds
        self.pp_l5_over_rate = pp_l5_over_rate
        self.pp_l10_over_rate = pp_l10_over_rate
        self.pp_dtm = pp_dtm
        self.pp_accuracy_sample = pp_accuracy_sample
        self.sources = sources or []
        self.single_source = single_source
        self.confidence_penalty = confidence_penalty

def merge_sources(pp_props: List[CanonicalProp], **kwargs) -> List[UnifiedProp]:
    """Convert PlayerProps.ai to unified format."""
    unified = []
    for pp in pp_props:
        pp_over = pp.p_model if pp.direction == "Over" else (1 - pp.p_model) if pp.p_model else None
        pp_under = (1 - pp.p_model) if pp.direction == "Over" and pp.p_model else pp.p_model if pp.p_model else None
        unified.append(UnifiedProp(
            player_name=pp.player, stat_type=pp.stat, line=pp.line, sport=pp.sport,
            league=pp.league or "", game_date=pp.game_time_cdt or "",
            pp_over_prob=pp_over, pp_under_prob=pp_under,
            pp_over_odds=pp.odds_american, pp_under_odds=pp.odds_american,
            pp_l5_over_rate=pp.l5, pp_l10_over_rate=pp.l10,
            pp_dtm=pp.dtm_pct, pp_accuracy_sample=pp.accuracy_sample,
            sources=["PlayerProps.ai"], single_source=True, confidence_penalty=0.0
        ))
    return unified
