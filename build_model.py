"""
Importer Performance Scorecard - prototype model.

ALL importer-level data produced here is SYNTHETIC (seeded random numbers) and exists
only to demonstrate the KPI framework, scoring method, weight-sensitivity test, data-quality
checks and the Power BI star schema. It does not describe any real Porsche importer.

Run:  python3 build_model.py   (writes CSVs + summary.json next to ../site/data)
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 20261115
OUT = Path(__file__).resolve().parent.parent / "site" / "data"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(SEED)

# ----------------------------------------------------------------------------------
# 1. KPI dictionary (proposed framework; pillars mirror the publicly stated criteria
#    of the Importer of the Year award: customer satisfaction, service quality,
#    sales innovation, team efficiency, long-term loyalty)
# ----------------------------------------------------------------------------------
PILLARS = {
    "A": ("Customer satisfaction", 0.30),
    "B": ("Service quality", 0.20),
    "C": ("Sales innovation", 0.20),
    "D": ("Team efficiency", 0.15),
    "E": ("Long-term loyalty", 0.15),
}
# kpi_id, pillar, name, unit, direction (+1 higher is better, -1 lower is better), target, weight in pillar,
# typical (mean, sd) used only to generate synthetic data, definition
KPIS = [
    ("A1", "A", "Sales satisfaction index", "pts", +1, 90, 0.40, (86, 5), "Mean post-purchase survey score, 0-100, delivered vehicles in quarter"),
    ("A2", "A", "Service satisfaction index", "pts", +1, 90, 0.40, (85, 6), "Mean post-service survey score, 0-100, completed workshop orders in quarter"),
    ("A3", "A", "Complaints resolved within 48h", "%", +1, 95, 0.20, (88, 7), "Complaints closed within 48h / complaints opened in quarter"),
    ("B1", "B", "First-time-fix rate", "%", +1, 92, 0.40, (89, 4), "Repair orders closed without a repeat visit within 30 days / orders closed"),
    ("B2", "B", "Service retention (cars 4+ yrs)", "%", +1, 55, 0.40, (48, 9), "Cars aged 4+ years serviced at an authorised workshop / cars in operation of that age"),
    ("B3", "B", "Warranty claim rejection rate", "%", -1, 3, 0.20, (4.5, 1.8), "Warranty claims rejected by the manufacturer / claims submitted"),
    ("C1", "C", "Individualisation share of orders", "%", +1, 35, 0.30, (30, 9), "Orders with Exclusive Manufaktur / factory-individualised content / total orders"),
    ("C2", "C", "Pre-owned sales per 100 new", "units", +1, 25, 0.30, (21, 7), "Approved pre-owned retail sales per 100 new-vehicle deliveries"),
    ("C3", "C", "Lead-to-order conversion", "%", +1, 12, 0.40, (10, 3), "Orders / qualified leads in the period"),
    ("D1", "D", "Leads answered within 1 hour", "%", +1, 90, 0.40, (80, 10), "Qualified leads with a first human response within 1h / qualified leads"),
    ("D2", "D", "Certified staff share", "%", +1, 95, 0.30, (90, 6), "Customer-facing staff holding current certification / customer-facing staff"),
    ("D3", "D", "Delivery-date adherence", "%", +1, 90, 0.30, (84, 8), "Vehicles handed over on or before the promised date / vehicles delivered"),
    ("E1", "E", "Repeat-customer share of new sales", "%", +1, 45, 0.50, (40, 9), "New-vehicle buyers who already own or owned a Porsche / buyers"),
    ("E2", "E", "Net Promoter Score", "pts", +1, 60, 0.50, (52, 12), "% promoters minus % detractors, rolling four quarters"),
]
kpi_df = pd.DataFrame(
    [
        dict(kpi_id=k[0], pillar_id=k[1], pillar=PILLARS[k[1]][0], kpi_name=k[2], unit=k[3],
             direction="higher is better" if k[4] > 0 else "lower is better",
             target=k[5], weight_in_pillar=k[6], definition=k[8])
        for k in KPIS
    ]
)
pillar_df = pd.DataFrame(
    [dict(pillar_id=p, pillar=v[0], base_weight=v[1]) for p, v in PILLARS.items()]
)

# ----------------------------------------------------------------------------------
# 2. Synthetic importers and quarterly KPI facts (FY, 4 quarters)
# ----------------------------------------------------------------------------------
N = 16
importer_ids = [f"IMP{i:02d}" for i in range(1, N + 1)]
tiers = rng.choice(["Large", "Mid", "Small"], size=N, p=[0.25, 0.45, 0.30])
centres = np.array([{"Large": 4, "Mid": 2, "Small": 1}[t] for t in tiers]) + rng.integers(0, 2, size=N)
imp_df = pd.DataFrame(
    dict(importer_id=importer_ids, importer_label=[f"Importer {i:02d}" for i in range(1, N + 1)],
         market_tier=tiers, porsche_centres=centres)
)

latent = rng.normal(0, 1, size=N)                       # overall operating quality
pillar_bias = {p: rng.normal(0, 0.6, size=N) for p in PILLARS}  # importer-specific strengths/weaknesses
quarters = ["FY-Q1", "FY-Q2", "FY-Q3", "FY-Q4"]

rows = []
for i, imp in enumerate(importer_ids):
    for q in quarters:
        for (kid, pid, name, unit, d, target, w, (mu, sd), _) in KPIS:
            z = 0.55 * latent[i] + pillar_bias[pid][i] + rng.normal(0, 0.35)
            val = mu + d * sd * z
            if unit == "%":
                val = float(np.clip(val, 1, 100)) if kid != "B3" else float(np.clip(val, 0.5, 15))
            elif kid in ("A1", "A2"):
                val = float(np.clip(val, 50, 100))
            elif kid == "E2":
                val = float(np.clip(val, -20, 90))
            elif kid == "C2":
                val = float(np.clip(val, 2, 60))
            rows.append(dict(importer_id=imp, quarter=q, kpi_id=kid, value=round(val, 2), dq_flag=""))
fact = pd.DataFrame(rows)

# Injected data-quality problems (to demonstrate the checks; documented in the data dictionary)
inj = []
m = (fact.importer_id == "IMP07") & (fact.quarter == "FY-Q3") & (fact.kpi_id == "B1")
fact.loc[m, "value"] = np.nan; fact.loc[m, "dq_flag"] = "INJECTED: missing value"
inj.append("IMP07 FY-Q3 B1 left blank")
m = (fact.importer_id == "IMP12") & (fact.quarter == "FY-Q2") & (fact.kpi_id == "A3")
fact.loc[m, "value"] = 982.0; fact.loc[m, "dq_flag"] = "INJECTED: unit error (count entered, not %)"
inj.append("IMP12 FY-Q2 A3 entered as 982 instead of a percentage")
m = (fact.importer_id == "IMP03") & (fact.quarter == "FY-Q4") & (fact.kpi_id == "C2")
fact.loc[m, "value"] = 0.0; fact.loc[m, "dq_flag"] = "INJECTED: suspicious zero"
inj.append("IMP03 FY-Q4 C2 reported as 0")
m = (fact.importer_id == "IMP09") & (fact.quarter == "FY-Q1") & (fact.kpi_id == "D1")
fact.loc[m, "value"] = 31.0; fact.loc[m, "dq_flag"] = "INJECTED: digit typo (31 instead of ~81)"
inj.append("IMP09 FY-Q1 D1 entered as 31 (typo)")

# ----------------------------------------------------------------------------------
# 3. Data-quality rules (run BEFORE scoring)
# ----------------------------------------------------------------------------------
RANGE = {"%": (0, 100), "pts": (-100, 100), "units": (0, 200)}
kpi_meta = {k[0]: k for k in KPIS}
dq_log = []
clean = fact.copy()
clean["value_clean"] = clean["value"]
for idx, r in clean.iterrows():
    k = kpi_meta[r.kpi_id]
    lo, hi = RANGE[k[3]]
    v = r.value
    if pd.isna(v):
        dq_log.append(dict(importer_id=r.importer_id, quarter=r.quarter, kpi_id=r.kpi_id, rule="R1 completeness", action="excluded; imputed with importer's mean of other quarters", value=None))
        clean.at[idx, "value_clean"] = np.nan
    elif not (lo <= v <= hi):
        dq_log.append(dict(importer_id=r.importer_id, quarter=r.quarter, kpi_id=r.kpi_id, rule="R2 plausible range", action="excluded; imputed with importer's mean of other quarters", value=v))
        clean.at[idx, "value_clean"] = np.nan
    elif v == 0 and k[3] in ("units", "%") and k[0] not in ("B3",):
        dq_log.append(dict(importer_id=r.importer_id, quarter=r.quarter, kpi_id=r.kpi_id, rule="R3 zero on a rate that cannot be zero", action="excluded; imputed with importer's mean of other quarters", value=v))
        clean.at[idx, "value_clean"] = np.nan
# R4 outlier vs own history: a quarter is flagged when it sits more than 4 pooled standard
# deviations from the importer's own median for that KPI. The pooled SD is estimated from every
# importer's quarter-to-quarter deviations for that KPI (using only values that passed R1-R3), so a
# single importer's four data points do not have to estimate their own spread.
for kid, gk in clean.groupby("kpi_id"):
    dev = []
    for imp, g in gk.groupby("importer_id"):
        v = g["value_clean"].dropna()
        if len(v) >= 3:
            dev.extend((v - v.median()).tolist())
    pooled_sd = float(np.std(dev)) if dev else 0.0
    if pooled_sd == 0:
        continue
    for imp, g in gk.groupby("importer_id"):
        v = g["value_clean"].dropna()
        if len(v) < 3:
            continue
        med = v.median()
        for idx, val in g["value_clean"].items():
            if pd.notna(val) and abs(val - med) > 4 * pooled_sd:
                dq_log.append(dict(importer_id=imp, quarter=clean.at[idx, "quarter"], kpi_id=kid, rule="R4 outlier vs own history (>4 pooled SD)", action="excluded pending confirmation; imputed with importer's mean of other quarters", value=float(val)))
                clean.at[idx, "value_clean"] = np.nan
# imputation = importer's mean of its other valid quarters for that KPI
clean["value_used"] = clean["value_clean"]
for (imp, kid), g in clean.groupby(["importer_id", "kpi_id"]):
    mean_other = g["value_clean"].mean()
    clean.loc[g.index, "value_used"] = g["value_clean"].fillna(mean_other)
dq_df = pd.DataFrame(dq_log)

# ----------------------------------------------------------------------------------
# 4. Risk gates (not scored; they decide eligibility / escalation) - synthetic
# ----------------------------------------------------------------------------------
gates = []
for i, imp in enumerate(importer_ids):
    cur = float(np.clip(rng.normal(1.5, 0.35), 0.7, 2.6))   # current ratio
    lev = float(np.clip(rng.normal(1.8, 0.9), 0.2, 5.0))     # net debt / EBITDA
    findings = int(np.clip(rng.poisson(0.6), 0, 6))          # open high-severity audit findings
    complete = float(np.clip(rng.normal(97.5, 2.2), 85, 100)) # reporting completeness %
    gates.append(dict(importer_id=imp, current_ratio=round(cur, 2), net_debt_to_ebitda=round(lev, 2),
                      open_high_findings=findings, reporting_completeness_pct=round(complete, 1)))
gate_df = pd.DataFrame(gates)
# one deliberately injected scenario so the gate logic has something to show
gate_df.loc[gate_df.importer_id == "IMP11", ["open_high_findings"]] = 4
gate_df.loc[gate_df.importer_id == "IMP05", ["net_debt_to_ebitda"]] = 3.4

def gate_status(r):
    red, amber = [], []
    if r.open_high_findings >= 3: red.append("integrity: >=3 open high-severity findings")
    elif r.open_high_findings >= 1: amber.append("integrity: open high-severity finding(s)")
    if r.current_ratio < 1.0 or r.net_debt_to_ebitda > 4.0: red.append("financial: liquidity/leverage breach")
    elif r.current_ratio < 1.2 or r.net_debt_to_ebitda > 3.0: amber.append("financial: liquidity/leverage watch")
    if r.reporting_completeness_pct < 90: red.append("data: reporting completeness < 90%")
    elif r.reporting_completeness_pct < 95: amber.append("data: reporting completeness < 95%")
    status = "RED" if red else ("AMBER" if amber else "GREEN")
    return pd.Series(dict(gate_status=status, gate_reasons="; ".join(red + amber)))
gate_df = pd.concat([gate_df, gate_df.apply(gate_status, axis=1)], axis=1)

# ----------------------------------------------------------------------------------
# 5. Scoring
#    attainment = actual/target (higher better) or target/actual (lower better), capped at 110%
#    pillar score = weighted mean of attainment x 100 ; total = sum(pillar weight x pillar score)
# ----------------------------------------------------------------------------------
CAP = 1.10
annual = clean.groupby(["importer_id", "kpi_id"], as_index=False)["value_used"].mean().rename(columns={"value_used": "annual_value"})
def attain(r):
    k = kpi_meta[r.kpi_id]
    t = k[5]; d = k[4]; v = r.annual_value
    a = v / t if d > 0 else t / max(v, 1e-9)
    return float(np.clip(a, 0, CAP))
annual["attainment"] = annual.apply(attain, axis=1)
annual["pillar_id"] = annual.kpi_id.map(lambda x: kpi_meta[x][1])
annual["w_in_pillar"] = annual.kpi_id.map(lambda x: kpi_meta[x][6])
pillar_scores = (annual.assign(wa=annual.attainment * annual.w_in_pillar)
                 .groupby(["importer_id", "pillar_id"], as_index=False)["wa"].sum()
                 .rename(columns={"wa": "pillar_score"}))
pillar_scores["pillar_score"] *= 100
wide = pillar_scores.pivot(index="importer_id", columns="pillar_id", values="pillar_score")
base_w = np.array([PILLARS[p][1] for p in wide.columns])
wide["total_score"] = wide[list(wide.columns)].values @ base_w
score_df = wide.reset_index().merge(gate_df[["importer_id", "gate_status", "gate_reasons"]], on="importer_id")
score_df["eligible"] = score_df.gate_status != "RED"
score_df["rank_score_only"] = score_df.total_score.rank(ascending=False, method="min").astype(int)
elig = score_df[score_df.eligible].copy()
elig["rank_eligible"] = elig.total_score.rank(ascending=False, method="min").astype(int)
score_df = score_df.merge(elig[["importer_id", "rank_eligible"]], on="importer_id", how="left")
score_df = score_df.sort_values("total_score", ascending=False).reset_index(drop=True)

# ----------------------------------------------------------------------------------
# 6. Weight sensitivity (Monte Carlo): Dirichlet draws centred on the base weights
# ----------------------------------------------------------------------------------
DRAWS = 5000
alpha = 20 * base_w
W = rng.dirichlet(alpha, size=DRAWS)                      # DRAWS x 5 (about +/-10 pp on a 30% weight)
P = wide[list(wide.columns[:-1])].values                    # N x 5 pillar scores (order A..E)
order = list(wide.index)
tot = W @ P.T                                               # DRAWS x N
elig_mask = np.array([bool(score_df.loc[score_df.importer_id == imp, "eligible"].iloc[0]) for imp in order])
tot_masked = np.where(elig_mask[None, :], tot, -np.inf)
ranks = (-tot_masked).argsort(axis=1).argsort(axis=1) + 1   # 1 = best
sens = []
for j, imp in enumerate(order):
    if not elig_mask[j]:
        sens.append(dict(importer_id=imp, eligible=False)); continue
    r = ranks[:, j]
    sens.append(dict(importer_id=imp, eligible=True, p_rank1=float((r == 1).mean()), p_top3=float((r <= 3).mean()),
                     median_rank=float(np.median(r)), rank_p05=float(np.percentile(r, 5)), rank_p95=float(np.percentile(r, 95))))
sens_df = pd.DataFrame(sens)

# pillar-out test: drop one pillar at a time, renormalise weights, does the leader change?
pillar_out = []
ids_sorted_elig = list(elig.sort_values("total_score", ascending=False).importer_id)
leader_base = ids_sorted_elig[0]
for k, p in enumerate(wide.columns[:-1]):
    w = base_w.copy(); w[k] = 0; w = w / w.sum()
    t = P @ w
    t_el = np.where(elig_mask, t, -np.inf)
    lead = order[int(np.argmax(t_el))]
    pillar_out.append(dict(dropped_pillar=p, leader=lead, same_leader_as_base=(lead == leader_base)))
pillar_out_df = pd.DataFrame(pillar_out)

# ----------------------------------------------------------------------------------
# 7. Star schema export (Power BI ready)
# ----------------------------------------------------------------------------------
dim_date = pd.DataFrame(dict(quarter=quarters, quarter_index=[1, 2, 3, 4]))
imp_df.to_csv(OUT / "dim_importer.csv", index=False)
kpi_df.to_csv(OUT / "dim_kpi.csv", index=False)
pillar_df.to_csv(OUT / "dim_pillar.csv", index=False)
dim_date.to_csv(OUT / "dim_quarter.csv", index=False)
clean[["importer_id", "quarter", "kpi_id", "value", "value_used", "dq_flag"]].to_csv(OUT / "fact_kpi_quarterly.csv", index=False)
gate_df.to_csv(OUT / "fact_risk_gates.csv", index=False)
score_df.to_csv(OUT / "fact_scorecard.csv", index=False)
sens_df.to_csv(OUT / "fact_weight_sensitivity.csv", index=False)
dq_df.to_csv(OUT / "dq_log.csv", index=False)

# ----------------------------------------------------------------------------------
# 8. Summary for the website
# ----------------------------------------------------------------------------------
lab = dict(zip(imp_df.importer_id, imp_df.importer_label))
def lead_gap(imp):
    """root-cause view: which pillars explain the gap between this importer and the eligible leader (weighted points)"""
    lead = score_df[score_df.importer_id == leader_base].iloc[0]
    me = score_df[score_df.importer_id == imp].iloc[0]
    return {p: round(float((me[p] - lead[p]) * PILLARS[p][1]), 2) for p in PILLARS}

summary = dict(
    seed=SEED, draws=DRAWS, cap=CAP,
    pillars={p: dict(name=v[0], weight=v[1]) for p, v in PILLARS.items()},
    kpis=kpi_df.to_dict(orient="records"),
    importers=[
        dict(id=r.importer_id, label=lab[r.importer_id],
             tier=str(imp_df.set_index("importer_id").loc[r.importer_id, "market_tier"]),
             centres=int(imp_df.set_index("importer_id").loc[r.importer_id, "porsche_centres"]),
             total=round(float(r.total_score), 2),
             pillars={p: round(float(getattr(r, p)), 1) for p in PILLARS},
             gate=r.gate_status, reasons=r.gate_reasons, eligible=bool(r.eligible),
             rank_score_only=int(r.rank_score_only),
             rank_eligible=(None if pd.isna(r.rank_eligible) else int(r.rank_eligible)),
             gap_to_leader=lead_gap(r.importer_id))
        for r in score_df.itertuples()
    ],
    leader=lab[leader_base],
    sensitivity=[dict(id=r.importer_id, label=lab[r.importer_id], **{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r._asdict().items() if k not in ("Index", "importer_id")}) for r in sens_df.itertuples()],
    pillar_out=pillar_out_df.assign(leader=pillar_out_df.leader.map(lab)).to_dict(orient="records"),
    dq=dict(injected=inj, caught=dq_df.to_dict(orient="records")),
    gates=gate_df.to_dict(orient="records"),
)
(OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
print("leader (eligible):", lab[leader_base])
print(score_df[["importer_id", "total_score", "gate_status", "rank_score_only", "rank_eligible"]].head(8).to_string())
print(sens_df.sort_values("p_rank1", ascending=False).head(6).to_string())
print(pillar_out_df.to_string())
print("DQ caught:", len(dq_df)); print(dq_df.to_string())
