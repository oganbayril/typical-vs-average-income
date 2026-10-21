# typical-vs-average

Portfolio project (junior data analyst): median ÷ mean equivalised
disposable income ("the typical person has X% of the average") across
European and OECD countries, as a Plotly choropleth. Replaces
food-housing-spending-share as the main portfolio piece and copies its
structure and deploy setup.

## Decisions (2026-10-19)

- **Headline:** median/mean income ratio. Not deprivation, not WID.
- **Default source: Eurostat `ilc_di03` only.** Never blend or average
  Eurostat with OECD in one series (different equivalence scales, year
  labels off by one).
- **OECD IDD (`DSD_WISE_IDD@DF_IDD`) = extension layer**, only for OECD
  members with no Eurostat income data. OECD years shifted +1 to the
  EU-SILC survey year. Every OECD value has `source = OECD` so the map can
  hatch it with a note.
- **Secondary layers, Europe only, never the headline:** median income in
  PPS, `ilc_mdsd11`, `ilc_li02`, `ilc_mdes04`, `ilc_mdes09`.
- **WID excluded** from the main dataset (separate file for an optional
  side panel at most).
- **No pre-EU-SILC Eurostat data** (`decisions.SILC_FIRST_YEAR`).
- (2026-10-21) **Snapshot only:** UK/Iceland/Kosovo (Eurostat ended) show
  the OECD value if newer, hatched, else grey (`build_snapshot.py`). History
  is never joined.
- (2026-10-21) `income_year` column for display; layer files start at
  income year 2002. Project flags `break_nso` (TUR 2014, making ends meet)
  and `unexplained_outlier` (SVK 2023, ratio) in `decisions.PROJECT_FLAGS`;
  values and source flags never changed.
- Branch: `main`.
- Turkey is one country among the rest; don't single it out in framing.
- Country scope: same as food-housing-spending-share (EU27, EFTA, UK,
  candidates incl. Kosovo, all 38 OECD members).
- Processed data committed; `data/raw/` gitignored.
- Tooling: Python 3.13, uv + requirements.txt, pandas, requests. Run with
  `uv run python`, never bare `python`.

Known gotcha: Eurostat uses `EL`/`UK`, ISO uses `GR`/`GB`; WID uses `GR`,
`GB` and `KS` for Kosovo.

## Working agreement

- Steps in order, wait for the user's confirmation between them.
- Never silently fix data. Log issues in DATA_NOTES.md.
- If a decision conflicts with the data, stop and say so.
- Don't build the map until asked. Ask before expanding scope.
- Don't commit until the user has seen the diff/summary.
- User is self-taught: simple, readable pandas. Briefly explain WHY for
  non-obvious decisions so they can defend them in interviews.

## Status

- [x] Source checks (DATA_NOTES.md sections 1-4)
- [x] Data layer: layers, robustness check, suspicious-series checks,
  coverage report (2026-10-19)
- [x] UK/Iceland snapshot, income_year, project flags (2026-10-21)
- [x] Tiers: scheme B (0.73/0.82/0.90), tier_uncertain column (2026-10-21)
- [ ] Map (copy food-housing-spending-share `src/build_map.py` approach)
- [ ] Deploy (Hetzner VPS, Caddy per-site file, DuckDNS subdomain)

Pipeline: `load_eurostat.py` -> `load_oecd.py` -> `build_headline.py` ->
`check_robustness.py` -> `build_snapshot.py` -> `report_coverage.py` (all in
`src/`).
