"""How much does a country's ratio change over 1-4 years?

The latest view mixes income years (2020-2025). This measures what that can
do: from the Eurostat yearly series, the absolute change in the median/mean
ratio between income years t-k and t, for k = 1, 2, 3, 4, over all
countries and years. Printed for all pairs and for pairs with no break flag
inside the span (a break can move the ratio for methodological reasons).

Then, for the latest view: which countries with older data sit close enough
to a tier line that a typical (90th percentile) change could move them
across it.

Run from the project root (after the pipeline):
    uv run python src/probes/probe_year_mixing.py
"""

import pandas as pd

from probe_common import select  # noqa: F401  (sets up imports and encoding)
from decisions import TIER_BOUNDARIES
from sources import PROCESSED_DIR
from year_changes import change_summary


def main():
    eurostat = pd.read_csv(PROCESSED_DIR / "eurostat_ratio.csv", keep_default_na=False)
    snapshot = pd.read_csv(PROCESSED_DIR / "snapshot_median_mean_ratio.csv", keep_default_na=False)

    summary = change_summary(eurostat)
    print("Absolute change in the Eurostat median/mean ratio over k income years")
    print(summary.round(4).to_string())

    common = snapshot["income_year"].mode().iloc[0]
    print(f"\nLatest view: most common income year {common}")
    for _, row in snapshot.sort_values("income_year").iterrows():
        age = common - row["income_year"]
        if age < 1:
            continue
        p90 = summary.loc[min(age, summary.index.max()), "p90_no_break"]
        distance = min(abs(row["value"] - b) for b in TIER_BOUNDARIES)
        risk = "could cross a tier line" if distance <= p90 else "tier unlikely to change"
        print(f"  {row['country']} income year {row['income_year']} ({age} older): "
              f"{row['value']:.3f}, {distance:.3f} from nearest line, 90th pct change {p90:.3f} -> {risk}")


if __name__ == "__main__":
    main()
