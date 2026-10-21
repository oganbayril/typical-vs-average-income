"""The three series checked before anything is published.

Prints the evidence used in DATA_NOTES.md (section "Suspicious series"):
- Türkiye, ilc_mdes09: all six "ability to make ends meet" answers per year,
  to see whether people moved between neighbouring answers (a sign of a
  question or survey change) or the whole distribution shifted; plus
  ilc_mdes04 and ilc_li02 for comparison.
- Slovakia and North Macedonia, ilc_di03 + ilc_di12: median, mean, ratio
  and the Gini coefficient, to see whether the ratio's movement is
  confirmed by an independent inequality measure.
- The OECD ratio for the same income year where it exists (needs
  data/processed/oecd_ratio.csv, i.e. run src/load_oecd.py first).

Nothing is changed; this only prints.

Run from the project root:
    uv run python src/probes/probe_suspicious.py
"""

import pandas as pd

from probe_common import read_eurostat_tsv, select
from sources import PROCESSED_DIR


def turkiye_ends_meet():
    data = read_eurostat_tsv("ilc_mdes09")
    tr = select(data, geo="TR", hhcomp="TOTAL", rskpovth="TOTAL")
    tr = tr[tr["year"] >= 2008]
    table = tr.pivot_table(index="year", columns="lev_diff", values="value")
    print("Türkiye, ability to make ends meet, % of people (ilc_mdes09)")
    print(table[["GRT", "DIF", "SOME", "FEASY", "EASY", "VEASY"]].to_string())
    print("break flags:", sorted(int(y) for y in tr.loc[tr["flag"].str.contains("b"), "year"].unique()))

    unexpected = select(read_eurostat_tsv("ilc_mdes04"), geo="TR", hhcomp="TOTAL", rskpovth="TOTAL", unit="PC")
    poverty = select(read_eurostat_tsv("ilc_li02"), geo="TR", statinfo="MED_EI", rskpovth="B_60", sex="T", age="TOTAL", unit="PC")
    both = pd.DataFrame({
        "cannot_face_unexpected": unexpected.set_index("year")["value"],
        "at_risk_of_poverty": poverty.set_index("year")["value"],
    })
    print(both.loc[2008:].to_string())


def ratio_and_gini(country, iso3):
    income = select(read_eurostat_tsv("ilc_di03"), geo=country, age="TOTAL", sex="T", unit="NAC")
    table = income.pivot_table(index="year", columns="statinfo", values="value")
    table["ratio"] = (table["MED_EI"] / table["MEAN_EI"]).round(3)
    flags = select(income, statinfo="MED_EI").set_index("year")["flag"]
    table["flag"] = flags

    gini = select(read_eurostat_tsv("ilc_di12"), geo=country, age="TOTAL")
    table["gini"] = gini.set_index("year")["value"]

    oecd_path = PROCESSED_DIR / "oecd_ratio.csv"
    if oecd_path.exists():
        oecd = pd.read_csv(oecd_path)
        table["oecd_ratio_same_income_year"] = oecd[oecd["country"] == iso3].set_index("year")["value"]

    print(f"\n{country}: median/mean (ilc_di03, NAC), Gini (ilc_di12), OECD ratio")
    print(table.loc[2012:].to_string())


def main():
    turkiye_ends_meet()
    ratio_and_gini("SK", "SVK")
    ratio_and_gini("MK", "MKD")


if __name__ == "__main__":
    main()
