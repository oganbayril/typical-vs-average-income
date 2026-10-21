"""Probe the OECD sources.

1. Income Distribution Database (OECD.WISE.INE,DSD_WISE_IDD@DF_IDD), whole
   dataflow: which codes are actually used in each dimension, and per country
   the years with median and mean disposable income (current definition,
   income definition since 2012). Years are OECD income years here.
2. How's Life current well-being (OECD.WISE.WDP,DSD_HSL@DF_HSL_CWB),
   measure 1_5 "Difficulty making ends meet": which countries and years.
   (Finding: for European countries it is the EU-SILC figure republished.)

Run from the project root:
    uv run python src/probes/probe_oecd.py
"""

import pandas as pd

from probe_common import fetch

OECD_URL = "https://sdmx.oecd.org/public/rest/data/{flow}/all?dimensionAtObservation=AllDimensions&format=csvfilewithlabels"
IDD = "OECD.WISE.INE,DSD_WISE_IDD@DF_IDD,"
HSL = "OECD.WISE.WDP,DSD_HSL@DF_HSL_CWB,"


def year_ranges(data, group_columns):
    """Print first-last year per group, listing the years when not continuous."""
    for keys, rows in data.groupby(group_columns):
        years = sorted(int(y) for y in rows["TIME_PERIOD"].unique())
        line = f"  {' '.join(keys)}: {years[0]}-{years[-1]} ({len(years)} years)"
        if len(years) != years[-1] - years[0] + 1:
            line += f" years={years}"
        provisional = sorted(rows.loc[rows["OBS_STATUS"] == "P", "TIME_PERIOD"].unique())
        if provisional:
            line += f" provisional={provisional}"
        print(line)


def probe_idd():
    path = fetch(OECD_URL.format(flow=IDD), "oecd_idd_all.csv")
    data = pd.read_csv(path, dtype=str)
    print("=" * 70)
    print("OECD IDD: codes in use")
    for column in ["MEASURE", "STATISTICAL_OPERATION", "UNIT_MEASURE", "METHODOLOGY", "DEFINITION", "POVERTY_LINE", "OBS_STATUS"]:
        label = data.columns[data.columns.get_loc(column) + 1]
        print(f"-- {column}")
        print(data.groupby([column, label]).size().to_string())
    print(f"-- countries: {sorted(data['REF_AREA'].unique())}")

    income = data[(data["MEASURE"] == "INC_DISP") & (data["AGE"] == "_T") & (data["METHODOLOGY"] == "METH2012")]
    for operation in ["MEDIAN", "MEAN"]:
        print(f"-- INC_DISP {operation}, by country and definition (income years)")
        year_ranges(income[income["STATISTICAL_OPERATION"] == operation], ["REF_AREA", "DEFINITION"])


def probe_hows_life():
    path = fetch(OECD_URL.format(flow=HSL), "oecd_hsl_cwb.csv")
    data = pd.read_csv(path, dtype=str)
    ends_meet = data[(data["MEASURE"] == "1_5") & (data["AGE"] == "_T") & (data["SEX"] == "_T")]
    print("=" * 70)
    print(f"How's Life 1_5 Difficulty making ends meet, unit: {ends_meet['Unit of measure'].iloc[0]}")
    year_ranges(ends_meet, ["REF_AREA"])


def main():
    probe_idd()
    probe_hows_life()


if __name__ == "__main__":
    main()
