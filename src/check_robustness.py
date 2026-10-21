"""How much does the median/mean ratio depend on the source?

For every country and year where both Eurostat and the OECD have a ratio
(after shifting OECD to the survey year), compute the absolute difference.
This does not change any layer; it measures how far an OECD-extension value
could sit from where Eurostat would have put it.

Also checked:
- The year shift itself: the same comparison without the shift. If the
  unshifted pairs matched better, the shift decision would be wrong.
- Rank stability: in each year, rank the countries both sources cover by
  each source and compare the ranks.

Outputs (data/processed/checks/):
- ratio_eurostat_vs_oecd.csv: every matched pair and its difference
- ratio_eurostat_vs_oecd_by_country.csv: summary per country

Run after load_eurostat.py and load_oecd.py:
    uv run python src/check_robustness.py
"""

import pandas as pd

from sources import PROCESSED_DIR, save_check

CLOSE = 0.01
ACCEPTABLE = 0.03


def match(eurostat, oecd, year_column):
    """Pair Eurostat and OECD ratios by country and the given OECD year column."""
    oecd = oecd[["country", "income_year", "value", "flag"]].assign(year=oecd[year_column])
    pairs = eurostat[["country", "year", "value", "flag"]].merge(
        oecd, on=["country", "year"], suffixes=("_eurostat", "_oecd")
    )
    pairs["difference"] = (pairs["value_oecd"] - pairs["value_eurostat"]).round(4)
    pairs["abs_difference"] = pairs["difference"].abs()
    return pairs


def rank_shifts(pairs):
    """Per year, how many places does each country move between sources?"""
    rows = []
    for year, group in pairs.groupby("year"):
        if len(group) < 10:  # too few countries for a ranking to mean much
            continue
        ranks = group[["country"]].copy()
        ranks["year"] = year
        ranks["countries_ranked"] = len(group)
        ranks["rank_eurostat"] = group["value_eurostat"].rank(ascending=False).values
        ranks["rank_oecd"] = group["value_oecd"].rank(ascending=False).values
        ranks["rank_shift"] = (ranks["rank_oecd"] - ranks["rank_eurostat"]).abs()
        rows.append(ranks)
    return pd.concat(rows, ignore_index=True)


def main():
    eurostat = pd.read_csv(PROCESSED_DIR / "eurostat_ratio.csv", keep_default_na=False)
    oecd = pd.read_csv(PROCESSED_DIR / "oecd_ratio.csv", keep_default_na=False)

    shifted = match(eurostat, oecd, "year")
    unshifted = match(eurostat, oecd, "income_year")
    print("Year shift test (mean absolute difference, lower = better match):")
    print(f"  OECD shifted +1: {shifted['abs_difference'].mean():.4f} over {len(shifted)} pairs")
    print(f"  not shifted:     {unshifted['abs_difference'].mean():.4f} over {len(unshifted)} pairs")

    pairs = shifted.sort_values(["country", "year"])
    save_check(pairs, "ratio_eurostat_vs_oecd.csv")

    by_country = pairs.groupby("country").agg(
        years=("year", "count"),
        first_year=("year", "min"),
        last_year=("year", "max"),
        mean_difference=("difference", "mean"),
        mean_abs_difference=("abs_difference", "mean"),
        max_abs_difference=("abs_difference", "max"),
    ).round(4).reset_index().sort_values("mean_abs_difference")
    save_check(by_country, "ratio_eurostat_vs_oecd_by_country.csv")

    n = len(pairs)
    print(f"\n{n} country-years in {pairs['country'].nunique()} countries have both sources")
    print(f"  within {CLOSE}:  {(pairs['abs_difference'] <= CLOSE).sum()} ({(pairs['abs_difference'] <= CLOSE).mean():.0%})")
    print(f"  within {ACCEPTABLE}:  {(pairs['abs_difference'] <= ACCEPTABLE).sum()} ({(pairs['abs_difference'] <= ACCEPTABLE).mean():.0%})")
    print(f"  over {ACCEPTABLE}:    {(pairs['abs_difference'] > ACCEPTABLE).sum()}")
    print("  percentiles of absolute difference:")
    print(pairs["abs_difference"].quantile([0.5, 0.9, 0.95, 1.0]).round(4).to_string())
    print(f"  mean signed difference (OECD - Eurostat): {pairs['difference'].mean():+.4f}")

    print("\nPer country, average absolute difference:")
    countries_close = by_country[by_country["mean_abs_difference"] <= CLOSE]["country"].tolist()
    countries_ok = by_country[(by_country["mean_abs_difference"] > CLOSE) & (by_country["mean_abs_difference"] <= ACCEPTABLE)]["country"].tolist()
    countries_far = by_country[by_country["mean_abs_difference"] > ACCEPTABLE]["country"].tolist()
    print(f"  within {CLOSE} ({len(countries_close)}): {', '.join(countries_close)}")
    print(f"  {CLOSE}-{ACCEPTABLE} ({len(countries_ok)}): {', '.join(countries_ok)}")
    print(f"  over {ACCEPTABLE} ({len(countries_far)}): {', '.join(countries_far)}")
    print(by_country.to_string(index=False))

    print("\nOutlier pairs (over 0.03):")
    outliers = pairs[pairs["abs_difference"] > ACCEPTABLE]
    print(outliers[["country", "year", "income_year", "value_eurostat", "value_oecd", "difference", "flag_eurostat"]].to_string(index=False))

    ranks = rank_shifts(pairs)
    save_check(ranks, "ratio_rank_shift.csv")
    print(f"\nRank shift between sources ({ranks['year'].nunique()} years with 10+ countries):")
    print(f"  median {ranks['rank_shift'].median():.1f}, 90th percentile {ranks['rank_shift'].quantile(0.9):.1f}, max {ranks['rank_shift'].max():.1f} places")
    latest = ranks[ranks["year"] == ranks["year"].max()]
    print(f"  latest year {latest['year'].iloc[0]} ({len(latest)} countries): median {latest['rank_shift'].median():.1f}, max {latest['rank_shift'].max():.1f}")


if __name__ == "__main__":
    main()
