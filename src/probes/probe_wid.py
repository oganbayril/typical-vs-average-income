"""Probe the World Inequality Database (WID): top 10% income share.

WID offers no small per-country download, only one ~900 MB zip of all
countries. A zip keeps its file index at the end, so with HTTP range
requests Python's zipfile can read the index and then fetch only the members
it needs (a few MB per country) instead of the whole archive.

What is printed, per country in scope:
- sptincj992 p90p100: top 10% share of pretax national income, adults 20+,
  equal-split between partners, for the last few years, with WID's data
  quality grade per year in brackets (0 = no country data, imputed from the
  region; higher = better)
- avg_quality from the metadata file

WID uses ISO alpha-2 (GR, GB) and has two Kosovo codes (KS holds the data,
XK is empty).

Run from the project root:
    uv run python src/probes/probe_wid.py            # all countries in scope
    uv run python src/probes/probe_wid.py TR DE US   # chosen countries
"""

import io
import sys
import urllib.request
import zipfile

import pandas as pd

from probe_common import PROBE_DIR

WID_ZIP_URL = "https://wid.world/bulk_download/wid_all_data.zip"
VARIABLE = "sptincj992"
PERCENTILE = "p90p100"

# Europe + OECD scope in WID's own codes.
WID_SCOPE = [
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "GR", "ES", "FI", "FR", "HR", "HU",
    "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK",
    "CH", "IS", "LI", "NO", "GB", "AL", "BA", "ME", "MK", "RS", "TR", "KS",
    "AU", "CA", "CL", "CO", "CR", "IL", "JP", "KR", "MX", "NZ", "US",
]


class RemoteFile(io.RawIOBase):
    """A read-only, seekable file whose bytes are fetched by HTTP range."""

    def __init__(self, url):
        self.url = url
        self.position = 0
        head = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"))
        self.size = int(head.headers["Content-Length"])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        if whence == 0:
            self.position = offset
        elif whence == 1:
            self.position += offset
        else:
            self.position = self.size + offset
        return self.position

    def readinto(self, buffer):
        if self.position >= self.size:
            return 0
        end = min(self.position + len(buffer), self.size) - 1
        request = urllib.request.Request(self.url, headers={"Range": f"bytes={self.position}-{end}"})
        data = urllib.request.urlopen(request).read()
        buffer[: len(data)] = data
        self.position += len(data)
        return len(data)


def extract(archive, member):
    """Save one zip member to data/raw/probes/wid/ unless already there."""
    folder = PROBE_DIR / "wid"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / member
    if not path.exists():
        print(f"  extracting {member}")
        path.write_bytes(archive.read(member))
    return path


def main():
    countries = sys.argv[1:] or WID_SCOPE
    archive = zipfile.ZipFile(io.BufferedReader(RemoteFile(WID_ZIP_URL), buffer_size=1 << 20))

    rows = []
    for country in countries:
        data = pd.read_csv(extract(archive, f"WID_data_{country}.csv"), sep=";", dtype={"data_quality": str})
        meta = pd.read_csv(extract(archive, f"WID_metadata_{country}.csv"), sep=";", dtype=str)

        series = data[(data["variable"] == VARIABLE) & (data["percentile"] == PERCENTILE)].sort_values("year")
        avg_quality = meta.loc[meta["variable"] == VARIABLE, "avg_quality"]
        recent = series[series["year"] >= 2019]
        print(f"{country} avg_quality={avg_quality.iloc[0] if len(avg_quality) else '?'}: "
              + " ".join(f"{y}:{v:.3f}[{q}]" for y, v, q in zip(recent["year"], recent["value"], recent["data_quality"].fillna(""))))
        if len(series):
            rows.append({"country": country, "first_year": series["year"].min(), "last_year": series["year"].max(),
                         "avg_quality": avg_quality.iloc[0] if len(avg_quality) else None})

    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
