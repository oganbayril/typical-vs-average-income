"""Report which countries each layer covers, and up to which year.

Prints, per layer: number of countries, first and latest year, how many
countries reach the latest year, and the countries that stop earlier.
For the headline layer, also lists Eurostat countries vs OECD-extension
countries, and countries in scope with no data at all.

Saves data/processed/checks/coverage.csv (one row per layer and country).

Run after the pipeline:
    uv run python src/report_coverage.py
"""

import pandas as pd

from country_codes import EUROSTAT_TO_ISO3, ISO3_NAMES, OECD_MEMBERS_ISO3
from sources import PROCESSED_DIR, save_check

LAYERS = [
    "median_mean_ratio",
    "median_income_pps",
    "severe_deprivation",
    "at_risk_of_poverty",
    "unexpected_expenses",
    "making_ends_meet",
]
SCOPE = set(EUROSTAT_TO_ISO3.values()) | OECD_MEMBERS_ISO3


def main():
    rows = []
    for layer in LAYERS:
        data = pd.read_csv(PROCESSED_DIR / f"layer_{layer}.csv", keep_default_na=False)
        summary = data.groupby(["country", "source"]).agg(
            first_year=("year", "min"), latest_year=("year", "max"), years=("year", "count")
        ).reset_index()
        summary.insert(0, "layer", layer)
        rows.append(summary)

        latest = summary["latest_year"].max()
        behind = summary[summary["latest_year"] < latest].sort_values("latest_year")
        print(f"\n{layer}: {len(summary)} countries, {summary['first_year'].min()}-{latest}")
        print(f"  at {latest}: {(summary['latest_year'] == latest).sum()} countries")
        if len(behind) > 0:
            print("  stop earlier: " + ", ".join(f"{c} {y}" for c, y in zip(behind["country"], behind["latest_year"])))

    coverage = pd.concat(rows, ignore_index=True)
    save_check(coverage, "coverage.csv")

    headline = coverage[coverage["layer"] == "median_mean_ratio"]
    eurostat = sorted(headline.loc[headline["source"] == "Eurostat", "country"])
    oecd = sorted(headline.loc[headline["source"] == "OECD", "country"])
    none = sorted(SCOPE - set(headline["country"]))
    print(f"\nHeadline, Eurostat ({len(eurostat)}): {', '.join(eurostat)}")
    print(f"Headline, OECD extension ({len(oecd)}): {', '.join(oecd)}")
    print(f"In scope, no data ({len(none)}): {', '.join(f'{c} ({ISO3_NAMES.get(c, c)})' for c in none)}")


if __name__ == "__main__":
    main()
