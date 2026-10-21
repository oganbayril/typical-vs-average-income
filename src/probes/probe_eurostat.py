"""Probe the EU-SILC datasets: dimensions, coverage, gaps, break flags.

For each dataset: print every dimension and its values, then for the slice
the project uses, one line per country in scope with first-last year, years
missing inside that range, break years and other flags.

Note: this shows all years, including the pre-EU-SILC ones the pipeline drops.

Run from the project root:
    uv run python src/probes/probe_eurostat.py              # all datasets
    uv run python src/probes/probe_eurostat.py ilc_mdes09   # one dataset
"""

import sys
from collections import Counter

from probe_common import EUROSTAT_SCOPE, read_eurostat_tsv, select

# The slice of each dataset the project uses (same as load_eurostat.py).
SLICES = {
    "ilc_di03": [
        {"age": "TOTAL", "sex": "T", "unit": "PPS", "statinfo": "MED_EI"},
        {"age": "TOTAL", "sex": "T", "unit": "PPS", "statinfo": "MEAN_EI"},
    ],
    "ilc_mdsd11": [{"age": "TOTAL", "sex": "T", "unit": "PC"}],
    "ilc_li02": [{"age": "TOTAL", "sex": "T", "unit": "PC", "statinfo": "MED_EI", "rskpovth": "B_60"}],
    "ilc_mdes04": [{"hhcomp": "TOTAL", "rskpovth": "TOTAL", "unit": "PC"}],
    "ilc_mdes09": [
        {"hhcomp": "TOTAL", "rskpovth": "TOTAL", "lev_diff": "GRT"},
        {"hhcomp": "TOTAL", "rskpovth": "TOTAL", "lev_diff": "DIF"},
    ],
    "ilc_peps01n": [{"age": "TOTAL", "sex": "T", "unit": "PC"}],
    "ilc_di12": [{"age": "TOTAL", "statinfo": "GINI_HND"}],
}


def describe_dimensions(data):
    for column in data.columns:
        if column in ("geo", "year", "value", "flag"):
            continue
        values = list(data[column].unique())
        print(f"  {column} ({len(values)}): {values[:30]}")


def describe_coverage(data):
    present = data.dropna(subset=["value"])
    missing = [c for c in EUROSTAT_SCOPE if c not in set(present["geo"])]
    print(f"  countries in scope with no data: {missing}")
    for country in EUROSTAT_SCOPE:
        rows = present[present["geo"] == country]
        if len(rows) == 0:
            continue
        years = sorted(int(y) for y in rows["year"].unique())
        gaps = [y for y in range(years[0], years[-1] + 1) if y not in years]
        breaks = sorted(int(y) for y in rows.loc[rows["flag"].str.contains("b"), "year"].unique())
        other_flags = Counter(f for f in rows["flag"] if f and "b" not in f)
        line = f"  {country}: {years[0]}-{years[-1]}"
        if gaps:
            line += f" gaps={gaps}"
        if breaks:
            line += f" breaks={breaks}"
        if other_flags:
            line += f" flags={dict(other_flags)}"
        print(line)


def main():
    datasets = sys.argv[1:] or list(SLICES)
    for dataset in datasets:
        data = read_eurostat_tsv(dataset)
        print("=" * 70)
        print(dataset)
        describe_dimensions(data)
        print(f"  latest year with any value: {data.dropna(subset=['value'])['year'].max()}")
        for filters in SLICES[dataset]:
            print(f"-- slice {filters}")
            describe_coverage(select(data, **filters))


if __name__ == "__main__":
    main()
