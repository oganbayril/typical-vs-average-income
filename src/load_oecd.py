"""Load the OECD median/mean income ratio for all OECD countries.

Source: OECD Income Distribution Database (IDD),
dataflow OECD.WISE.INE,DSD_WISE_IDD@DF_IDD.

Slice used:
- MEASURE=INC_DISP, STATISTICAL_OPERATION=MEAN and MEDIAN
- UNIT_MEASURE=XDC_HH_EQ (national currency per equivalised household)
- AGE=_T (whole population)
- METHODOLOGY=METH2012 (income definition since 2012; the older one counts
  some income differently)
- DEFINITION=D_CUR (current definition only). Older series ("previous
  definition", e.g. Israel 2011-2022) are left out rather than joined on.

The result holds every OECD member the IDD covers, including European ones.
build_headline.py uses only those Eurostat does not cover; check_robustness.py
uses the European ones to compare the two sources.

Years are shifted from OECD income year to EU-SILC survey year
(decisions.OECD_YEAR_SHIFT); the original income year is kept in its own
column for checking.

Run from the project root:
    uv run python src/load_oecd.py
"""

from country_codes import OECD_MEMBERS_ISO3
from decisions import OECD_YEAR_SHIFT, SOURCE_OECD
from layers import combine_flags, oecd_flag_words
from sources import download_oecd, save_processed

DATAFLOW = "OECD.WISE.INE,DSD_WISE_IDD@DF_IDD,"
# Dimension order: REF_AREA.FREQ.MEASURE.STATISTICAL_OPERATION.UNIT_MEASURE.
#                  AGE.METHODOLOGY.DEFINITION.POVERTY_LINE
KEY = ".A.INC_DISP.MEAN+MEDIAN.XDC_HH_EQ._T.METH2012.D_CUR._Z"


def main():
    raw = download_oecd(DATAFLOW, KEY, "oecd_idd_income.csv")
    data = raw[raw["REF_AREA"].isin(OECD_MEMBERS_ISO3)].copy()
    data = data.rename(columns={"REF_AREA": "country", "TIME_PERIOD": "income_year", "OBS_VALUE": "value"})
    data["flag"] = data["OBS_STATUS"].fillna("").apply(oecd_flag_words)

    median = data[data["STATISTICAL_OPERATION"] == "MEDIAN"].set_index(["country", "income_year"])
    mean = data[data["STATISTICAL_OPERATION"] == "MEAN"].set_index(["country", "income_year"])
    both = median[["value", "flag"]].join(mean[["value", "flag"]], lsuffix="_median", rsuffix="_mean", how="inner")

    ratio = both.reset_index()
    ratio["value"] = (ratio["value_median"] / ratio["value_mean"]).round(4)
    ratio["flag"] = [combine_flags(a, b) for a, b in zip(ratio["flag_median"], ratio["flag_mean"])]
    ratio["year"] = ratio["income_year"] + OECD_YEAR_SHIFT
    ratio["source"] = SOURCE_OECD
    ratio["unit"] = "ratio (median / mean equivalised disposable income)"

    columns = ["country", "year", "income_year", "value", "source", "flag", "unit"]
    ratio = ratio[columns].sort_values(["country", "year"])
    save_processed(ratio, "oecd_ratio.csv")

    not_covered = sorted(OECD_MEMBERS_ISO3 - set(ratio["country"]))
    print(f"OECD members with no IDD median/mean on the current definition: {not_covered}")


if __name__ == "__main__":
    main()
