"""How much a country's median/mean ratio changes over a few income years.

Used to judge what mixing income years does in the latest view (the map's
footnote quotes these numbers; src/probes/probe_year_mixing.py prints them
in full).
"""

import pandas as pd


def ratio_changes(series, lag):
    """Absolute change over `lag` income years, per country and end year.

    `series` has country, income_year, value, flag (a Eurostat-format layer).
    Only pairs where both ends exist; `break_inside` says whether a break
    flag sits inside the span (start year excluded, end year included).
    """
    rows = []
    for country, group in series.groupby("country"):
        by_year = group.set_index("income_year")
        for year in by_year.index:
            start = year - lag
            if start not in by_year.index:
                continue
            span = by_year.loc[start + 1:year]
            rows.append({
                "country": country,
                "income_year": year,
                "change": abs(by_year.loc[year, "value"] - by_year.loc[start, "value"]),
                "break_inside": span["flag"].str.contains("break").any(),
            })
    return pd.DataFrame(rows)


def change_summary(series, lags=(1, 2, 3, 4)):
    """Median and 90th percentile of the absolute change, all pairs and break-free pairs."""
    rows = []
    for lag in lags:
        table = ratio_changes(series, lag)
        clean = table[~table["break_inside"]]
        rows.append({
            "years": lag,
            "pairs": len(table),
            "median": table["change"].median(),
            "p90": table["change"].quantile(0.9),
            "pairs_no_break": len(clean),
            "median_no_break": clean["change"].median(),
            "p90_no_break": clean["change"].quantile(0.9),
        })
    return pd.DataFrame(rows).set_index("years")
