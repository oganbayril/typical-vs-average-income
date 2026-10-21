"""Spread and rank correlation of the measures in one survey year.

Reads the layer files (run the pipeline first), keeps Eurostat values for
one year, and prints min / median / max, the lowest and highest countries,
and the Spearman rank correlation between measures across countries.

Run from the project root:
    uv run python src/probes/probe_spread.py         # survey year 2024
    uv run python src/probes/probe_spread.py 2023
"""

import sys

import pandas as pd

from probe_common import select  # noqa: F401  (also sets up imports/encoding)
from sources import PROCESSED_DIR

LAYERS = [
    "median_mean_ratio",
    "median_income_pps",
    "severe_deprivation",
    "at_risk_of_poverty",
    "unexpected_expenses",
    "making_ends_meet",
]


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    columns = {}
    for layer in LAYERS:
        data = pd.read_csv(PROCESSED_DIR / f"layer_{layer}.csv", keep_default_na=False)
        data = data[(data["year"] == year) & (data["source"] == "Eurostat")]
        columns[layer] = data.set_index("country")["value"]
    table = pd.DataFrame(columns)

    print(f"Eurostat survey year {year}, countries per measure: {table.notna().sum().to_dict()}")
    print(table.describe().loc[["min", "50%", "max"]].round(3).to_string())
    for layer in LAYERS:
        ordered = table[layer].dropna().sort_values()
        low = ", ".join(f"{c} {v:g}" for c, v in ordered.head(3).items())
        high = ", ".join(f"{c} {v:g}" for c, v in ordered.tail(3).items())
        print(f"{layer:20s} lowest: {low} | highest: {high}")
    print("\nSpearman rank correlation:")
    print(table.corr(method="spearman").round(2).to_string())


if __name__ == "__main__":
    main()
