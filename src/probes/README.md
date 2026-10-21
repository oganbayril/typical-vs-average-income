# Probes

Scripts used to check the sources before the pipeline was built. They only
download and print; nothing they produce feeds the layer files. Results are
written up in DATA_NOTES.md.

Raw downloads go to `data/raw/probes/` (not in git). Run from the project root:

| Script | What it checks | Run |
|---|---|---|
| `probe_eurostat.py` | Dimensions, country coverage, gaps and break flags of the EU-SILC datasets | `uv run python src/probes/probe_eurostat.py` |
| `probe_oecd.py` | OECD IDD codes in use and coverage of median/mean income; How's Life "difficulty making ends meet" coverage | `uv run python src/probes/probe_oecd.py` |
| `probe_wid.py` | WID top 10% share and data-quality grade for all countries in scope (reads only the needed files from the 900 MB bulk zip) | `uv run python src/probes/probe_wid.py` |
| `probe_spread.py` | Spread and rank correlation of the measures in one year (needs the layer files, so run the pipeline first) | `uv run python src/probes/probe_spread.py` |
| `probe_tiers.py` | Candidate tier schemes for the latest-year ratio: countries within ±0.03 of each boundary, largest gaps (needs the snapshot file) | `uv run python src/probes/probe_tiers.py` |
| `probe_suspicious.py` | The three series checked before publishing: Türkiye making ends meet, Slovakia and North Macedonia median/mean | `uv run python src/probes/probe_suspicious.py` |

`probe_eurostat.py` and `probe_oecd.py` take a minute or two (the full
datasets are downloaded once and reused if already in `data/raw/probes/`;
delete the folder to fetch fresh copies). `probe_wid.py` makes many small
range requests and takes a few minutes.
