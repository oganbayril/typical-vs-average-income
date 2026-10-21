"""Shared helpers for the probe scripts.

Probes download whole datasets (not just the slices the pipeline uses), so
they can show every dimension and value. Files are cached in
data/raw/probes/ and reused on the next run.
"""

import gzip
import sys
from pathlib import Path

import pandas as pd
import requests

# Probes live in src/probes/; make src/ importable for country_codes etc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")  # country names with ü on Windows

from country_codes import EUROSTAT_TO_ISO3  # noqa: E402
from sources import RAW_DIR  # noqa: E402

PROBE_DIR = RAW_DIR / "probes"
EUROSTAT_TSV_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{dataset}?format=TSV&compressed=true"

# Countries in scope, in Eurostat's two-letter codes.
EUROSTAT_SCOPE = list(EUROSTAT_TO_ISO3.keys())


def fetch(url, filename):
    """Download url to data/raw/probes/<filename> unless already there."""
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    path = PROBE_DIR / filename
    if path.exists():
        return path
    print(f"Downloading {url}")
    response = requests.get(url, timeout=600)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def read_eurostat_tsv(dataset):
    """Return a whole Eurostat dataset in long format.

    Eurostat's TSV has one column per year and the other dimensions packed
    into the first column ("freq,unit,...,geo\\TIME_PERIOD"). Cells hold the
    value and the flag letters together, e.g. "20123 b" or ": " (missing).
    Columns returned: one per dimension, year, value, flag.
    """
    path = fetch(EUROSTAT_TSV_URL.format(dataset=dataset), f"{dataset}.tsv.gz")
    with gzip.open(path, "rt", encoding="utf-8") as f:
        wide = pd.read_csv(f, sep="\t", dtype=str)

    first = wide.columns[0]
    dimensions = first.split("\\")[0].split(",")
    keys = wide[first].str.split(",", expand=True)
    keys.columns = dimensions
    values = wide.drop(columns=first)
    values.columns = [c.strip() for c in values.columns]

    long = pd.concat([keys, values], axis=1).melt(id_vars=dimensions, var_name="year", value_name="cell")
    long["cell"] = long["cell"].str.strip()
    long["value"] = pd.to_numeric(long["cell"].str.extract(r"^([-\d.]+)")[0], errors="coerce")
    long["flag"] = long["cell"].str.extract(r"^[-\d.:]+\s*([a-z]*)")[0].fillna("")
    long["year"] = long["year"].astype(int)
    return long.drop(columns="cell")


def select(data, **filters):
    """Keep rows where each named column equals the given value."""
    for column, value in filters.items():
        data = data[data[column] == value]
    return data
