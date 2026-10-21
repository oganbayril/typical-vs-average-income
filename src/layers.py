"""The tidy format every layer file uses, and helpers to build it.

One file per layer in data/processed/, named layer_<name>.csv, one row per
country and year. These are the map-ready outputs.

    country      ISO-3 code (the map and both sources join on it)
    year         EU-SILC survey year (OECD values shifted, see decisions.py);
                 used to line the sources up
    income_year  the year the income was earned; used for display
    value        the number itself
    source       "Eurostat" or "OECD"; the map draws OECD values differently
    flag         words separated by "; " (break, provisional, estimated, ...,
                 plus this project's own: break_nso, unexplained_outlier),
                 empty when nobody attached a flag
    unit         what `value` is measured in
"""

from decisions import EUROSTAT_FLAG_WORDS, MAP_FIRST_INCOME_YEAR, OECD_STATUS_WORDS, PROJECT_FLAGS
from sources import save_processed

LAYER_COLUMNS = ["country", "year", "income_year", "value", "source", "flag", "unit"]


def eurostat_flag_words(letters):
    """Turn Eurostat flag letters ("bu") into words ("break; low reliability").

    Unknown letters are kept as they are rather than dropped, so nothing is
    silently lost; they would show up in the flag counts the loaders print.
    """
    words = []
    for letter in letters:
        word = EUROSTAT_FLAG_WORDS.get(letter, letter)
        if word not in words:
            words.append(word)
    return "; ".join(words)


def oecd_flag_words(status):
    """Turn an OECD OBS_STATUS code ("P") into a word ("provisional")."""
    return OECD_STATUS_WORDS.get(status, status)


def combine_flags(*flags):
    """Merge flag strings, e.g. for a ratio built from two flagged values."""
    words = []
    for flag in flags:
        for word in flag.split("; "):
            if word and word not in words:
                words.append(word)
    return "; ".join(words)


def add_project_flags(layer, name):
    """Append this project's own flags (decisions.PROJECT_FLAGS) to a layer.

    Only the flag column changes, and only by adding a word. Fails if a flag
    points at a row that does not exist, so a typo cannot silently do nothing.
    """
    layer = layer.copy()
    for (flag_layer, country, year), word in PROJECT_FLAGS.items():
        if flag_layer != name:
            continue
        row = (layer["country"] == country) & (layer["year"] == year)
        if row.sum() != 1:
            raise ValueError(f"project flag {word}: no single row for {country} {year} in {name}")
        layer.loc[row, "flag"] = layer.loc[row, "flag"].apply(lambda flag: combine_flags(flag, word))
        print(f"  {name}: added flag {word} to {country} {year}")
    return layer


def save_layer(df, name):
    """Check a layer, add project flags, keep map years, then save it."""
    missing = [c for c in LAYER_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"layer {name} is missing columns {missing}")

    layer = df[LAYER_COLUMNS].sort_values(["country", "year"]).reset_index(drop=True)
    if layer["value"].isna().any():
        raise ValueError(f"layer {name} has empty values; drop them before saving")
    if layer.duplicated(["country", "year"]).any():
        raise ValueError(f"layer {name} has more than one row per country and year")

    layer = add_project_flags(layer, name)

    too_early = layer["income_year"] < MAP_FIRST_INCOME_YEAR
    if too_early.any():
        countries = ", ".join(sorted(layer.loc[too_early, "country"].unique()))
        print(f"  {name}: left out {too_early.sum()} values before income year {MAP_FIRST_INCOME_YEAR} ({countries})")
    layer = layer[~too_early]

    save_processed(layer, f"layer_{name}.csv")
    return layer
