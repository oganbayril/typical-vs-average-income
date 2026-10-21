"""Load the Eurostat (EU-SILC) layers.

Datasets (all annual, whole population, all countries):
- ilc_di03:   mean and median equivalised disposable income
              -> the median/mean ratio (headline, Eurostat part)
              -> median income in PPS (secondary layer)
- ilc_mdsd11: severe material and social deprivation rate
- ilc_li02:   at-risk-of-poverty rate (below 60% of the national median)
- ilc_mdes04: share who cannot face an unexpected financial expense
- ilc_mdes09: share making ends meet with great difficulty or difficulty

Steps:
1. Download each dataset (only the slices used) to data/raw/.
2. Keep countries in scope, drop years before each country's first EU-SILC
   survey (decisions.SILC_FIRST_YEAR), turn flag letters into words.
3. Save one tidy file per layer (format in layers.py). The Eurostat ratio is
   saved as eurostat_ratio.csv; build_headline.py turns it into the headline
   layer together with the OECD extension.

Run from the project root:
    uv run python src/load_eurostat.py
"""

import pandas as pd

from country_codes import EUROSTAT_TO_ISO3
from decisions import EUROSTAT_INCOME_YEAR_LAG, SILC_DEFAULT_FIRST_YEAR, SILC_FIRST_YEAR, SOURCE_EUROSTAT
from layers import combine_flags, eurostat_flag_words, save_layer
from sources import download_eurostat, save_processed


def load(dataset, key):
    """Download one dataset and return the rows in scope, flags as words."""
    raw = download_eurostat(dataset, key, f"{dataset}.csv")
    raw = raw.rename(columns={"geo": "eurostat_code", "TIME_PERIOD": "year", "OBS_VALUE": "value"})

    # Only countries in scope. This also drops EU and euro-area aggregates.
    data = raw[raw["eurostat_code"].isin(EUROSTAT_TO_ISO3.keys())].copy()
    data["country"] = data["eurostat_code"].map(EUROSTAT_TO_ISO3)
    data["flag"] = data["OBS_FLAG"].apply(eurostat_flag_words)
    # EU-SILC asks about last year's income (see decisions.py).
    data["income_year"] = data["year"] - EUROSTAT_INCOME_YEAR_LAG

    data = drop_pre_silc_years(data, dataset)
    data = data.dropna(subset=["value"])
    return data


def drop_pre_silc_years(data, dataset):
    """Drop years before the country's first EU-SILC survey, and say so."""
    first_year = data["eurostat_code"].map(SILC_FIRST_YEAR).fillna(SILC_DEFAULT_FIRST_YEAR)
    too_early = data["year"] < first_year
    dropped = data[too_early & data["value"].notna()]
    if len(dropped) > 0:
        countries = ", ".join(sorted(dropped["eurostat_code"].unique()))
        print(f"  {dataset}: dropped {len(dropped)} pre-EU-SILC values ({countries})")
    return data[~too_early]


def income_layers():
    """Median/mean ratio (headline, Eurostat part) and median income in PPS."""
    data = load("ilc_di03", "A.TOTAL.T.MEAN_EI+MED_EI.NAC+PPS.")

    # The ratio uses national currency (NAC): both numbers are in the same
    # currency in the same year, so the currency cancels out. NAC and EUR
    # give the same ratio; NAC avoids exchange-rate rounding.
    nac = data[data["unit"] == "NAC"]
    median = nac[nac["statinfo"] == "MED_EI"].set_index(["country", "year"])
    mean = nac[nac["statinfo"] == "MEAN_EI"].set_index(["country", "year"])
    both = median[["value", "flag"]].join(mean[["value", "flag"]], lsuffix="_median", rsuffix="_mean", how="inner")

    ratio = both.reset_index()
    ratio["value"] = (ratio["value_median"] / ratio["value_mean"]).round(4)
    # A ratio inherits every flag of the two numbers it is made of.
    ratio["flag"] = [combine_flags(a, b) for a, b in zip(ratio["flag_median"], ratio["flag_mean"])]
    ratio["income_year"] = ratio["year"] - EUROSTAT_INCOME_YEAR_LAG
    ratio["source"] = SOURCE_EUROSTAT
    ratio["unit"] = "ratio (median / mean equivalised disposable income)"
    save_processed(ratio[["country", "year", "income_year", "value", "source", "flag", "unit"]], "eurostat_ratio.csv")

    pps = data[(data["unit"] == "PPS") & (data["statinfo"] == "MED_EI")].copy()
    pps["source"] = SOURCE_EUROSTAT
    pps["unit"] = "PPS per year (median equivalised disposable income)"
    save_layer(pps, "median_income_pps")


def simple_layer(dataset, key, name, unit):
    """A layer that is one Eurostat series as published (a % of people)."""
    data = load(dataset, key)
    data["source"] = SOURCE_EUROSTAT
    data["unit"] = unit
    save_layer(data, name)


def ends_meet_layer():
    """Making ends meet with great difficulty + with difficulty.

    Eurostat publishes the two answers separately. Their sum is the usual
    headline figure (the OECD's "difficulty making ends meet" is exactly
    this sum of the same EU-SILC numbers). If either part is missing, the
    year is left out rather than counted as zero.
    """
    data = load("ilc_mdes09", "A.PC.GRT+DIF.TOTAL.TOTAL.")
    great = data[data["lev_diff"] == "GRT"].set_index(["country", "year"])
    some = data[data["lev_diff"] == "DIF"].set_index(["country", "year"])
    both = great[["value", "flag"]].join(some[["value", "flag"]], lsuffix="_great", rsuffix="_dif", how="inner")

    layer = both.reset_index()
    layer["value"] = (layer["value_great"] + layer["value_dif"]).round(1)
    layer["flag"] = [combine_flags(a, b) for a, b in zip(layer["flag_great"], layer["flag_dif"])]
    layer["income_year"] = layer["year"] - EUROSTAT_INCOME_YEAR_LAG
    layer["source"] = SOURCE_EUROSTAT
    layer["unit"] = "% of people (households with great difficulty or difficulty making ends meet)"
    save_layer(layer, "making_ends_meet")


def main():
    income_layers()
    simple_layer(
        "ilc_mdsd11", "A.TOTAL.T.PC.", "severe_deprivation",
        "% of people (severe material and social deprivation, 7+ of 13 items)",
    )
    simple_layer(
        "ilc_li02", "A.MED_EI.PC.B_60.T.TOTAL.", "at_risk_of_poverty",
        "% of people (below 60% of national median equivalised income)",
    )
    simple_layer(
        "ilc_mdes04", "A.TOTAL.TOTAL.PC.", "unexpected_expenses",
        "% of people (household cannot face an unexpected financial expense)",
    )
    ends_meet_layer()


if __name__ == "__main__":
    main()
