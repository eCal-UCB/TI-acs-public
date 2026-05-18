"""Color palettes, label dictionaries, and Bay-area FIPS constants.

Pure data — no logic. Imported by the notebooks and by ti_acs.plotting.
"""

# Bay Area counties used in the study (Alameda, Contra Costa, Marin,
# San Francisco, San Mateo, Santa Clara). Excludes Napa, Solano, Sonoma to
# match the mobility dataset coverage (see paper, §2.3 footnote).
BAY_COUNTY_FIPS = ["001", "013", "041", "075", "081", "085"]

# Counties whose water polygons we render lightblue under the choropleths
# to show the SF bay itself (some include water that touches Bay tracts).
BAY_COUNTY_WATER_FIPS = ["001", "013", "041", "075", "081"]

# Bar/density colors for the location and TOU segment plots.
# Tuples are (fill, edge/dark accent).
LOC_COLORS = {
    "all":   ("gold",       "goldenrod"),
    "home":  ("skyblue",    "slategrey"),
    "work":  ("yellowgreen", "olivedrab"),
    "other": ("pink",       "palevioletred"),
}

TOU_COLORS = {
    "SuperOffPeak": ("powderblue", "steelblue"),
    "OffPeak":      ("lavender",   "slateblue"),
    "Peak":         ("plum",       "purple"),
}

# (Display label, time window, total hours per day) — informational, used in plot labels.
TOU_INFO = {
    "SuperOffPeak": ("Super Off-Peak", "9 AM - 2 PM",         5),
    "OffPeak":      ("Off-Peak",       "9 PM - 9 AM, 2 PM - 4 PM", 14),
    "Peak":         ("Peak",           "4 PM - 9 PM",         5),
}

# Colors for census tracts grouped by dominant racial/ethnic identity.
RACE_COLORS = {
    "White_nonHis": "dodgerblue",
    "Black_nonHis": "darkorange",
    "Asian_nonHis": "yellowgreen",
    "Hispanic":     "hotpink",
    "No-dominant":  "slategrey",
}

RACE_LABELS = {
    "White_nonHis": "White",
    "Black_nonHis": "Black",
    "Asian_nonHis": "Asian",
    "Hispanic":     "Hispanic",
    "No-dominant":  "No dominant",
}

# Income quintile labels used in the equity notebook.
INCOME_LABELS = {
    0: "Low",
    1: "Low-middle",
    2: "Middle",
    3: "Upper-middle",
    4: "High",
}
