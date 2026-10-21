"""Data decisions in one place, so they can be read (and defended) together.

Background and evidence for each: DATA_NOTES.md and the README's
"Data limitations" section.
"""

# --- Sources -----------------------------------------------------------------

SOURCE_EUROSTAT = "Eurostat"
SOURCE_OECD = "OECD"

# The headline (median/mean ratio) comes from Eurostat ilc_di03 only. OECD
# fills in only OECD members with no Eurostat income data at all. A country
# never gets a series made of both sources (no splicing, no averaging):
# the two use different equivalence scales and income years, so a blend would
# be a number nobody publishes. Countries where Eurostat stops early keep a
# Eurostat-only series; the one exception is the latest-year snapshot below.

# Countries whose Eurostat series has ended (UK after 2018 because of Brexit;
# Iceland after 2020; Kosovo has a single year, 2018). Their Eurostat history
# stays as it is. Only in the latest-year snapshot (build_snapshot.py): if the
# OECD has a newer value, it is shown instead, hatched, as source = OECD;
# otherwise the country is left grey in the snapshot.
# Kosovo is not an OECD member, so it is always grey in the snapshot.
EUROSTAT_DISCONTINUED = {"GBR", "ISL", "XKX"}

# --- Tiers (headline ratio) ----------------------------------------------------

# Lower edges of the upper tiers: a value >= 0.90 is in the top tier, etc.
# Chosen 2026-10-21 (scheme B in DATA_NOTES.md T1): each boundary sits in the
# widest gap between neighbouring countries available at that level.
TIER_BOUNDARIES = [0.73, 0.82, 0.90]

# Eurostat and OECD ratios for the same country usually agree within this
# (95% of matched years, check_robustness.py). An OECD-sourced country this
# close to a boundary could be in another tier on Eurostat's method.
SOURCE_UNCERTAINTY = 0.03

# --- Years -------------------------------------------------------------------

# All layers use Eurostat's year label: the EU-SILC survey year. The income
# behind it is from the previous calendar year (Ireland and the UK use a
# 12-month period close to the survey instead).
# The OECD labels by income year, so OECD year N is shifted to N + 1 to sit
# next to the Eurostat survey that measured the same income year.
OECD_YEAR_SHIFT = 1

# Every layer also has an income_year column, used for display: Eurostat
# survey year - 1, OECD as published. (`year` stays the survey year, so the
# two sources line up internally.)
EUROSTAT_INCOME_YEAR_LAG = 1

# Layer files (the map-ready outputs) start at income year 2002, the first
# income year of EU-SILC (survey 2003). Older OECD years (e.g. Canada from
# 1976) stay in data/processed/oecd_ratio.csv but are not mapped.
MAP_FIRST_INCOME_YEAR = 2002

# First EU-SILC survey year per country. Earlier Eurostat values come from the
# European Community Household Panel (ECHP, 1995-2001) or from national
# surveys (around 2000-2004), and are not comparable, so they are dropped
# rather than spliced on. Countries not listed start in 2005, or later when
# their Eurostat data simply begins later (e.g. Bulgaria 2006, Romania 2007).
SILC_FIRST_YEAR = {
    # EU-SILC launched in 2003 in these countries (under a gentlemen's
    # agreement, before the regulation).
    "AT": 2003, "BE": 2003, "DK": 2003, "EL": 2003, "IE": 2003, "LU": 2003,
    "NO": 2003,
    # 2004: the rest of the EU-15 except DE, NL, UK, plus Estonia and Iceland.
    "ES": 2004, "FI": 2004, "FR": 2004, "IT": 2004, "PT": 2004, "SE": 2004,
    "EE": 2004, "IS": 2004,
    # Türkiye: EU-SILC from 2006. ilc_li02 also has a 2002 value from before
    # EU-SILC, and flags a break in 2006.
    "TR": 2006,
}
SILC_DEFAULT_FIRST_YEAR = 2005

# --- Flags -------------------------------------------------------------------

# Eurostat flag letters (an observation can carry several, e.g. "bu").
EUROSTAT_FLAG_WORDS = {
    "b": "break",
    "p": "provisional",
    "e": "estimated",
    "s": "estimated",  # Eurostat estimate
    "u": "low reliability",
    "d": "definition differs",
    "c": "confidential",
    "n": "not significant",
}

# Flags this project adds on top of the sources' own flags. Values and the
# sources' flags are never changed; these words are appended.
# Key: (layer name, ISO-3 country, survey year).
PROJECT_FLAGS = {
    # Türkiye's statistics office (TurkStat) gives the length of its
    # comparable SILC series as "2024 - 2014 + 1 = 11 years", i.e. a break in
    # 2014, in its quality report published by Eurostat (metadata page
    # ilc_simsilc_tr, section 15.2.1). Eurostat's data has no break flag there.
    ("making_ends_meet", "TUR", 2014): "break_nso",
    # Slovakia 2023 ratio 0.990: a one-year spike seen only in Eurostat (the
    # OECD has 0.957 for the same income year), no break flag, no
    # explanation found. See DATA_NOTES.md R3.
    ("median_mean_ratio", "SVK", 2023): "unexplained_outlier",
}

# OECD OBS_STATUS codes (SDMX standard).
OECD_STATUS_WORDS = {
    "A": "",  # normal value
    "P": "provisional",
    "E": "estimated",
    "B": "break",
    "F": "forecast",
}
