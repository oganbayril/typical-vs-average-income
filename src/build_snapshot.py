"""Build the latest-year snapshot of the headline ratio, one row per country.

Each country's most recent value from the headline layer, with one exception
(decisions.EUROSTAT_DISCONTINUED): for countries whose Eurostat series has
ended, the snapshot takes the OECD value if the OECD has a newer year than
Eurostat's last one, marked source = OECD with a note on how far the two
sources differ for that country. If the OECD has nothing newer, the country
is left out of the snapshot (grey on the map). The time series in the layer
file is not touched: no country's series ever joins the two sources.

Output: data/processed/snapshot_median_mean_ratio.csv, the layer columns plus
- `tier_uncertain`: True for OECD-sourced countries within
  decisions.SOURCE_UNCERTAINTY of a tier boundary (decisions.TIER_BOUNDARIES),
  since on Eurostat's method they could fall in another tier
- `note`: text for the map's hover; empty when there is nothing to say

Run after build_headline.py:
    uv run python src/build_snapshot.py
"""

import pandas as pd

from decisions import (
    EUROSTAT_DISCONTINUED,
    MAP_FIRST_INCOME_YEAR,
    SOURCE_OECD,
    SOURCE_UNCERTAINTY,
    TIER_BOUNDARIES,
)
from layers import LAYER_COLUMNS
from sources import PROCESSED_DIR, save_processed

TIER_UNCERTAIN_NOTE = "Tier may differ under Eurostat's method."

OECD_EXTENSION_NOTE = (
    "OECD Income Distribution Database, not Eurostat: a different method. "
    "Where both sources exist, they usually agree within ±0.03."
)


def source_offset(country, eurostat, oecd):
    """Mean and range of OECD minus Eurostat for one country, matched years."""
    pairs = eurostat[eurostat["country"] == country].merge(
        oecd[oecd["country"] == country], on=["country", "year"], suffixes=("_eurostat", "_oecd")
    )
    difference = pairs["value_oecd"] - pairs["value_eurostat"]
    return difference.mean(), difference.min(), difference.max(), pairs["year"].min(), pairs["year"].max()


def discontinued_row(country, latest_eurostat_year, eurostat, oecd):
    """The OECD row to show instead of an ended Eurostat series, or None."""
    newer = oecd[(oecd["country"] == country) & (oecd["year"] > latest_eurostat_year)
                 & (oecd["income_year"] >= MAP_FIRST_INCOME_YEAR)]
    if len(newer) == 0:
        print(f"  {country}: Eurostat ends {latest_eurostat_year}, no newer OECD value -> left grey")
        return None

    row = newer.sort_values("year").iloc[[-1]].copy()
    mean, low, high, first, last = source_offset(country, eurostat, oecd)
    row["note"] = (
        f"Eurostat stopped covering this country after survey year {latest_eurostat_year} "
        f"(income year {latest_eurostat_year - 1}); this is the OECD value. In the years both "
        f"sources cover (survey years {first}-{last}) the OECD ratio is {mean:+.3f} on average "
        f"compared with Eurostat (range {low:+.3f} to {high:+.3f})."
    )
    print(f"  {country}: Eurostat ends {latest_eurostat_year} -> OECD {int(row['year'].iloc[0])} "
          f"(offset {mean:+.3f}, {low:+.3f} to {high:+.3f})")
    return row


def mark_tier_uncertain(snapshot):
    """Flag OECD values close enough to a tier boundary to switch tier.

    Eurostat values are not marked: the source uncertainty is about how far
    an OECD value can sit from what Eurostat would have measured. Values are
    not changed; only the new column and the note.
    """
    snapshot = snapshot.copy()
    near_boundary = pd.Series(False, index=snapshot.index)
    for boundary in TIER_BOUNDARIES:
        near_boundary = near_boundary | ((snapshot["value"] - boundary).abs() <= SOURCE_UNCERTAINTY)
    snapshot["tier_uncertain"] = near_boundary & (snapshot["source"] == SOURCE_OECD)

    for index in snapshot.index[snapshot["tier_uncertain"]]:
        note = snapshot.at[index, "note"]
        snapshot.at[index, "note"] = f"{note} {TIER_UNCERTAIN_NOTE}".strip()

    marked = snapshot.loc[snapshot["tier_uncertain"], "country"]
    print(f"Tier uncertain ({len(marked)}): {', '.join(sorted(marked))}")
    return snapshot


def main():
    headline = pd.read_csv(PROCESSED_DIR / "layer_median_mean_ratio.csv", keep_default_na=False)
    eurostat = pd.read_csv(PROCESSED_DIR / "eurostat_ratio.csv", keep_default_na=False)
    oecd = pd.read_csv(PROCESSED_DIR / "oecd_ratio.csv", keep_default_na=False)

    rows = []
    for country, series in headline.groupby("country"):
        latest = series.sort_values("year").iloc[[-1]].copy()
        if country in EUROSTAT_DISCONTINUED:
            replacement = discontinued_row(country, int(latest["year"].iloc[0]), eurostat, oecd)
            if replacement is not None:
                rows.append(replacement)
            continue
        if latest["source"].iloc[0] == SOURCE_OECD:
            latest["note"] = OECD_EXTENSION_NOTE
        else:
            latest["note"] = ""
        rows.append(latest)

    snapshot = pd.concat(rows, ignore_index=True)
    snapshot = mark_tier_uncertain(snapshot)
    snapshot = snapshot[LAYER_COLUMNS + ["tier_uncertain", "note"]]
    snapshot = snapshot.sort_values("value").reset_index(drop=True)
    save_processed(snapshot, "snapshot_median_mean_ratio.csv")

    print("\nIncome years in the snapshot:", snapshot["income_year"].value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
