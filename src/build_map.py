"""Build the map page: the median/mean income ratio by country, in tiers.

Output:
- site/index.html               standalone page (Plotly included; the map outlines
                                are loaded from Plotly's CDN, so it needs internet)
- site/snapshot_median_mean_ratio.csv, site/layer_median_mean_ratio.csv
                                the data behind the map, as downloads
- site/favicon.svg              small icon (avoids a favicon.ico 404)
- site/og-image.png             link-preview image (Open Graph), Europe, latest view
- images/map_latest.png         static image, world view, light theme (README)
- images/map_latest_europe.png  static image, Europe view, light theme (README)

Built on food-housing-spending-share's map (same page, controls, themes,
zoom/pan limits, CSP and exports). What is different here:

- Views of the data: "Latest" (the default) shows the snapshot, each country's
  most recent value (data/processed/snapshot_median_mean_ratio.csv). The year
  slider shows the yearly series by INCOME year (layer_median_mean_ratio.csv),
  2002 onward. Each country's series comes from one source only; the UK's
  OECD value appears only in "Latest" (see build_snapshot.py).
- Tiers come from decisions.TIER_BOUNDARIES (one more tier than boundaries).
  They are ordered, so one hue in light-to-dark steps; the tier furthest
  from the average (lowest ratio) is the most prominent in both themes. Both
  4-step ramps passed the dataviz palette validator (--ordinal, light and dark).
- OECD values are HATCHED. Plotly choropleths cannot draw patterns (their
  marker has only line and opacity), so OECD countries get their own traces
  and the page script fills those paths with an SVG pattern after every
  redraw. Static PNGs (and Plotly's own PNG button) therefore show OECD
  values unhatched.
- OECD values within decisions.SOURCE_UNCERTAINTY of a tier boundary get an
  open-circle marker and a hover note: their tier may differ under Eurostat's
  method. "Latest" uses the snapshot's tier_uncertain column; the yearly views
  apply the same rule to each year.
- Grey = in scope but no data, with the reason in the hover.
- Kosovo: the base map has no Kosovo shape and draws its territory as part of
  Serbia, so Kosovo rows never reach the map and Serbia's hover says so.

Trace layout (frames update the data traces only, never colours or layout):
  [tier traces, Eurostat] [tier traces, OECD] [no data] [uncertain markers]
  [permanent legend entries: tiers, no data, uncertain marker]

Run from the project root, after src/build_snapshot.py:
    uv run python src/build_map.py
"""

import base64
import hashlib
import html
import json
import re
import shutil
import textwrap

import pandas as pd
import plotly.graph_objects as go

from build_snapshot import source_offset
from country_codes import EUROSTAT_TO_ISO3, ISO3_NAMES, OECD_MEMBERS_ISO3
from decisions import (
    EUROSTAT_DISCONTINUED,
    MAP_FIRST_INCOME_YEAR,
    SOURCE_EUROSTAT,
    SOURCE_OECD,
    SOURCE_UNCERTAINTY,
    TIER_BOUNDARIES,
)
from sources import PROCESSED_DIR, PROJECT_ROOT
from year_changes import change_summary

SITE_DIR = PROJECT_ROOT / "site"
IMAGES_DIR = PROJECT_ROOT / "images"

# Where the page will live and where its code lives. Link previews (Open
# Graph) need ABSOLUTE https URLs. The site is not deployed yet: SITE_URL is
# the planned DuckDNS address (same pattern as food-housing-spending-share).
SITE_URL = "https://typical-vs-average-income.duckdns.org/"
REPO_URL = "https://github.com/oganbayril/typical-vs-average-income"
HEADLINE = "How far is the typical person from the average?"
SHARE_DESCRIPTION = (
    "Median income as a share of mean income in European and OECD countries: "
    "how much the typical person has compared with the average, on an interactive map."
)
OG_IMAGE = "og-image.png"
OG_SIZE = (1200, 630)
OG_SCALE = 2
OG_HEADER_PX = 160
OG_LON_RANGE = [-46, 66]
OG_LAT_RANGE = [33, 72]
OG_IMAGE_ALT = (
    "Map of Europe shaded in four blue tiers by median income as a share of mean income, "
    "latest year per country."
)

# Countries in the data that the base map cannot draw.
NOT_MAPPABLE = {"XKX"}
SCOPE = (set(EUROSTAT_TO_ISO3.values()) | OECD_MEMBERS_ISO3) - NOT_MAPPABLE

LATEST = "Latest"  # name of the default frame (the snapshot)

# Latest view: values more than this many years older than the most common
# income year get a dashed outline and an "older data" line in the hover.
OLDER_AFTER_YEARS = 1

# Natural Earth resolution of the base map (50 = 1:50m, 110 = 1:110m). 110 was
# tried on 2026-10-21: see DATA_NOTES.md M1.
RESOLUTION = 50

# --- tiers -----------------------------------------------------------------------

N_TIERS = len(TIER_BOUNDARIES) + 1
PERCENTS = [round(boundary * 100) for boundary in TIER_BOUNDARIES]


def tier_names():
    """Legend names, lowest ratio first, built from TIER_BOUNDARIES."""
    names = [f"Below {PERCENTS[0]}% of the average"]
    for low, high in zip(PERCENTS[:-1], PERCENTS[1:]):
        names.append(f"{low}% to {high}%")
    names.append(f"{PERCENTS[-1]}% or more")
    return names


TIER_NAMES = tier_names()
TIER_SHORT = [f"<{PERCENTS[0]}%"] + [f"{a}-{b}%" for a, b in zip(PERCENTS[:-1], PERCENTS[1:])] + [f"{PERCENTS[-1]}%+"]
NO_DATA = "No data"
UNCERTAIN_NAME = "OECD value near a tier line: tier may differ"
UNCERTAIN_SHORT = "Tier may differ"
LEGEND_TITLE = "<b>The typical person's income</b><br>as a % of the average (median ÷ mean)"

# Trace positions (see the module docstring).
SOLID = list(range(0, N_TIERS))
HATCHED = list(range(N_TIERS, 2 * N_TIERS))
NO_DATA_TRACE = 2 * N_TIERS
MARKER_TRACE = NO_DATA_TRACE + 1
DATA_TRACES = SOLID + HATCHED + [NO_DATA_TRACE, MARKER_TRACE]
LEGEND_TRACES = list(range(MARKER_TRACE + 1, MARKER_TRACE + 1 + N_TIERS + 2))
COLORBAR_TRACE = LEGEND_TRACES[-1] + 1

LEGEND_LAYOUTS = {
    "side": {   # map 1000 px or wider
        "names": TIER_NAMES + [NO_DATA, UNCERTAIN_NAME],
        "layout": {"legend.orientation": "v", "legend.x": 0.01, "legend.y": 0.06,
                   "legend.xanchor": "left", "legend.yanchor": "bottom",
                   "legend.title.text": LEGEND_TITLE, "legend.title.side": "top",
                   "legend.entrywidthmode": "pixels", "legend.entrywidth": 0},
        "colorbar": {"marker.colorbar.title.text": "The typical person's income, % of the average",
                     "marker.colorbar.len": 0.45},
    },
    "top": {    # 600-999 px
        "names": TIER_NAMES + [NO_DATA, UNCERTAIN_NAME],
        "layout": {"legend.orientation": "h", "legend.x": 0, "legend.y": 1,
                   "legend.xanchor": "left", "legend.yanchor": "bottom",
                   "legend.title.text": LEGEND_TITLE.replace("<br>", " "), "legend.title.side": "top",
                   "legend.entrywidthmode": "fraction", "legend.entrywidth": 0.33},
        "colorbar": {"marker.colorbar.title.text": "The typical person's income, % of the average",
                     "marker.colorbar.len": 0.45},
    },
    "compact": {  # under 600 px
        "names": TIER_SHORT + [NO_DATA, UNCERTAIN_SHORT],
        "layout": {"legend.orientation": "h", "legend.x": 0, "legend.y": 1,
                   "legend.xanchor": "left", "legend.yanchor": "bottom",
                   "legend.title.text": "<b>Typical income</b> as a % of the average",
                   "legend.title.side": "top",
                   "legend.entrywidthmode": "fraction", "legend.entrywidth": 0.33},
        "colorbar": {"marker.colorbar.title.text": "% of the average income",
                     "marker.colorbar.len": 0.7},
    },
}

# Colours per theme, in tier order (lowest ratio first). Light: dark -> light,
# so the tier furthest from the average is darkest. Dark: the same hue, light
# -> dark against the dark surface, so that tier is the brightest. Ordinal
# ramps validated with the dataviz validator (scripts/validate_palette.js
# --ordinal; light end 2.06:1 / 2.15:1 against the surface).
THEMES = {
    "light": {
        "tiers": ["#0d366b", "#1c5cab", "#3987e5", "#86b6ef"],
        "no_data": "#c3c2b7",
        "surface": "#fcfcfb",
        "land": "#f0efec",
        "text": "#0b0b0b",
        "text_2": "#52514e",
        "control_bg": "#ffffff",
        "border": "#c3c2b7",
        "legend_bg": "rgba(252,252,251,0.85)",
        "accent": "#2a78d6",
    },
    "dark": {
        "tiers": ["#9ec5f4", "#5598e7", "#2a78d6", "#184f95"],
        "no_data": "#898781",
        "surface": "#1a1a19",
        "land": "#2c2c2a",
        "text": "#ffffff",
        "text_2": "#c3c2b7",
        "control_bg": "#262624",
        "border": "#383835",
        "legend_bg": "rgba(26,26,25,0.85)",
        "accent": "#3987e5",
    },
}
LIGHT = THEMES["light"]
for _theme in THEMES.values():
    if len(_theme["tiers"]) != N_TIERS:
        raise ValueError(f"{N_TIERS} tiers need {N_TIERS} colours per theme (TIER_BOUNDARIES changed?)")

# Hatching for OECD values: lines in the surface colour at 45 degrees over the
# tier colour, so it reads in every tier and both themes.
HATCH_SPACING = 5
HATCH_WIDTH = 1.6

MAP_HEIGHT_CSS = "clamp(360px, 75vw, 620px)"

# Views, zoom/pan limits and pan margins: unchanged from food-housing-spending-share
# (measured there in Edge and Firefox).
GEO_LON_RANGE = [-180, 180]
GEO_LAT_RANGE = [-58, 85]
VIEWS = {
    "world": {"scale": 1, "lon": 0, "lat": 10.793053},
    "europe": {"scale": 3.5, "lon": 8, "lat": 52},
}
PAN_MARGINS = {"x_fraction": 0.12, "x_cap_lon": 20, "y_fraction": 0.08, "y_cap_lat": 2}

PLOTLY_CONFIG = {
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "modeBarButtonsToRemove": [
        "sendChartToCloud", "select2d", "lasso2d", "pan2d",
        "zoomInGeo", "zoomOutGeo", "hoverClosestGeo",
    ],
}

CSP_TEMPLATE = (
    "default-src 'none'; "
    "script-src {script_hashes}; "
    "style-src 'unsafe-inline'; "
    "img-src 'self' blob:; "
    "connect-src https://cdn.plot.ly; "
    "base-uri 'none'; "
    "form-action 'none'"
)

FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
    '<rect width="16" height="16" rx="3" fill="#1c5cab"/>'
    '<rect x="3" y="9" width="3" height="4" fill="#cde2fb"/>'
    '<rect x="7" y="6" width="3" height="7" fill="#cde2fb"/>'
    '<rect x="11" y="3" width="2" height="10" fill="#cde2fb"/>'
    "</svg>\n"
)

# Why a country in scope has no value at all (any year), for the grey hover.
NEVER_COVERED = {
    "BIH": "No household income survey data from Eurostat or the OECD.",
    "LIE": "No household income survey data from Eurostat or the OECD.",
    "COL": "OECD member, but not covered by the OECD Income Distribution Database.",
}


# --- data -> table ---------------------------------------------------------------

def tier_index(value):
    """0 for the lowest tier ... N_TIERS - 1 for the highest (value >= boundary goes up)."""
    index = 0
    for boundary in TIER_BOUNDARIES:
        if value >= boundary:
            index += 1
    return index


def near_boundary(value):
    """Within SOURCE_UNCERTAINTY of any tier boundary (same rule as build_snapshot.py)."""
    return any(abs(value - boundary) <= SOURCE_UNCERTAINTY for boundary in TIER_BOUNDARIES)


def wrap(text, width=62):
    """Plotly hover labels do not wrap: break long notes into lines."""
    return "<br>".join(textwrap.wrap(text, width))


def value_hover(row, name, uncertain, older):
    """Hover text for a country with a value, as HTML lines."""
    percent = round(row["value"] * 100)
    lines = [f"<b>{name}</b>, income year {int(row['income_year'])}"]
    if older:
        lines.append(f"Older data: income year {int(row['income_year'])}")
    lines += [
        f"The typical person has {percent}% of the average income",
        f"Tier: {TIER_NAMES[tier_index(row['value'])]}",
        f"Median ÷ mean income: {row['value']:.3f}",
    ]
    if row["source"] == SOURCE_OECD:
        lines.append("Source: OECD Income Distribution Database (hatched)")
    else:
        lines.append(f"Source: Eurostat, EU-SILC {int(row['year'])}")
    if row["flag"]:
        lines.append(f"Flag: {row['flag']}")
    note = row.get("note", "")
    if uncertain and "Tier may differ" not in note:
        note = f"{note} Tier may differ under Eurostat's method.".strip()
    if note:
        lines.append(wrap(note))
    return "<br>".join(lines)


def no_data_hover(iso3, frame, series_by_country):
    """Hover text for a grey country, saying why there is no value."""
    name = ISO3_NAMES[iso3]
    title = f"<b>{name}</b>" if frame == LATEST else f"<b>{name}</b>, income year {frame}"
    if iso3 in NEVER_COVERED:
        reason = NEVER_COVERED[iso3]
    else:
        series = series_by_country[iso3]
        first, last = int(series["income_year"].min()), int(series["income_year"].max())
        source = series["source"].iloc[0]
        if frame == LATEST:
            # Only countries whose Eurostat series ended reach this branch.
            reason = (f"Eurostat data ends with income year {last}, and the OECD has nothing newer, "
                      f"so the latest view leaves it grey.")
        elif iso3 in EUROSTAT_DISCONTINUED and int(frame) > last:
            reason = f"Eurostat stopped covering this country after income year {last}."
        else:
            reason = f"No {source} value for this year (data for income years {first}-{last}, with gaps)."
    return "<br>".join([title, "No data", wrap(reason)])


def serbia_note(hover, kosovo):
    """Serbia's shape on the base map includes Kosovo: say so in its hover."""
    line = "Map: this shape includes Kosovo, which cannot be shown separately"
    if kosovo is not None:
        line += f" (Kosovo's own value, income year {int(kosovo['income_year'])}: {kosovo['value']:.3f})"
    return hover + "<br>" + wrap(line + ".")


def frame_rows(rows, frame, series_by_country, kosovo, older_before=None):
    """One entry per country in scope for one frame: trace position, value,
    hover, circle marker, older-data outline.

    `older_before`: in the latest view, income years below this are "older".
    """
    entries = []
    present = set()
    for _, row in rows.iterrows():
        iso3 = row["country"]
        if iso3 in NOT_MAPPABLE:
            continue
        present.add(iso3)
        if frame == LATEST:
            uncertain = bool(row["tier_uncertain"])
        else:
            uncertain = row["source"] == SOURCE_OECD and near_boundary(row["value"])
        older = older_before is not None and row["income_year"] < older_before
        hover = value_hover(row, ISO3_NAMES[iso3], uncertain, older)
        if iso3 == "SRB":
            hover = serbia_note(hover, kosovo)
        offset = 0 if row["source"] == SOURCE_EUROSTAT else N_TIERS
        entries.append({"iso3": iso3, "trace": offset + tier_index(row["value"]), "value": row["value"],
                        "hover": hover, "uncertain": uncertain, "older": older})
    for iso3 in sorted(SCOPE - present):
        hover = no_data_hover(iso3, frame, series_by_country)
        if iso3 == "SRB":
            hover = serbia_note(hover, kosovo)
        entries.append({"iso3": iso3, "trace": NO_DATA_TRACE, "value": 0.0, "hover": hover,
                        "uncertain": False, "older": False})
    return pd.DataFrame(entries)


def latest_years(snapshot):
    """Most common income year in the latest view, and where "older" starts."""
    common = int(snapshot["income_year"].mode().iloc[0])
    return common, common - OLDER_AFTER_YEARS


def map_years(layer):
    """Income years for the slider: from MAP_FIRST_INCOME_YEAR to the last year
    with at least half as many countries as the best-covered year (2025 has
    only Costa Rica, so it is shown in Latest only)."""
    counts = layer.groupby("income_year")["country"].nunique()
    enough = counts[counts >= counts.max() / 2]
    last = int(enough.index.max())
    return list(range(MAP_FIRST_INCOME_YEAR, last + 1))


def load_tables():
    """Per frame (each slider year, then Latest), one row per mappable country."""
    layer = pd.read_csv(PROCESSED_DIR / "layer_median_mean_ratio.csv", keep_default_na=False)
    snapshot = pd.read_csv(PROCESSED_DIR / "snapshot_median_mean_ratio.csv", keep_default_na=False)
    snapshot["tier_uncertain"] = snapshot["tier_uncertain"].astype(str) == "True"
    layer["note"] = ""

    check_one_source_per_series(layer)
    series_by_country = {iso3: rows for iso3, rows in layer.groupby("country")}
    kosovo_rows = layer[layer["country"] == "XKX"].sort_values("income_year")
    latest_kosovo = kosovo_rows.iloc[-1] if len(kosovo_rows) else None

    years = map_years(layer)
    tables = {}
    for year in years:
        rows = layer[layer["income_year"] == year]
        kosovo_year = kosovo_rows[kosovo_rows["income_year"] == year]
        tables[str(year)] = frame_rows(rows, str(year), series_by_country,
                                       kosovo_year.iloc[0] if len(kosovo_year) else None)
    _, older_before = latest_years(snapshot)
    tables[LATEST] = frame_rows(snapshot, LATEST, series_by_country, latest_kosovo, older_before)
    check_latest_uncertain(snapshot)
    return tables, years, snapshot, layer


def check_one_source_per_series(layer):
    """Stop if any country's yearly series mixes Eurostat and OECD."""
    sources = layer.groupby("country")["source"].nunique()
    mixed = sources[sources > 1]
    if len(mixed) > 0:
        raise ValueError(f"Series mixing sources: {list(mixed.index)}")
    print(f"Source check: all {len(sources)} yearly series use one source each.")


def check_latest_uncertain(snapshot):
    """The snapshot's tier_uncertain column must match the rule the yearly views use."""
    rule = (snapshot["source"] == SOURCE_OECD) & snapshot["value"].apply(near_boundary)
    if not (rule == snapshot["tier_uncertain"]).all():
        raise ValueError("snapshot tier_uncertain does not match the map's rule")


# --- figure --------------------------------------------------------------------

def frame_traces(table):
    """All data traces for one frame, in fixed positions (empty ones included,
    so traces always line up between frames)."""
    traces = []
    for position in SOLID + HATCHED + [NO_DATA_TRACE]:
        rows = table[table["trace"] == position]
        # z is the ratio itself: in the tier view each trace's colour scale is
        # one flat colour, so z does not matter; the continuous view swaps in
        # the ramp and z picks the colour. (No data: 0, always grey.)
        traces.append(go.Choropleth(
            name=trace_name(position),
            locations=list(rows["iso3"]),
            z=list(rows["value"]),
            customdata=[[text] for text in rows["hover"]],
        ))
    marked = table[table["uncertain"]]
    traces.append(go.Scattergeo(
        name="tier uncertain",
        locations=list(marked["iso3"]),
        customdata=[[text] for text in marked["hover"]],
    ))
    return traces


def trace_name(position):
    if position in SOLID:
        return f"{TIER_NAMES[position]} (Eurostat)"
    if position in HATCHED:
        return f"{TIER_NAMES[position - N_TIERS]} (OECD)"
    return NO_DATA


def trace_colors(theme):
    """Fill colour for each choropleth data trace position."""
    return theme["tiers"] + theme["tiers"] + [theme["no_data"]]


def legend_entry(name, color, symbol="square", size=13, line_color=None, line_width=0):
    """A permanent legend entry: an empty Scattergeo (no points, always listed)."""
    return go.Scattergeo(
        name=name, lon=[None], lat=[None], mode="markers",
        marker=dict(symbol=symbol, size=size, color=color,
                    line=dict(width=line_width, color=line_color or color)),
        hoverinfo="skip", showlegend=True,
    )


def animation_args(duration):
    return dict(mode="immediate", fromcurrent=True,
                frame=dict(duration=duration, redraw=True), transition=dict(duration=0))


def value_range(tables):
    """Lowest and highest ratio over every frame: the continuous scale's ends,
    so a colour means the same value in every year."""
    values = pd.concat([table.loc[table["trace"] != NO_DATA_TRACE, "value"] for table in tables.values()])
    return float(values.min()), float(values.max())


def continuous_scale(theme):
    """The tier ramp as one smooth scale, lowest ratio first (same order as the tiers)."""
    colors = theme["tiers"]
    return [[index / (len(colors) - 1), color] for index, color in enumerate(colors)]


def colorbar_entry(zmin, zmax):
    """The continuous view's colour bar: an empty Scattergeo whose marker
    carries the scale (a choropleth's own bar would vanish in years where
    that trace has no countries). Hidden in the tier view."""
    ticks = [round(zmin, 2)] + [b for b in TIER_BOUNDARIES if zmin < b < zmax] + [round(zmax, 2)]
    return go.Scattergeo(
        name="scale", lon=[None], lat=[None], mode="markers", showlegend=False, hoverinfo="skip",
        visible=False,
        marker=dict(
            color=[zmin], cmin=zmin, cmax=zmax, colorscale=continuous_scale(LIGHT), showscale=True,
            colorbar=dict(
                orientation="h", x=0.5, xanchor="center", y=0.02, yanchor="bottom", len=0.45,
                thickness=12, title=dict(text="The typical person's income, % of the average", side="top"),
                tickvals=ticks, ticktext=[f"{round(t * 100)}%" for t in ticks],
                outlinewidth=0, bgcolor=LIGHT["legend_bg"],
            ),
        ),
    )


def build_figure(tables, years):
    frame_names = [str(year) for year in years] + [LATEST]
    zmin, zmax = value_range(tables)

    data = []
    for trace, color in zip(frame_traces(tables[LATEST]), trace_colors(LIGHT) + [None]):
        if isinstance(trace, go.Choropleth):
            trace.update(
                colorscale=[[0, color], [1, color]], zmin=zmin, zmax=zmax,
                showscale=False, showlegend=False,
                hovertemplate="%{customdata[0]}<extra></extra>",
                marker_line_color=LIGHT["surface"], marker_line_width=0.6,
            )
        else:
            trace.update(
                locationmode="ISO-3", mode="markers", showlegend=False,
                marker=dict(symbol="circle-open", size=11, color=LIGHT["text"], line=dict(width=2)),
                hovertemplate="%{customdata[0]}<extra></extra>",
            )
        data.append(trace)
    for name, color in zip(TIER_NAMES + [NO_DATA], LIGHT["tiers"] + [LIGHT["no_data"]]):
        data.append(legend_entry(name, color))
    data.append(legend_entry(UNCERTAIN_NAME, LIGHT["text"], symbol="circle-open", size=11, line_width=2))
    data.append(colorbar_entry(zmin, zmax))

    frames = []
    for name in frame_names:
        frames.append(go.Frame(name=name, data=frame_traces(tables[name]), traces=DATA_TRACES))

    fig = go.Figure(data=data, frames=frames)
    world = VIEWS["world"]
    fig.update_geos(
        resolution=RESOLUTION,
        projection_type="natural earth",
        projection_scale=world["scale"],
        projection_rotation_lon=0,
        projection_minscale=1,
        center=dict(lon=world["lon"], lat=world["lat"]),
        lonaxis_range=GEO_LON_RANGE,
        lataxis_range=GEO_LAT_RANGE,
        showcountries=True, countrycolor=LIGHT["surface"],
        showland=True, landcolor=LIGHT["land"],
        showcoastlines=False, showocean=False, showlakes=False, showframe=False,
        bgcolor=LIGHT["surface"],
    )

    steps = []
    for name in frame_names:
        steps.append(dict(label=name, method="animate", args=[[name], animation_args(0)]))
    fig.update_layout(
        paper_bgcolor=LIGHT["surface"],
        plot_bgcolor=LIGHT["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', color=LIGHT["text"]),
        margin=dict(l=10, r=10, t=10, b=10),
        dragmode="pan",
        legend=dict(
            title=dict(text=LEGEND_TITLE),
            orientation="v", x=0.01, y=0.06, xanchor="left", yanchor="bottom",
            bgcolor=LIGHT["legend_bg"], itemclick=False, itemdoubleclick=False,
        ),
        hoverlabel=dict(bgcolor=LIGHT["control_bg"], font_size=13, align="left"),
        sliders=[dict(
            active=frame_names.index(LATEST),
            currentvalue=dict(prefix="Income year: "),
            pad=dict(t=40, b=10),
            x=0, len=1, xanchor="left", y=0, yanchor="top",
            steps=steps,
        )],
    )
    return fig, frame_names


def check_frames(fig, frame_names, tables):
    """Stop the build if a frame could put a colour on the wrong tier, drop a
    legend entry, change the view, or draw a country twice."""
    if [frame.name for frame in fig.frames] != frame_names:
        raise ValueError("Frames do not match the slider")
    expected = [trace.name for trace in fig.data[:len(DATA_TRACES)]]
    for frame in fig.frames:
        if list(frame.traces) != DATA_TRACES:
            raise ValueError(f"Frame {frame.name} targets traces {frame.traces}")
        if [trace.name for trace in frame.data] != expected:
            raise ValueError(f"Frame {frame.name}: traces out of order")
        for trace in frame.data:
            if getattr(trace, "colorscale", None) is not None:
                raise ValueError(f"Frame {frame.name}: trace carries its own colours")
        if frame.layout and frame.layout.to_plotly_json():
            raise ValueError(f"Frame {frame.name} carries layout, which would override the view")
        drawn = []
        for trace in frame.data[:-1]:
            drawn += list(trace.locations)
        if len(drawn) != len(set(drawn)) or set(drawn) != SCOPE:
            raise ValueError(f"Frame {frame.name}: countries missing or drawn twice")
    for index in LEGEND_TRACES:
        trace = fig.data[index]
        if trace.type != "scattergeo" or not trace.showlegend:
            raise ValueError(f"Legend entry {trace.name} is not a permanent legend trace")
    if len(fig.data) != COLORBAR_TRACE + 1 or fig.data[COLORBAR_TRACE].name != "scale":
        raise ValueError("The colour bar trace is not where the page script expects it")
    print(f"Frame check: {len(fig.frames)} frames, {len(DATA_TRACES)} data traces in order, every "
          f"country in scope drawn exactly once per frame, no colours or layout in frames.")


def check_kosovo_isolated(fig):
    """Kosovo must never reach the map, and Serbia must appear once per frame."""
    for frame in fig.frames:
        serbia = 0
        for trace in frame.data:
            for location in trace.locations:
                if location in NOT_MAPPABLE:
                    raise ValueError(f"{frame.name}: {location} is on the map")
            serbia += list(trace.locations).count("SRB") if trace.type == "choropleth" else 0
        if serbia != 1:
            raise ValueError(f"{frame.name}: Serbia appears {serbia} times")
    print(f"Kosovo check: XKX in none of {len(fig.frames)} frames; Serbia drawn once per frame.")


# --- page ----------------------------------------------------------------------

def theme_payload():
    """What the page script needs to recolour the map for a theme."""
    payload = {}
    for mode, theme in THEMES.items():
        scales = [[[0, color], [1, color]] for color in trace_colors(theme)]
        payload[mode] = {
            "scales": scales,
            "continuous": continuous_scale(theme),
            "legendColors": theme["tiers"] + [theme["no_data"], theme["text"]],
            "border": theme["surface"],
            "marker": theme["text"],
            "hatchLine": theme["surface"],
            "olderLine": theme["text_2"],
            "colorbar": {
                "marker.colorscale": [continuous_scale(theme)],
                "marker.colorbar.bgcolor": theme["legend_bg"],
                "marker.colorbar.tickfont.color": theme["text"],
                "marker.colorbar.title.font.color": theme["text"],
            },
            "layout": {
                "paper_bgcolor": theme["surface"],
                "plot_bgcolor": theme["surface"],
                "font.color": theme["text"],
                "geo.bgcolor": theme["surface"],
                "geo.landcolor": theme["land"],
                "geo.countrycolor": theme["surface"],
                "legend.bgcolor": theme["legend_bg"],
                "legend.font.color": theme["text"],
                "hoverlabel.bgcolor": theme["control_bg"],
                "hoverlabel.font.color": theme["text"],
                "hoverlabel.bordercolor": theme["border"],
                "sliders[0].bgcolor": theme["control_bg"],
                "sliders[0].bordercolor": theme["border"],
                "sliders[0].font.color": theme["text"],
                "sliders[0].currentvalue.font.color": theme["text"],
            },
        }
    return payload


def hatch_pattern(pattern_id, fill, line):
    """One hatch pattern: lines at 45 degrees over a fill colour."""
    return (
        f'<pattern id="{pattern_id}" patternUnits="userSpaceOnUse" width="{HATCH_SPACING}" '
        f'height="{HATCH_SPACING}" patternTransform="rotate(45)">'
        f'<rect width="{HATCH_SPACING}" height="{HATCH_SPACING}" fill="{fill}"/>'
        f'<line x1="0" y1="0" x2="0" y2="{HATCH_SPACING}" stroke="{line}" '
        f'stroke-width="{HATCH_WIDTH}"/></pattern>'
    )


def hatch_defs():
    """An invisible SVG holding the hatch patterns. The page script adds one
    pattern per OECD country, filled with the colour Plotly gave that country
    (tier or continuous), so the hatch works in both colour views. The key
    swatch has its own fixed pattern."""
    key = hatch_pattern("hatch-key", LIGHT["tiers"][2], LIGHT["surface"])
    return ('<svg class="hatch-defs" width="0" height="0" aria-hidden="true" focusable="false">'
            f'<defs id="hatch-defs">{key}</defs></svg>')


def key_swatches():
    """Small inline SVGs for the key above the map (hatch, marker, older
    outline), using the page's CSS colours so they follow the theme."""
    hatch = ('<svg width="22" height="14" aria-hidden="true"><rect width="22" height="14" '
             'fill="url(#hatch-key)"/></svg>')
    older = ('<svg width="22" height="14" aria-hidden="true"><rect x="1" y="1" width="20" height="12" '
             'fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3 2"/></svg>')
    marker = ('<svg width="16" height="16" aria-hidden="true"><circle cx="8" cy="8" r="5" '
              'fill="none" stroke="currentColor" stroke-width="2"/></svg>')
    return hatch, marker, older


EARLY_THEME_SCRIPT = """(function () {
  var choice = "system";
  try { choice = localStorage.getItem("tva-theme") || "system"; } catch (e) {}
  var dark = choice === "dark" ||
    (choice === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  document.documentElement.setAttribute("data-theme-choice", choice);
})();"""


PAGE_SCRIPT = """(function () {
  var map = document.getElementById("map");
  var note = document.getElementById("year-note");
  var themes = __THEMES__;
  var views = __VIEWS__;
  var frameNotes = __FRAME_NOTES__;
  var T = __TRACES__;
  var GEO_LON = __GEO_LON__, GEO_LAT = __GEO_LAT__;
  var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
  var STORAGE_KEY = "tva-theme";

  var LATEST = __LATEST__;
  var OLDER = __OLDER__;          // latest view: countries with older data (dashed outline)
  var currentTheme = themes.light;
  var colorMode = "tiers";
  var current = LATEST;           // the frame on screen

  // ---- decorations: hatching (OECD) and older-data outlines -----------------
  // Plotly choropleths have no pattern fill or dashed outline, so the page
  // adds them to the country paths. Plotly resets fills and outlines when it
  // redraws (year, theme, colour view), never on hover or zoom/pan (those
  // only move the outlines), so decorating follows redraws only. Several
  // redraws in one screen frame (e.g. a theme change restyles four times)
  // are coalesced into one run on the next frame.
  var decoratePending = false;
  window.decorateRuns = 0;        // read by the browser check
  function scheduleDecorate() {
    if (decoratePending) { return; }
    decoratePending = true;
    window.requestAnimationFrame(function () { decoratePending = false; decorate(); });
  }
  // One pattern per OECD country, filled with the colour Plotly gave it
  // (tier colour or continuous colour), hatched in the surface colour.
  function patternFor(loc, fill) {
    var id = "hatch-" + loc;
    var pattern = document.getElementById(id);
    if (!pattern) {
      pattern = document.getElementById("hatch-key").cloneNode(true);
      pattern.id = id;
      document.getElementById("hatch-defs").appendChild(pattern);
    }
    pattern.querySelector("rect").setAttribute("fill", fill);
    pattern.querySelector("line").setAttribute("stroke", currentTheme.hatchLine);
    return "url(#" + id + ")";
  }
  function decorate() {
    window.decorateRuns += 1;
    var older = current === LATEST ? OLDER : [];
    map.querySelectorAll(".choroplethlayer g.trace").forEach(function (group) {
      var calc = group.__data__;
      if (!calc || !calc[0] || !calc[0].trace) { return; }
      var hatched = T.hatched.indexOf(calc[0].trace.index) >= 0;
      group.querySelectorAll("path").forEach(function (path) {
        var loc = path.__data__ && path.__data__.loc;
        if (hatched) {
          // Plotly writes each country's colour into the fill ATTRIBUTE on
          // every redraw (tier or continuous colour); the pattern takes that
          // colour, and the inline style (which wins over the attribute)
          // points the path at the pattern.
          var fill = path.getAttribute("fill");
          if (fill) { path.style.fill = patternFor(loc, fill); }
        }
        // Plotly never sets a dash, so it must be cleared here; colour and
        // width are reset by Plotly's own redraw.
        if (older.indexOf(loc) >= 0) {
          path.style.strokeDasharray = "4 2.5";
          path.style.stroke = currentTheme.olderLine;
          path.style.strokeWidth = "1.6px";
        } else {
          path.style.strokeDasharray = "";
        }
      });
    });
  }

  // ---- colour view: tiers or continuous ------------------------------------
  // Both read the same z values (the ratio): in Tiers each trace's scale is
  // one flat colour; in Continuous the tier traces share one smooth scale.
  var COLOR_KEY = "tva-colors";
  function storedColorMode() {
    try { return localStorage.getItem(COLOR_KEY) === "continuous" ? "continuous" : "tiers"; } catch (e) { return "tiers"; }
  }
  function applyColors() {
    var theme = currentTheme, continuous = colorMode === "continuous";
    var scales = T.choropleths.map(function (index, position) {
      return continuous && index !== T.noData ? theme.continuous : theme.scales[position];
    });
    Plotly.restyle(map, { colorscale: scales, "marker.line.color": theme.border }, T.choropleths);
    var bar = {};
    Object.keys(theme.colorbar).forEach(function (key) { bar[key] = theme.colorbar[key]; });
    bar.visible = continuous;
    Plotly.restyle(map, bar, [T.colorbar]);
    // In Continuous the tier swatches would be misleading: keep only No data
    // and the circle in the legend.
    var show = T.legend.map(function (index, position) { return !continuous || position >= T.tierCount; });
    Plotly.restyle(map, { showlegend: show }, T.legend);
    document.querySelectorAll("[data-color-mode]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.dataset.colorMode === colorMode));
    });
    scheduleDecorate();
  }

  // ---- theme ------------------------------------------------------------
  function storedChoice() {
    try { return localStorage.getItem(STORAGE_KEY) || "system"; } catch (e) { return "system"; }
  }
  function storeChoice(choice) {
    try { localStorage.setItem(STORAGE_KEY, choice); } catch (e) {}
  }
  function modeFor(choice) {
    if (choice === "light" || choice === "dark") { return choice; }
    return darkQuery.matches ? "dark" : "light";
  }
  function applyTheme(choice) {
    var mode = modeFor(choice);
    document.documentElement.setAttribute("data-theme", mode);
    document.documentElement.setAttribute("data-theme-choice", choice);
    document.querySelectorAll("[data-theme-button]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.dataset.themeButton === choice));
    });
    var theme = themes[mode];
    currentTheme = theme;
    // Frames carry no colours, so these changes hold for every year.
    Plotly.restyle(map, { "marker.color": theme.marker }, [T.marker]);
    Plotly.restyle(map, { "marker.color": theme.legendColors, "marker.line.color": theme.legendColors }, T.legend);
    Plotly.relayout(map, theme.layout);
    applyColors();
  }

  // ---- views: presets, zoom and pan -----------------------------------------
  // Unchanged from food-housing-spending-share: Plotly's own drag / wheel
  // handling is blocked, and every change passes through limitView() before
  // it is drawn (never zoomed out beyond World, never rotated, panning limited).
  var WHEEL_RATE = 0.002;
  var LAT_MAX = GEO_LAT[1], LAT_MIN = GEO_LAT[0];
  var EDGE_LON = 179.999;

  function subplot() { return map._fullLayout.geo._subplot; }
  function frameBox(sp) {
    var c = sp.clipRect.node();
    return { x: +c.getAttribute("x"), y: +c.getAttribute("y"),
             w: +c.getAttribute("width"), h: +c.getAttribute("height") };
  }
  var MARGINS = __MARGINS__;
  function marginsFor(sp) {
    var p = sp.projection, box = frameBox(sp);
    var pxPerLon = Math.abs(p([1, 0])[0] - p([0, 0])[0]);
    var pxNorth = Math.abs(p([0, LAT_MAX])[1] - p([0, LAT_MAX + MARGINS.y_cap_lat])[1]);
    var pxSouth = Math.abs(p([0, LAT_MIN - MARGINS.y_cap_lat])[1] - p([0, LAT_MIN])[1]);
    return {
      x: Math.min(MARGINS.x_fraction * box.w, MARGINS.x_cap_lon * pxPerLon),
      y: Math.min(MARGINS.y_fraction * box.h, pxNorth, pxSouth)
    };
  }
  function within(value, low, high) { return Math.min(Math.max(value, low), high); }
  function limitView(sp) {
    var p = sp.projection, box = frameBox(sp);
    if (p.scale() < sp.fitScale) { p.scale(sp.fitScale); }
    var r = p.rotate();
    if (r[0] !== 0 || r[1] !== 0 || r[2] !== 0) { p.rotate([0, 0, 0]); }
    var world = p.scale() <= sp.fitScale * 1.0001;
    var margin = world ? { x: 0, y: 0 } : marginsFor(sp);
    var t = p.translate();
    var yNorth = p([0, LAT_MAX])[1], ySouth = p([0, LAT_MIN])[1];
    var top = box.y, bottom = box.y + box.h, dy;
    if (world || ySouth - yNorth < box.h - 2 * margin.y) {
      dy = (top + bottom) / 2 - (yNorth + ySouth) / 2;
    } else {
      dy = within(0, (bottom - margin.y) - ySouth, (top + margin.y) - yNorth);
    }
    p.translate([t[0], t[1] + dy]);
    t = p.translate();
    var centreX = box.x + box.w / 2;
    var latTop = within(p.invert([centreX, top])[1], LAT_MIN, LAT_MAX);
    var latBottom = within(p.invert([centreX, bottom])[1], LAT_MIN, LAT_MAX);
    var widest = (latTop > 0 && latBottom < 0) ? 0
               : (Math.abs(latTop) < Math.abs(latBottom) ? latTop : latBottom);
    var left = p([-EDGE_LON, widest])[0], right = p([EDGE_LON, widest])[0];
    var dx;
    if (world || right - left < box.w - 2 * margin.x) {
      dx = centreX - (p([-EDGE_LON, 0])[0] + p([EDGE_LON, 0])[0]) / 2;
    } else {
      dx = within(0, (box.x + box.w - margin.x) - right, (box.x + margin.x) - left);
    }
    p.translate([t[0] + dx, t[1]]);
  }
  function syncLayout(emit) {
    var sp = subplot(), p = sp.projection, centre = p.invert(sp.midPt);
    var values = { scale: p.scale() / sp.fitScale, lon: centre[0], lat: centre[1] };
    [map.layout, map._fullLayout].forEach(function (layout) {
      layout.geo = layout.geo || {};
      layout.geo.projection = layout.geo.projection || {};
      layout.geo.projection.scale = values.scale;
      layout.geo.projection.rotation = layout.geo.projection.rotation || {};
      layout.geo.projection.rotation.lon = 0;
      layout.geo.center = layout.geo.center || {};
      layout.geo.center.lon = values.lon;
      layout.geo.center.lat = values.lat;
    });
    if (emit) {
      map.emit("plotly_relayout", { "geo.projection.scale": values.scale, "geo.center.lon": values.lon,
                                    "geo.center.lat": values.lat, "geo.projection.rotation.lon": 0 });
    }
  }
  function atWorld(sp) { return sp.projection.scale() <= sp.fitScale * 1.0001; }
  var mapFrame = document.querySelector(".map-frame");
  function updateTouchMode(sp) { mapFrame.classList.toggle("zoomed", !atWorld(sp)); }
  var renderPending = false;
  function draw(sp) {
    limitView(sp);
    syncLayout(false);
    if (renderPending) { return; }
    renderPending = true;
    window.requestAnimationFrame(function () {
      renderPending = false;
      var current = subplot();
      current.render(true);
      updateTouchMode(current);
    });
  }
  function zoomAt(point, factor) {
    var sp = subplot(), p = sp.projection;
    var k0 = p.scale(), k = Math.max(sp.fitScale, k0 * factor);
    if (Math.abs(k - k0) < 1e-9) { return; }
    var t = p.translate(), ratio = k / k0;
    p.scale(k);
    p.translate([point[0] - (point[0] - t[0]) * ratio, point[1] - (point[1] - t[1]) * ratio]);
    draw(sp);
  }
  function panBy(dx, dy) {
    var sp = subplot(), p = sp.projection, t = p.translate();
    p.translate([t[0] + dx, t[1] + dy]);
    draw(sp);
  }
  function framePoint(sp, clientX, clientY) {
    var rect = sp.framework.node().getBoundingClientRect(), box = frameBox(sp);
    return [clientX - rect.left + box.x, clientY - rect.top + box.y];
  }
  function onMapArea(event) {
    return event.target && event.target.closest && event.target.closest("#map .geo");
  }
  var gestureTimer = null;
  function scheduleGestureEnd() {
    window.clearTimeout(gestureTimer);
    gestureTimer = window.setTimeout(function () { syncLayout(true); }, 250);
  }
  map.addEventListener("wheel", function (event) {
    if (!onMapArea(event)) { return; }
    event.preventDefault();
    event.stopPropagation();
    var sp = subplot();
    var delta = event.deltaY * (event.deltaMode ? 120 : 1);
    if (delta > 0 && atWorld(sp)) { return; }
    zoomAt(framePoint(sp, event.clientX, event.clientY), Math.pow(2, -delta * WHEEL_RATE));
    scheduleGestureEnd();
  }, { capture: true, passive: false });

  var pointers = {};
  var pinchDistance = null;
  function pointerList() { return Object.keys(pointers).map(function (id) { return pointers[id]; }); }
  ["mousedown", "touchstart", "dblclick"].forEach(function (type) {
    map.addEventListener(type, function (event) { if (onMapArea(event)) { event.stopPropagation(); } }, true);
  });
  map.addEventListener("pointerdown", function (event) {
    if (!onMapArea(event)) { return; }
    event.stopPropagation();
    pointers[event.pointerId] = { x: event.clientX, y: event.clientY };
    var list = pointerList();
    if (list.length === 2) {
      pinchDistance = Math.hypot(list[0].x - list[1].x, list[0].y - list[1].y);
    }
    if (!atWorld(subplot()) || list.length === 2) {
      event.preventDefault();
      try { event.target.setPointerCapture(event.pointerId); } catch (e) {}
    }
  }, true);
  window.addEventListener("pointermove", function (event) {
    var previous = pointers[event.pointerId];
    if (!previous) { return; }
    var current = { x: event.clientX, y: event.clientY };
    pointers[event.pointerId] = current;
    var list = pointerList(), sp = subplot();
    if (list.length === 2 && pinchDistance) {
      var distance = Math.hypot(list[0].x - list[1].x, list[0].y - list[1].y);
      var middle = framePoint(sp, (list[0].x + list[1].x) / 2, (list[0].y + list[1].y) / 2);
      zoomAt(middle, distance / pinchDistance);
      pinchDistance = distance;
    } else if (list.length === 1 && !atWorld(sp)) {
      panBy(current.x - previous.x, current.y - previous.y);
    }
  });
  function endPointer(event) {
    if (!pointers[event.pointerId]) { return; }
    delete pointers[event.pointerId];
    if (pointerList().length < 2) { pinchDistance = null; }
    if (pointerList().length === 0) { syncLayout(true); }
  }
  window.addEventListener("pointerup", endPointer);
  window.addEventListener("pointercancel", endPointer);

  // Tap -> tooltip on touch screens (see food-housing-spending-share).
  var TAP_MS = 500, TAP_PX = 10;
  var touchStart = null;
  map.addEventListener("pointerdown", function (event) {
    if (event.pointerType !== "touch" || !onMapArea(event)) { return; }
    touchStart = event.isPrimary ? { x: event.clientX, y: event.clientY, time: event.timeStamp, moved: 0 } : null;
  }, true);
  window.addEventListener("pointermove", function (event) {
    if (!touchStart || !event.isPrimary || event.pointerType !== "touch") { return; }
    touchStart.moved = Math.max(touchStart.moved,
      Math.hypot(event.clientX - touchStart.x, event.clientY - touchStart.y));
  });
  window.addEventListener("pointerup", function (event) {
    var start = touchStart;
    touchStart = null;
    if (!start || !event.isPrimary || event.pointerType !== "touch") { return; }
    if (event.timeStamp - start.time > TAP_MS || start.moved > TAP_PX) { return; }
    var x = event.clientX, y = event.clientY;
    window.requestAnimationFrame(function () {
      var target = document.elementFromPoint(x, y);
      if (!target) { return; }
      target.dispatchEvent(new MouseEvent("mousemove", {
        clientX: x, clientY: y, bubbles: true, cancelable: true, view: window
      }));
    });
  });
  document.addEventListener("pointerdown", function (event) {
    if (event.pointerType === "touch" && !onMapArea(event)) { Plotly.Fx.unhover(map); }
  }, true);

  function relayoutFor(name) {
    var v = views[name];
    return { "geo.projection.scale": v.scale, "geo.center.lon": v.lon,
             "geo.center.lat": v.lat, "geo.projection.rotation.lon": 0 };
  }
  function currentView() {
    var geo = map.layout.geo || {}, projection = geo.projection || {}, center = geo.center || {};
    return {
      scale: projection.scale == null ? 1 : projection.scale,
      lon: center.lon == null ? views.world.lon : center.lon,
      lat: center.lat == null ? views.world.lat : center.lat
    };
  }
  var settling = false;
  function enforceLimits() {
    var sp = subplot(), p = sp.projection;
    var before = [p.scale(), p.translate()[0], p.translate()[1]].concat(p.rotate());
    limitView(sp);
    var after = [p.scale(), p.translate()[0], p.translate()[1]].concat(p.rotate());
    var changed = before.some(function (value, i) { return Math.abs(value - after[i]) > 1e-6; });
    if (changed) {
      settling = true;
      sp.render(true);
      syncLayout(true);
      settling = false;
    }
    updateTouchMode(sp);
    markPreset();
  }
  function markPreset() {
    var now = currentView();
    document.querySelectorAll("[data-view]").forEach(function (button) {
      var v = views[button.dataset.view];
      var same = Math.abs(now.scale - v.scale) < 1e-3 && Math.abs(now.lon - v.lon) < 1e-2 &&
                 Math.abs(now.lat - v.lat) < 1e-2;
      button.setAttribute("aria-pressed", String(same));
    });
  }
  map.on("plotly_relayout", function () {
    if (!settling) { enforceLimits(); }
  });
  // Every full redraw (year, theme, colour view, view preset) resets fills
  // and outlines: decorate again (coalesced to one run per screen frame).
  map.on("plotly_afterplot", scheduleDecorate);

  // ---- legend layout by map width ------------------------------------------
  var legendLayouts = __LEGENDS__;
  var legendMode = "side";
  function legendModeFor(width) {
    if (width >= 1000) { return "side"; }
    if (width >= 600) { return "top"; }
    return "compact";
  }
  function fitLegend() {
    var mode = legendModeFor(map.clientWidth);
    if (mode === legendMode) { return; }
    legendMode = mode;
    var chosen = legendLayouts[mode];
    Plotly.restyle(map, { name: chosen.names }, T.legend);
    Plotly.restyle(map, chosen.colorbar, [T.colorbar]);
    Plotly.relayout(map, chosen.layout);
  }
  var resizeTimer = null;
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(fitLegend, 150);
  });

  // ---- years: note, Play / Pause -------------------------------------------
  var frames = __FRAMES__;
  var playButton = document.querySelector("[data-play]");
  function showFrame(name) {
    current = String(name);
    note.textContent = frameNotes[current] || "";
    scheduleDecorate();   // the older-data outlines belong to the latest view only
  }
  map.on("plotly_sliderchange", function (event) { showFrame(event.step.label); });
  map.on("plotly_animatingframe", function (event) { showFrame(event.name); });
  map.on("plotly_animated", scheduleDecorate);
  function setPlaying(playing) {
    playButton.setAttribute("aria-pressed", String(playing));
    playButton.textContent = playing ? "Pause" : "Play";
  }
  function play() {
    // Through the years from the one after the current; from the first year
    // when starting at Latest or the end. Ends at Latest.
    var start = frames.indexOf(current) + 1;
    if (start <= 0 || start >= frames.length) { start = 0; }
    setPlaying(true);
    Plotly.animate(map, frames.slice(start), {
      mode: "immediate", frame: { duration: 700, redraw: true }, transition: { duration: 0 }
    }).then(function () { setPlaying(false); }, function () { setPlaying(false); });
  }
  function pause() {
    Plotly.animate(map, [null], {
      mode: "immediate", frame: { duration: 0, redraw: false }, transition: { duration: 0 }
    }).catch(function () {});
    setPlaying(false);
  }
  playButton.addEventListener("click", function () {
    if (playButton.getAttribute("aria-pressed") === "true") { pause(); } else { play(); }
  });

  // ---- wiring -------------------------------------------------------------
  document.querySelectorAll("[data-theme-button]").forEach(function (button) {
    button.addEventListener("click", function () {
      storeChoice(button.dataset.themeButton);
      applyTheme(button.dataset.themeButton);
    });
  });
  darkQuery.addEventListener("change", function () {
    if (storedChoice() === "system") { applyTheme("system"); }
  });
  document.querySelectorAll("[data-view]").forEach(function (button) {
    button.addEventListener("click", function () {
      Plotly.relayout(map, relayoutFor(button.dataset.view)).catch(function () {});
    });
  });
  document.querySelectorAll("[data-color-mode]").forEach(function (button) {
    button.addEventListener("click", function () {
      colorMode = button.dataset.colorMode;
      try { localStorage.setItem(COLOR_KEY, colorMode); } catch (e) {}
      applyColors();
    });
  });

  window.initMap = function () {
    colorMode = storedColorMode();
    showFrame(__DEFAULT_FRAME__);
    applyTheme(storedChoice());
    fitLegend();
    markPreset();
  };
  if (window.mapDrawn) { window.initMap(); }
})();"""


def latest_banner(snapshot):
    """E.g. "Most recent value per country (41 of 45 are income years 2023-24)",
    counted from the snapshot: the most common income year and the one before."""
    common, older_before = latest_years(snapshot)
    recent = snapshot["income_year"].between(older_before, common).sum()
    return (f"Most recent value per country ({recent} of {len(snapshot)} are income years "
            f"{older_before}-{common % 100:02d})")


def older_countries(tables):
    return sorted(tables[LATEST].loc[tables[LATEST]["older"], "iso3"])


def frame_notes(tables, years, snapshot):
    """The line under the controls for each frame."""
    notes = {}
    for year in years:
        table = tables[str(year)]
        n = (table["trace"] != NO_DATA_TRACE).sum()
        notes[str(year)] = f"Income year {year}: {n} of {len(table)} countries have data."
    _, older_before = latest_years(snapshot)
    notes[LATEST] = (f"{latest_banner(snapshot)}. Dashed outline: older data, income year "
                     f"{older_before - 1} or earlier.")
    return notes


def page_script(tables, years, frame_names, snapshot):
    traces = {
        "hatched": HATCHED,
        "choropleths": SOLID + HATCHED + [NO_DATA_TRACE],
        "noData": NO_DATA_TRACE,
        "marker": MARKER_TRACE,
        "legend": LEGEND_TRACES,
        "tierCount": N_TIERS,
        "colorbar": COLORBAR_TRACE,
    }
    replacements = {
        "__THEMES__": json.dumps(theme_payload()),
        "__VIEWS__": json.dumps(VIEWS),
        "__FRAME_NOTES__": json.dumps(frame_notes(tables, years, snapshot)),
        "__LATEST__": json.dumps(LATEST),
        "__OLDER__": json.dumps(older_countries(tables)),
        "__TRACES__": json.dumps(traces),
        "__GEO_LON__": json.dumps(GEO_LON_RANGE),
        "__GEO_LAT__": json.dumps(GEO_LAT_RANGE),
        "__DEFAULT_FRAME__": json.dumps(LATEST),
        "__FRAMES__": json.dumps(frame_names),
        "__LEGENDS__": json.dumps(LEGEND_LAYOUTS),
        "__MARGINS__": json.dumps(PAN_MARGINS),
    }
    script = PAGE_SCRIPT
    for placeholder, value in replacements.items():
        script = script.replace(placeholder, value)
    return script


def og_image_version(path):
    """First 10 hex digits of the image's SHA-256 (crawlers cache og:image by URL)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def share_tags(og_version):
    image_url = f"{SITE_URL}{OG_IMAGE}?v={og_version}"
    tags = [
        ("name", "description", SHARE_DESCRIPTION),
        ("property", "og:type", "website"),
        ("property", "og:url", SITE_URL),
        ("property", "og:title", HEADLINE),
        ("property", "og:description", SHARE_DESCRIPTION),
        ("property", "og:image", image_url),
        ("property", "og:image:width", str(OG_SIZE[0] * OG_SCALE)),
        ("property", "og:image:height", str(OG_SIZE[1] * OG_SCALE)),
        ("property", "og:image:alt", OG_IMAGE_ALT),
        ("name", "twitter:card", "summary_large_image"),
    ]
    lines = []
    for attribute, key, value in tags:
        lines.append(f'<meta {attribute}="{key}" content="{html.escape(value, quote=True)}">')
    return "\n".join(lines)


def uk_offset_text(layer_eurostat, oecd):
    mean, low, high, first, last = source_offset("GBR", layer_eurostat, oecd)
    return (f"{-mean:.3f} lower on average ({-high:.3f} to {-low:.3f} lower, survey years "
            f"{first}-{last})")


def page_html(fig, tables, years, frame_names, snapshot, og_version):
    figure_html = fig.to_html(
        include_plotlyjs=True,
        full_html=False,
        auto_play=False,
        div_id="map",
        post_script="window.mapDrawn = true; if (window.initMap) { window.initMap(); }",
        config=PLOTLY_CONFIG,
    )
    eurostat = pd.read_csv(PROCESSED_DIR / "eurostat_ratio.csv", keep_default_na=False)
    oecd = pd.read_csv(PROCESSED_DIR / "oecd_ratio.csv", keep_default_na=False)
    latest = tables[LATEST]
    n_data = (latest["trace"] != NO_DATA_TRACE).sum()
    n_oecd = latest["trace"].isin(HATCHED).sum()
    hatch_swatch, marker_swatch, older_swatch = key_swatches()
    low_year, high_year = int(snapshot["income_year"].min()), int(snapshot["income_year"].max())
    tier_text = ", ".join(f"<strong>{name.lower()}</strong>" for name in TIER_NAMES)
    light, dark = THEMES["light"], THEMES["dark"]
    common, older_before = latest_years(snapshot)
    older = snapshot[snapshot["income_year"] < older_before].sort_values("income_year")
    older_text = ", ".join(f"{ISO3_NAMES[c]} {y}" for c, y in zip(older["country"], older["income_year"]))
    changes = change_summary(eurostat)
    lines_text = " and ".join(f"{b:.2f}" for b in TIER_BOUNDARIES[:-1])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Typical vs Average Income</title>
{share_tags(og_version)}
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<script>{EARLY_THEME_SCRIPT}</script>
<style>
  :root {{ --surface: {light['surface']}; --text: {light['text']}; --text-2: {light['text_2']};
          --border: {light['border']}; --control: {light['control_bg']}; --accent: {light['accent']};
          color-scheme: light; }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{ --surface: {dark['surface']}; --text: {dark['text']};
          --text-2: {dark['text_2']}; --border: {dark['border']}; --control: {dark['control_bg']};
          --accent: {dark['accent']}; color-scheme: dark; }}
  }}
  :root[data-theme="dark"] {{ --surface: {dark['surface']}; --text: {dark['text']};
          --text-2: {dark['text_2']}; --border: {dark['border']}; --control: {dark['control_bg']};
          --accent: {dark['accent']}; color-scheme: dark; }}
  body {{ margin: 0; background: var(--surface); color: var(--text);
         font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 16px; }}
  header {{ display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: flex-start;
           justify-content: space-between; }}
  h1 {{ font-size: 1.5rem; margin: 0.25rem 0; flex: 1 1 20rem; }}
  .lede, .caption {{ color: var(--text-2); margin: 0 0 0.75rem; }}
  .caption {{ font-size: 0.9rem; }}
  .map-frame {{ height: {MAP_HEIGHT_CSS}; }}
  .map-frame > div, .map-frame .plotly-graph-div {{ height: 100%; }}
  .map-frame {{ touch-action: pan-y; }}
  .map-frame.zoomed {{ touch-action: none; }}
  .map-frame.zoomed .geo {{ cursor: grab; }}
  .hatch-defs {{ position: absolute; width: 0; height: 0; }}
  .segmented {{ display: inline-flex; border: 1px solid var(--border); border-radius: 6px;
               overflow: hidden; }}
  .segmented button {{ font: inherit; font-size: 0.85rem; padding: 4px 10px; border: 0;
                      background: var(--control); color: var(--text); cursor: pointer; }}
  .segmented button + button {{ border-left: 1px solid var(--border); }}
  .segmented button[aria-pressed="true"] {{ background: var(--accent); color: #ffffff; }}
  .segmented button:focus-visible {{ outline: 2px solid var(--accent); outline-offset: -2px; }}
  .map-tools {{ display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center;
               margin: 0.25rem 0; }}
  .key {{ display: flex; flex-wrap: wrap; gap: 4px 18px; font-size: 0.85rem; color: var(--text-2);
         margin: 0.25rem 0; }}
  .key span {{ display: inline-flex; align-items: center; gap: 6px; }}
  .key svg {{ color: var(--text); flex: none; }}
  .year-note {{ min-height: 1.4em; font-size: 0.9rem; color: var(--text-2); margin: 0; flex: 1 1 16rem; }}
  h2 {{ font-size: 1rem; margin: 1.25rem 0 0.25rem; }}
  ul {{ color: var(--text-2); font-size: 0.9rem; padding-left: 1.2rem; }}
  li {{ margin: 0.2rem 0; }}
  a {{ color: inherit; }}
</style>
</head>
<body>
{hatch_defs()}
<main>
<header>
<h1>{HEADLINE}</h1>
<div class="segmented" role="group" aria-label="Colour theme">
  <button type="button" data-theme-button="system" aria-pressed="true">System</button>
  <button type="button" data-theme-button="light" aria-pressed="false">Light</button>
  <button type="button" data-theme-button="dark" aria-pressed="false">Dark</button>
</div>
</header>
<p class="lede">Median income as a share of mean income, European and OECD countries.
The lower the share, the further the person in the middle is from the "average" income.
{latest_banner(snapshot)}; {len(latest) - n_data} of {len(latest)} countries in scope have no data.</p>
<p class="caption"><strong>What is measured:</strong> median equivalised disposable income (the
person in the middle) divided by the mean (the average). Disposable income is household income
after taxes and benefits; "equivalised" adjusts it for household size. "The typical person has
X% of the average income" means the median is X% of the mean. Tiers: {tier_text}.</p>
<div class="map-tools">
  <div class="segmented" role="group" aria-label="Map view">
    <button type="button" data-view="world" aria-pressed="true">World</button>
    <button type="button" data-view="europe" aria-pressed="false">Europe</button>
  </div>
  <div class="segmented" role="group" aria-label="Colours">
    <button type="button" data-color-mode="tiers" aria-pressed="true">Tiers</button>
    <button type="button" data-color-mode="continuous" aria-pressed="false">Continuous</button>
  </div>
  <div class="segmented" role="group" aria-label="Years">
    <button type="button" data-play aria-pressed="false">Play</button>
  </div>
  <p class="year-note" id="year-note" aria-live="polite"></p>
</div>
<div class="key">
  <span>{hatch_swatch} Hatched: OECD value ({n_oecd} countries in the latest view), a different method from Eurostat</span>
  <span>{marker_swatch} Circle: OECD value within {SOURCE_UNCERTAINTY:g} of a tier line, so its tier may differ under Eurostat's method</span>
  <span>{older_swatch} Dashed outline (latest view): older data, income year {older_before - 1} or earlier</span>
</div>
<div class="map-frame">
{figure_html}
</div>
<h2>How to read it</h2>
<ul>
  <li><strong>Sources.</strong> European countries: Eurostat (EU-SILC survey). Non-European OECD
      members: the OECD Income Distribution Database, hatched. Each country's series comes from
      one source only; the two are never combined.</li>
  <li><strong>The sources differ in method</strong> (how income is adjusted for household size,
      and how years are labelled). Where both cover the same country and year, their ratios agree
      within ±{SOURCE_UNCERTAINTY:g} in 95% of cases. OECD values that close to a tier line are
      marked with a circle.</li>
  <li><strong>United Kingdom.</strong> Eurostat stopped covering the UK after income year 2017, so
      the latest view shows the OECD value (hatched). For the UK the OECD ratio is
      {uk_offset_text(eurostat, oecd)}
      than Eurostat's, so the UK's latest value is probably understated. The yearly views show
      only the Eurostat series.</li>
  <li><strong>Tier lines</strong> ({", ".join(f"{b:.2f}" for b in TIER_BOUNDARIES)}): {lines_text} sit in
      the widest gaps between neighbouring countries; {TIER_BOUNDARIES[-1]:.2f} is the only place the
      central cluster of countries can be split. <strong>Continuous</strong> shows the same values on
      one smooth scale, without the lines.</li>
  <li><strong>Years are income years</strong>: the survey asks about the previous year's income.
      The latest view mixes years ({low_year}-{high_year}); the hover shows each country's year.
      Most are {older_before}-{common}; older values have a dashed outline ({older_text}).
      A country's ratio moves slowly: in Eurostat's data the typical change is
      {changes.loc[1, "median"]:.3f} over one year and {changes.loc[4, "median"]:.3f} over four,
      and 9 in 10 changes are under {changes.loc[1, "p90"]:.3f} and {changes.loc[4, "p90"]:.3f}.
      So an older value can differ from today's by about as much as the two sources differ,
      which matters only near a tier line.</li>
  <li>Grey: in scope but no data (the hover says why). Plain land: outside this project's scope.</li>
  <li>Kosovo: the base map draws Kosovo's territory as part of Serbia, so that area shows Serbia's
      colour and data. Kosovo's own value is in the data download.</li>
  <li>Scroll to zoom; drag to move once zoomed in. World and Europe reset the view. Small
      countries (Malta, Luxembourg, Cyprus) are a few pixels wide: zoom in and hover.</li>
  <li>Official statistics from Eurostat and the OECD. Data:
      <a href="snapshot_median_mean_ratio.csv" download>latest view (CSV)</a>,
      <a href="layer_median_mean_ratio.csv" download>all years (CSV)</a>.
      <a href="{REPO_URL}" data-source-link>Source code</a> (method and data decisions included).</li>
</ul>
</main>
<script>{page_script(tables, years, frame_names, snapshot)}</script>
</body>
</html>
"""


# --- CSP -----------------------------------------------------------------------

def inline_scripts(page):
    return re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", page, flags=re.DOTALL)


def script_hash(text):
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


def add_csp_meta(page):
    """Insert the Content-Security-Policy as the FIRST element in <head>,
    allowing exactly this page's inline scripts by hash."""
    hashes = [script_hash(text) for text in inline_scripts(page)]
    policy = CSP_TEMPLATE.format(script_hashes=" ".join(hashes))
    meta = f'<meta http-equiv="Content-Security-Policy" content="{policy}">'
    if page.count("<head>\n") != 1:
        raise ValueError("Expected exactly one <head>")
    return page.replace("<head>\n", f"<head>\n{meta}\n", 1)


def check_csp_meta(page):
    head = page.split("<head>\n", 1)[1]
    first_element = head.split("\n", 1)[0]
    if not first_element.startswith('<meta http-equiv="Content-Security-Policy"'):
        raise ValueError(f"CSP meta is not the first element in <head>: {first_element[:80]}")
    for text in inline_scripts(page):
        if script_hash(text) not in first_element:
            raise ValueError("An inline script is not covered by the CSP hashes")
    print(f"CSP check: <meta> is first in <head>; all {len(inline_scripts(page))} inline "
          f"scripts are allowed by hash.")


# --- static images (README) ----------------------------------------------------

def static_figure(fig):
    """The latest view without controls. OECD values are not hatched here
    (the hatch is drawn by the page script)."""
    static = go.Figure(data=fig.data, layout=fig.layout)
    static.layout.sliders = ()
    return static


def save_png(fig, path, view_name):
    static = static_figure(fig)
    view = VIEWS[view_name]
    static.update_layout(width=1200, height=620)
    static.update_geos(projection_scale=view["scale"], projection_rotation_lon=0,
                       center=dict(lon=view["lon"], lat=view["lat"]))
    static.write_image(path, scale=2)


def save_og_image(fig, path):
    width, height = OG_SIZE
    top = OG_HEADER_PX
    plot_height = height - top
    static = static_figure(fig)
    for index, name in zip(LEGEND_TRACES, TIER_NAMES + [NO_DATA, UNCERTAIN_SHORT]):
        static.data[index].name = name
    static.update_geos(
        projection_scale=1, projection_rotation_lon=0,
        lonaxis_range=OG_LON_RANGE, lataxis_range=OG_LAT_RANGE,
        center=dict(lon=sum(OG_LON_RANGE) / 2, lat=sum(OG_LAT_RANGE) / 2),
        domain=dict(x=[0, 1], y=[0, 1]),
    )
    static.update_layout(
        width=width, height=height, margin=dict(l=0, r=0, t=top, b=0),
        annotations=[
            dict(text=f"<b>{HEADLINE.replace(' from', '<br>from')}</b>",
                 x=0.03, y=1 + (top - 18) / plot_height, xref="paper", yref="paper",
                 yanchor="top", xanchor="left", align="left", showarrow=False,
                 font=dict(size=52, color=LIGHT["text"])),
        ],
        legend=dict(
            title=dict(text="<b>Latest</b>: the typical person's income<br>as a % of the average",
                       side="top", font=dict(size=22, color=LIGHT["text"])),
            orientation="v", x=0.01, y=0.03, xanchor="left", yanchor="bottom",
            font=dict(size=22, color=LIGHT["text"]), bgcolor=LIGHT["legend_bg"],
            entrywidthmode="pixels", entrywidth=0, itemsizing="constant",
        ),
    )
    for index in LEGEND_TRACES:
        static.data[index].marker.size = 18
    static.write_image(path, width=width, height=height, scale=OG_SCALE)


def main():
    tables, years, snapshot, layer = load_tables()
    fig, frame_names = build_figure(tables, years)
    check_frames(fig, frame_names, tables)
    check_kosovo_isolated(fig)

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    og_path = SITE_DIR / OG_IMAGE
    save_og_image(fig, og_path)
    og_version = og_image_version(og_path)
    print(f"Saved {og_path} ({og_path.stat().st_size / 1e3:.0f} kB, version {og_version})")

    html_path = SITE_DIR / "index.html"
    page = add_csp_meta(page_html(fig, tables, years, frame_names, snapshot, og_version))
    check_csp_meta(page)
    html_path.write_text(page, encoding="utf-8", newline="\n")
    print(f"Saved {html_path} ({html_path.stat().st_size / 1e6:.1f} MB)")

    (SITE_DIR / "favicon.svg").write_text(FAVICON_SVG, encoding="utf-8", newline="\n")
    for name in ["snapshot_median_mean_ratio.csv", "layer_median_mean_ratio.csv"]:
        shutil.copyfile(PROCESSED_DIR / name, SITE_DIR / name)
    print(f"Copied the data CSVs to {SITE_DIR}")

    for suffix, view_name in [("", "world"), ("_europe", "europe")]:
        png_path = IMAGES_DIR / f"map_latest{suffix}.png"
        save_png(fig, png_path, view_name)
        print(f"Saved {png_path}")

    latest = tables[LATEST]
    counts = {}
    for position in SOLID:
        counts[TIER_NAMES[position]] = int(latest["trace"].isin([position, position + N_TIERS]).sum())
    counts[NO_DATA] = int((latest["trace"] == NO_DATA_TRACE).sum())
    print(f"\nLatest view: {counts}")
    print(f"Slider: income years {years[0]}-{years[-1]} + {LATEST}")


if __name__ == "__main__":
    main()
