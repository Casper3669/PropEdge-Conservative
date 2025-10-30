import numpy as np, pandas as pd
from typing import List, Dict
STANDARD = {2:3.0, 3:6.0}
FLEX3 = {3:3.0, 2:1.0}
WHITELIST_PLUS = {("ast","points")}
BLACKLIST_MINUS = {("reb","reb"), ("points","points")}
def sigma_for_market(m, pace=100.0):
    base = {"points":7.0,"reb":3.0,"ast":3.2,"pa":6.0,"pr":7.0,"ra":4.8,"pra":8.5}.get(m,6.5)
    return base*np.sqrt(pace/100.0)
def normal_over_prob(mu, line, sigma):
    z = (line - mu)/max(1e-6, sigma)
    from math import erf, sqrt
    cdf = 0.5*(1.0 + erf(z/np.sqrt(2)))
    return 1.0 - cdf
def blend_p(row, pace=100.0):
    p = None
    if pd.notnull(row.get("prob_over")):
        p = 0.2*0.60 + 0.8*float(row["prob_over"])
    elif pd.notnull(row.get("proj_mean")):
        mkey = str(row["market"]).lower()
        sigma = sigma_for_market(mkey, pace)
        p = normal_over_prob(float(row["proj_mean"]), float(row["line"]), sigma)
        if str(row.get("side","over")) == "under": p = 1.0 - p
    else:
        p = 0.55
    return min(max(p, 0.01), 0.99)
def ev_3flex(p_list: List[float]) -> float:
    p = np.array(p_list); ev = 3.0*np.prod(p)
    for i in range(3): ev += 1.0*np.prod(np.delete(p, i))*(1.0 - p[i])
    return float(ev)
def ev_standard_k(p_list: List[float], k:int) -> float:
    return float(STANDARD[k]*np.prod(p_list))
def build_entries(props_df: pd.DataFrame, bankroll: float, pace_lookup=None) -> Dict:
    out = []; props_df = props_df.copy()
    props_df["p_est"] = props_df.apply(lambda r: blend_p(r, 100.0), axis=1)
    legs_std  = props_df[props_df["p_est"]>=0.58]
    legs_flex = props_df[props_df["p_est"]>=0.577]
    flex_pool = (legs_flex.sort_values("p_est", ascending=False).drop_duplicates(subset=["player"]))
    if len(flex_pool)>=3:
        tri = flex_pool.head(3); p = tri["p_est"].tolist(); ev = ev_3flex(p)
        stake = min(1.0, bankroll*0.025)
        out.append({"product":"classic_flex","format":"3-leg","legs":tri.to_dict("records"),
                    "EV_multiple":round(ev,4),"ROI":round(ev-1,4),"stake":stake,
                    "notes":["independent 3-flex"]})
    std_pool = legs_std.sort_values("p_est", ascending=False).drop_duplicates(subset=["player"])
    if len(std_pool)>=3:
        found = False; recs = std_pool.head(6).to_dict("records")
        for i in range(len(recs)):
            for j in range(i+1, len(recs)):
                a, b = recs[i], recs[j]
                pair = (str(a["market"]).lower(), str(b["market"]).lower())
                pair_rev = (pair[1], pair[0])
                if pair in WHITELIST_PLUS or pair_rev in WHITELIST_PLUS:
                    for k in range(len(recs)):
                        if k in (i,j): continue
                        c = recs[k]; legs = [a,b,c]
                        p = [x["p_est"] for x in legs]; ev = ev_standard_k(p,3)
                        stake = min(1.0, bankroll*0.025)
                        out.append({"product":"classic_standard","format":"3-leg(staggered)",
                                    "legs":legs,"EV_multiple":round(ev,4),"ROI":round(ev-1,4),"stake":stake,
                                    "contingency":{"trigger":"early_leg_miss",
                                                   "ev_2leg": round(3.0*(p[1]*p[2]) - 1.0,4),
                                                   "rule":"place if ev_2leg >= +0.05"},
                                    "notes":["whitelist same-game pair"]})
                        found = True; break
                if found: break
    totals = {"entries":len(out),"stake_sum": round(sum(e["stake"] for e in out),2)}
    return {"entries": out, "totals": totals}
