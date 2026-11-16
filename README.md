# Importer Performance Scorecard (prototype)

Independent portfolio project by Amaan Khan. Not affiliated with Porsche.

**All importer-level data here is synthetic** (seeded random numbers, seed 20261115). It describes no real importer.
Regional delivery figures on the page come from Porsche's public press releases and are cited on the page.

## What is in here
- `index.html` - the project page (self-contained; open it in a browser or host it on GitHub Pages).
- `build_model.py` - generates the synthetic data, runs data-quality rules, scores importers, runs the weight-sensitivity test, writes `data/`.
- `data/*.csv` - star schema for Power BI: `dim_importer`, `dim_kpi`, `dim_pillar`, `dim_quarter`, `fact_kpi_quarterly`, `fact_risk_gates`, plus outputs `fact_scorecard`, `fact_weight_sensitivity`, `dq_log`.
- `measures.dax` - core measures. Written as a design; not yet executed in Power BI Desktop.

## Load into Power BI Desktop
1. Get data > Text/CSV: load the six model tables.
2. Create relationships as listed at the top of `measures.dax` (all many-to-one, single direction).
3. Add the measures. Compare `Total Score` per importer against `data/fact_scorecard.csv`; they should match to rounding.
4. Fix any syntax issues and note them; do not publish numbers you have not reconciled.

## Method in one paragraph
Clean first (4 data-quality rules). Attainment per KPI = actual/target (or target/actual if lower is better), capped at 110%.
Pillar score = weighted mean of KPI attainments x 100. Total = pillar scores x pillar weights (30/20/20/15/15).
Any red risk gate removes an importer from the award ranking. Weight sensitivity: 5,000 Dirichlet draws centred on the base weights.

## Run it
`python3 build_model.py` (needs pandas and numpy).
