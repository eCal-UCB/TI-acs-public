"""Minimal loaders for the shipped data files.

Each function reads one file and returns a tidy structure with a clean index.
No math, no unit conversion, no derived columns — those steps live in the
notebooks so the reader can see them.

Repo layout assumed:
    public_repo/
      ti_acs/io.py        (this file)
      data/*.xlsx, *.csv
      data/shapefiles/...
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd

# ---------------------------------------------------------------------------
# Path resolution: ti_acs/io.py is at <repo>/ti_acs/io.py, so data is one
# level up. Resolving via __file__ keeps the repo movable.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA = _REPO_ROOT / "data"

# Stats files and what they each cover. Keep this dict in lock-step with §5
# of the plan and with the file rename in the public repo.
_STATS_FILES = {
    "hours_annual":     "ti_acs_hours_tract_annual.xlsx",
    "hours_multidist":  "ti_acs_hours_tract_multidist.xlsx",
    "ports_annual":     "ti_acs_ports_tract_annual.xlsx",
}

# What each file actually contains, used by the validators below.
SUPPORTED_CONFIG = {
    "hours_annual":    {"years": list(range(2012, 2025)), "dists": [1000]},
    "hours_multidist": {"years": [2015, 2018, 2021, 2024], "dists": [500, 1000, 2000, 3000]},
    "ports_annual":    {"years": list(range(2012, 2025)), "dists": [1000]},
}


def load_tract_stats(kind: str) -> dict[str, pd.DataFrame]:
    """Load one of the tract-level TI-acs statistics files.

    Parameters
    ----------
    kind : {"hours_annual", "hours_multidist", "ports_annual"}
        Which precomputed file to load. See SUPPORTED_CONFIG for what each
        file covers in (year, distance) space.

    Returns
    -------
    dict with keys {"mean", "pct25", "pct75", "num_users"}; each value is a
    DataFrame indexed by census-tract GEOID (string, 11 chars, zero-padded).
    Columns of the first three follow the schema "{year}_{level}_{dist}_{metric}",
    where metric ∈ {"all", "home", "HnW", "SuperOffPeak", "OffPeak", "Peak"}.
    `num_users` has a single column "num_users".

    Notes
    -----
    No unit conversion is applied. The duration-style files (hours_*) hold
    fractions-of-day; the notebook should multiply by 24 to get hours-per-day.
    """
    if kind not in _STATS_FILES:
        raise ValueError(
            f"Unknown stats kind {kind!r}. Choose from {list(_STATS_FILES)}."
        )
    path = _DATA / _STATS_FILES[kind]
    dfs = pd.read_excel(path, sheet_name=None, index_col=0)
    # Zero-pad GEOID to 11 characters (census tract). Excel often strips
    # the leading zero from California's "06" state FIP.
    for k in dfs:
        dfs[k].index = "0" + dfs[k].index.astype(str)
    return dfs


def validate_config(kind: str, years=None, dists=None) -> None:
    """Raise ValueError if (year, dist) combos are not in the shipped file.

    Use this in the notebook config cell to fail fast and clearly when a user
    sets a value the data cannot support.
    """
    cfg = SUPPORTED_CONFIG[kind]
    if years is not None:
        bad = [y for y in years if y not in cfg["years"]]
        if bad:
            raise ValueError(
                f"Year(s) {bad} not in stats file {kind!r}. "
                f"Supported: {cfg['years']}."
            )
    if dists is not None:
        bad = [d for d in dists if d not in cfg["dists"]]
        if bad:
            raise ValueError(
                f"Distance(s) {bad} m not in stats file {kind!r}. "
                f"Supported: {cfg['dists']} m."
            )


def load_acs_demographics() -> dict[str, pd.DataFrame]:
    """Load ACS census-tract demographics.

    Returns one DataFrame per ACS variable (e.g. Pop_Hispanic_pct, House_MUD_pct,
    Income_Household_med). Each is indexed by GEOID (string, 11 chars, zero-
    padded to match `load_tract_stats`) and has integer-year columns.
    """
    path = _DATA / "acs_tract_demographics.xlsx"
    dfs = pd.read_excel(path, sheet_name=None, index_col=0)
    # The xlsx stores GEOID as int64 (Excel strips California's "06" prefix).
    # Zero-pad to 11 chars so it matches the stats files.
    for k in dfs:
        dfs[k].index = dfs[k].index.astype(str).str.zfill(11)
    return dfs


def load_evcs() -> pd.DataFrame:
    """Load the SF Bay public-EVCS roster derived from AFDC (June 2024).

    Returns the raw DataFrame with at least the columns: 'Longitude',
    'Latitude', 'Open Date', 'EV Level2 EVSE Num', 'EV DC Fast Count'.
    No spatial join is performed here — the notebook does that explicitly
    so the reader sees the EVCS-to-tract assignment step.
    """
    path = _DATA / "sf_bay_public_evcs.csv"
    return pd.read_csv(path)


def load_shapefiles(epsg: int = 4326) -> dict[str, gpd.GeoDataFrame]:
    """Load the shapefiles needed for the Bay-area maps.

    Returns
    -------
    dict with keys:
        "county" : full California county polygons (used to draw water under
                   the Bay choropleth and for county-level reference). Has a
                   "COUNTY_FIP" column matching BAY_COUNTY_FIPS.
        "tract"  : Bay-area census tracts only (TIGER 2021, subset to the 6
                   counties in BAY_COUNTY_FIPS); has a "GEOID" column.
                   Also exposes "COUNTY_FIP" (renamed from "COUNTYFP") for
                   consistent join with the stats DataFrames.
    """
    # Defensive: pyogrio may surface RuntimeWarnings whose text contains the
    # absolute path of the shapefile (e.g. winding-order auto-correction).
    # Those messages would leak the reader's local install path into notebook
    # output cells. The shipped shapefiles have been pre-corrected, so this
    # filter is belt-and-suspenders for future edits.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio.*")
        county = gpd.read_file(_DATA / "shapefiles" / "CA_County" / "cnty19_1.shp").to_crs(epsg=epsg)
        tract = gpd.read_file(_DATA / "shapefiles" / "CA_Tract_BayArea" / "tl_2021_06_tract_bayarea.shp").to_crs(epsg=epsg)
    tract = tract.rename(columns={"COUNTYFP": "COUNTY_FIP"})
    tract = tract.set_index("GEOID", drop=False)
    return {"county": county, "tract": tract}


def load_cached_race_regression(income_control_order: int) -> dict[str, pd.DataFrame]:
    """Load cached race-regression coefficients keyed by income-control order.

    Parameters
    ----------
    income_control_order : {0, 1, 4}
        Polynomial order of the ln(income) control. The paper headline
        (Fig. 4) uses 1; the robustness panel (Fig. 6) compares 0 and 4.

    Returns
    -------
    dict mapping sheet name (e.g. "L2_all", "DCFC_home") to a DataFrame
    indexed by "{year}-{group}" with columns ["coef", "lo", "hi", "p-value"].
    """
    if income_control_order not in {0, 1, 4}:
        raise ValueError(
            f"income_control_order={income_control_order} has no cached file. "
            "Shipped caches cover {0, 1, 4}; rerun the regression inline in "
            "notebook 03 to compute other orders."
        )
    path = _DATA / f"race_regression_I{income_control_order}.xlsx"
    return pd.read_excel(path, sheet_name=None, index_col=0)
