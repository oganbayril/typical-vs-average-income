"""Build the headline layer: median/mean income ratio, one source per country.

- Countries with any Eurostat income data: Eurostat values only, all years.
- OECD members with no Eurostat income data: OECD values (the "extension").
  Their source column says "OECD" so the map can draw them differently and
  show a note.

No country ever has values from both sources (see decisions.py). A country
Eurostat stops covering early (UK after 2018, Iceland after 2020) keeps its
Eurostat series here and is not topped up with OECD years; only the
latest-year snapshot (build_snapshot.py) may show an OECD value for it.

Run after load_eurostat.py and load_oecd.py:
    uv run python src/build_headline.py
"""

import pandas as pd

from layers import save_layer
from sources import PROCESSED_DIR


def main():
    eurostat = pd.read_csv(PROCESSED_DIR / "eurostat_ratio.csv", keep_default_na=False)
    oecd = pd.read_csv(PROCESSED_DIR / "oecd_ratio.csv", keep_default_na=False)

    eurostat_countries = set(eurostat["country"])
    extension = oecd[~oecd["country"].isin(eurostat_countries)]

    headline = pd.concat([eurostat, extension], ignore_index=True)
    save_layer(headline, "median_mean_ratio")

    print(f"Eurostat countries: {len(eurostat_countries)}")
    print(f"OECD extension countries: {sorted(extension['country'].unique())}")


if __name__ == "__main__":
    main()
