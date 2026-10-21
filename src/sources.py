"""Download helpers for Eurostat and OECD data.

Both sources offer an SDMX web API that can return plain CSV, which pandas
reads directly. Every download is saved untouched to data/raw/ first, so the
processing can always be re-run (and checked) against exactly what was
received.
"""

from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHECKS_DIR = PROCESSED_DIR / "checks"

EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data"
OECD_URL = "https://sdmx.oecd.org/public/rest/data"


def _download(url, filename):
    """Download a URL and save the response text to data/raw/<filename>."""
    print(f"Downloading {url}")
    response = requests.get(url, timeout=300)
    response.raise_for_status()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / filename
    path.write_text(response.text, encoding="utf-8")
    print(f"  saved to {path}")
    return path


def download_eurostat(dataset, key, filename):
    """Download a Eurostat dataset as CSV and return it as a DataFrame.

    `key` selects values for each dimension, in the dataset's own order,
    separated by dots. Several values go together with "+", and an empty
    slot means "all values". Example for ilc_di03 (freq.age.sex.statinfo.unit.geo):
        "A.TOTAL.T.MEAN_EI+MED_EI.NAC."  -> mean and median, all countries
    """
    url = f"{EUROSTAT_URL}/{dataset}/{key}/?format=SDMX-CSV"
    path = _download(url, filename)
    # dtype=str for flags: an empty flag must stay "", not become NaN.
    return pd.read_csv(path, dtype={"OBS_FLAG": str}, keep_default_na=False, na_values={"OBS_VALUE": [""]})


def download_oecd(dataflow, key, filename):
    """Download an OECD Data Explorer dataflow as CSV and return a DataFrame.

    `dataflow` is "<agency>,<dataflow id>,<version>", e.g.
    "OECD.WISE.INE,DSD_WISE_IDD@DF_IDD,". `key` works like Eurostat's.
    """
    url = f"{OECD_URL}/{dataflow}/{key}?dimensionAtObservation=AllDimensions&format=csvfilewithlabels"
    path = _download(url, filename)
    return pd.read_csv(path, dtype={"OBS_STATUS": str})


def save_processed(df, filename):
    """Save a processed table to data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / filename
    df.to_csv(path, index=False)
    print(f"Saved {len(df)} rows to {path}")


def save_check(df, filename):
    """Save the output of an investigation to data/processed/checks/."""
    CHECKS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKS_DIR / filename
    df.to_csv(path, index=False)
    print(f"Saved {path}")
