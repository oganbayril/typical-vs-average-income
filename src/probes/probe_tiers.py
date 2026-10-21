"""Compare candidate tier schemes for the latest-year headline ratio.

The source check (check_robustness.py) found Eurostat and OECD ratios usually
agree within ±0.03. A tier boundary is robust if no country sits within 0.03
of it: then switching source could not move any country across the line.

For each scheme this prints, per boundary:
- countries within 0.03 (all), and how many of those are OECD-sourced
  (the values the ±0.03 source uncertainty really applies to)
- the margin: distance from the boundary to the nearest country
and the countries in each tier. The largest gaps in the data are printed
first, since boundaries placed in gaps are the most robust.

Reads data/processed/snapshot_median_mean_ratio.csv (run build_snapshot.py).

Run from the project root:
    uv run python src/probes/probe_tiers.py
"""

import pandas as pd

from probe_common import select  # noqa: F401  (sets up imports and encoding)
from sources import PROCESSED_DIR

UNCERTAINTY = 0.03

# Boundaries are lower edges of the upper tier: value >= boundary goes up.
SCHEMES = {
    "A. gaps, 3 tiers": [0.82, 0.90],
    "B. gaps, 4 tiers": [0.73, 0.82, 0.90],
    "C. round numbers, 4 tiers": [0.80, 0.85, 0.90],
    "D. robust gaps only, 3 tiers": [0.73, 0.82],
}


def largest_gaps(values, n=6):
    ordered = values.sort_values()
    gaps = pd.DataFrame({
        "below": ordered.index[:-1],
        "above": ordered.index[1:],
        "low": ordered.values[:-1],
        "high": ordered.values[1:],
    })
    gaps["gap"] = gaps["high"] - gaps["low"]
    gaps["midpoint"] = (gaps["low"] + gaps["high"]) / 2
    return gaps.sort_values("gap", ascending=False).head(n).round(4)


def describe_scheme(name, boundaries, snapshot):
    values = snapshot["value"]
    print("=" * 70)
    print(f"{name}: boundaries {boundaries}")
    total_near = set()
    for boundary in boundaries:
        near = snapshot[(values - boundary).abs() <= UNCERTAINTY]
        near_oecd = near[near["source"] == "OECD"]
        margin = (values - boundary).abs().min()
        total_near |= set(near.index)
        print(f"  {boundary:.2f}: {len(near)} within ±{UNCERTAINTY} ({len(near_oecd)} OECD: "
              f"{', '.join(near_oecd.index) or '-'}), nearest country {margin:.4f} away")
    print(f"  countries near any boundary: {len(total_near)} of {len(snapshot)}")

    edges = [-1.0] + boundaries + [2.0]
    for low, high in zip(edges[:-1], edges[1:]):
        members = snapshot[(values >= low) & (values < high)]
        label = f"< {high:.2f}" if low < 0 else (f">= {low:.2f}" if high > 1 else f"{low:.2f}-{high:.2f}")
        print(f"  {label:10s} ({len(members):2d}): {', '.join(members.index)}")


def main():
    snapshot = pd.read_csv(PROCESSED_DIR / "snapshot_median_mean_ratio.csv", keep_default_na=False)
    snapshot = snapshot.set_index("country").sort_values("value")

    print(f"{len(snapshot)} countries, income years {snapshot['income_year'].min()}-{snapshot['income_year'].max()}")
    print("Largest gaps between neighbouring countries:")
    print(largest_gaps(snapshot["value"]).to_string(index=False))

    for name, boundaries in SCHEMES.items():
        describe_scheme(name, boundaries, snapshot)


if __name__ == "__main__":
    main()
