"""Matplotlib-heavy figure assembly for Figs. 2–8.

Each function takes a pre-computed DataFrame (or simple dict) plus an `ax`,
applies styling, and returns nothing. Notebooks own `plt.subplots` and
`plt.savefig` calls; this module focuses on the per-axes rendering.

No data wrangling or methodology (Gini, regression, demographic grouping)
lives here — that stays inline in the notebooks.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt

from .style import (
    BAY_COUNTY_FIPS,
    BAY_COUNTY_WATER_FIPS,
    LOC_COLORS,
    RACE_COLORS,
    RACE_LABELS,
    TOU_COLORS,
    TOU_INFO,
)


# =============================================================================
# Choropleth maps (Fig. 2 a/b, Fig. 7, Fig. 8)
# =============================================================================

def plot_tract_choropleth(
    ax,
    gdf_tract_with_value,
    county_gdf,
    value_col: str,
    level: str,
    year: int,
    dist: int,
    metric_kind: str = "hours",
    vmax: float | None = None,
    legend: bool = True,
    title_fontsize: int = 16,
):
    """Draw one tract-level choropleth of TI-acs over the Bay area.

    Parameters
    ----------
    gdf_tract_with_value : GeoDataFrame indexed by GEOID, must contain
        `value_col`, `geometry`, and a "COUNTY_FIP" column. Caller is
        responsible for joining stats onto geometry.
    county_gdf : GeoDataFrame for CA counties (used to render water polygons).
    metric_kind : "hours" or "ports". Controls colorbar scale and label.
    """
    cmap = "YlGn" if level == "L2" else "RdPu"
    if metric_kind == "hours":
        vmax = 24 if vmax is None else vmax
        extend = None
        label = "Accessible Hours"
    else:
        vmax = (15 if level == "L2" else 10) if vmax is None else vmax
        extend = "max"
        label = "# of Accessible ports"

    bay_mask = gdf_tract_with_value["COUNTY_FIP"].isin(BAY_COUNTY_FIPS)
    gdf_tract_with_value[bay_mask].plot(
        column=value_col, cmap=cmap, edgecolor="silver", linewidth=0.3,
        ax=ax, vmin=0, vmax=vmax,
        legend=legend,
        legend_kwds={"orientation": "horizontal", "shrink": 0.55, "aspect": 12,
                     "anchor": (0.6, 1), "extend": extend},
    )
    # Render water under the choropleth so the SF bay itself shows up.
    county_gdf[county_gdf["COUNTY_FIP"].isin(BAY_COUNTY_WATER_FIPS)].plot(
        color="lightblue", edgecolor=(0, 0, 0, 0), ax=ax, zorder=-200,
    )

    stats = gdf_tract_with_value[bay_mask][value_col].quantile([0.25, 0.5, 0.75])
    mean_val = gdf_tract_with_value[bay_mask][value_col].mean()
    stats_txt = (
        f"mean: {mean_val:.2f}",
        rf'$_{{[25, med, 75]=[{stats[0.25]:.2f}, {stats[0.5]:.2f}, {stats[0.75]:.2f}]}}$',
    )
    if legend:
        ax.text(0.03, -0.06, f"CT avg {label}", fontsize=14,
                ha="left", va="bottom", transform=ax.transAxes)
        ax.text(0.1, -0.068, f"within {dist} m range", fontsize=14, color="dimgrey",
                ha="left", va="top", transform=ax.transAxes)
        ax.text(0.03, -0.19, stats_txt[0] + "   " + stats_txt[1], fontsize=14,
                color="dimgrey", ha="left", va="bottom", transform=ax.transAxes)
    else:
        ax.text(0.5, 0.08, stats_txt[0] + "\n" + stats_txt[1], fontsize=14,
                color="dimgrey", ha="center", va="top", transform=ax.transAxes)

    ax.set_title(f"{year} ({level})", fontsize=title_fontsize)
    ax.set_axis_off()


# =============================================================================
# Trend with twin axis (Fig. 2 c/d)
# =============================================================================

def plot_ti_acs_trend(
    ax,
    quantile_df: pd.DataFrame,
    total_ports_series: pd.Series,
    level: str,
    metric_kind: str = "hours",
    year_up: int | None = None,
):
    """Plot median + IQR TI-acs over years against cumulative installed ports.

    Parameters
    ----------
    quantile_df : DataFrame indexed by year with columns {0.25, 0.5, 0.75}
        giving tract-level quantiles of TI-acs per year.
    total_ports_series : Series indexed by year, total installed ports of `level`.
    """
    if year_up is None:
        year_up = int(quantile_df.index.max())
    x = list(quantile_df.index[quantile_df.index <= year_up])
    y0 = quantile_df.loc[x, 0.5]
    y0_lo, y0_hi = quantile_df.loc[x, 0.25], quantile_df.loc[x, 0.75]
    y1 = total_ports_series.loc[x]

    c0 = "olivedrab" if level == "L2" else "palevioletred"
    c1 = "steelblue"
    unit = "hrs" if metric_kind == "hours" else "count"

    ax.plot(x, y0, label=f'TI-acs (CT median) [{unit}]', color=c0, marker=">", ms=3)
    ax.fill_between(x, y0_lo, y0_hi, label=f'TI-acs (CT IQR) [{unit}]',
                    alpha=0.2, color=c0, zorder=-100)
    ax.scatter(x[-1], y0.iloc[-1], color=c0, marker=">")

    ax.set_xlim(min(x) - 0.5, max(x) + 0.5)
    y0_max = quantile_df[0.75].max()
    ax.set_ylim(-0.02 * y0_max, 1.05 * y0_max)

    ax1 = ax.twinx()
    ax1.plot(x, y1, label=f'Total {level} EVSE', color=c1, linestyle='--')
    ax1.scatter(x[-1], y1.iloc[-1], color=c1)

    # Anchor right-axis at the 2018 ratio so the dashed line visually tracks the trend.
    anchor_year = 2018 if 2018 in quantile_df.index else x[0]
    axs_ratio = total_ports_series[anchor_year] / quantile_df[0.5][anchor_year]
    y_lim = ax.get_ylim()
    ax1.set_ylim(y_lim[0] * axs_ratio, y_lim[1] * axs_ratio)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(c0)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_color(c1)
    ax1.spines['left'].set_color(c0)
    ax.yaxis.label.set_color(c0)
    ax1.yaxis.label.set_color(c1)
    ax.tick_params(axis='y', colors=c0)
    ax1.tick_params(axis='y', colors=c1)

    ax.legend(loc=(0.02, 0.8), frameon=False, fontsize=14)
    ax1.legend(loc=(0.02, 0.67), frameon=False, fontsize=14)


# =============================================================================
# Breakdown trend bars (Fig. 3 a/b/e/f, Fig. 5)
# =============================================================================

def plot_breakdown_bars(
    ax,
    mean_df: pd.DataFrame,
    median_df: pd.DataFrame,
    pct25_df: pd.DataFrame,
    pct75_df: pd.DataFrame,
    segment_type: str,
    *,
    level: str | None = None,
    dist: int | None = None,
    annotate: bool = True,
    legend: bool = False,
    x_labels=None,
):
    """Clustered, stacked breakdown bars with median-anchored IQR error bars.

    Mirrors the layout used in the paper's Fig. 3 and Fig. 5:
      * three segments per index value are drawn as narrow bars offset
        horizontally by ±0.16 (so the trio is visually clustered);
      * within each cluster the bars are *stacked* by mean (home at 0,
        work atop home, other atop home+work — likewise for the three TOU
        periods), so the cluster total equals the mean of `all`;
      * a filled-circle marker sits at each segment's median (raised by the
        same stacking bottom), with whiskers down to the 25th and up to the
        75th percentile across tracts.

    Parameters
    ----------
    mean_df, median_df, pct25_df, pct75_df :
        Four DataFrames with the same index (years, or distances) and
        columns matching the chosen segments.
    segment_type : "location" | "tou".
    level, dist :
        Optional; if both given and `annotate=True`, a top-right annotation
        shows e.g. "L2 / within 1000 m".
    """
    if segment_type == "location":
        metrics = ["home", "work", "other"]
        colors = LOC_COLORS
    elif segment_type == "tou":
        metrics = ["SuperOffPeak", "OffPeak", "Peak"]
        colors = TOU_COLORS
    else:
        raise ValueError(f"segment_type must be 'location' or 'tou', got {segment_type!r}")

    # Vertical stack offsets: home at 0, work atop home, other atop home+work.
    y_bottom = mean_df.copy()
    y_bottom[metrics[0]] = 0
    for i in range(1, len(metrics)):
        y_bottom[metrics[i]] = mean_df[metrics[:i]].sum(axis=1)

    xs = np.arange(len(mean_df))
    width = 0.3
    offset_step = 0.16
    for idx, m in enumerate(metrics):
        fill_c, edge_c = colors[m]
        x_off = xs + offset_step * (idx - 1)   # -1, 0, +1
        ax.bar(x_off, mean_df[m].values, bottom=y_bottom[m].values,
               width=width, color=fill_c, label=m)
        yerr = np.array([
            (median_df[m] - pct25_df[m]).values,
            (pct75_df[m] - median_df[m]).values,
        ])
        ax.errorbar(x_off, (median_df[m] + y_bottom[m]).values,
                    yerr=yerr, ecolor=edge_c, capsize=1, capthick=1,
                    fmt='o', ms=4, mfc=edge_c, mec=edge_c)
        if legend:
            x = xs[-1] + offset_step * (idx + 2)
            y = 0.5 * mean_df[m].iloc[-1] + y_bottom[m].iloc[-1]
            ax.text(x, y, m, fontsize=10, ha="center", va="center",
                    color=edge_c, rotation=90)

    if x_labels is None:
        x_labels = [str(v) for v in mean_df.index]
    ax.set_xticks(xs)
    ax.set_xticklabels(x_labels, rotation=0)
    ax.set_ylabel("Accessible Hours", fontsize=16)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if annotate and level is not None and dist is not None:
        ax.text(0.73, 0.92, level, fontsize=18, ha="center", va="bottom",
                fontweight="bold", color="dimgrey", transform=ax.transAxes)
        ax.text(0.73, 0.90, f"within {dist} m", fontsize=14, ha="center",
                va="top", color="dimgrey", transform=ax.transAxes)


# =============================================================================
# Segment KDE insets (Fig. 3 a1/b1/e1/f1, Fig. 5 insets)
# =============================================================================

def plot_segment_kde(ax, values: pd.Series, segment: str, segment_type: str,
                     annotate: bool = False, xlim: tuple | None = None):
    """KDE of one tract-level segment for the 2024 cross-section.

    Draws a single filled KDE curve on `ax`. To recreate the original Fig. 3
    a1/b1 inset stack, place three of these on transparent inset axes (one
    per segment) with overlapping bbox offsets — the curves visually merge.

    Parameters
    ----------
    values : 1-D Series of tract-level values for `segment`.
    segment : segment name (e.g. "home", "OffPeak"); selects the color from
        LOC_COLORS or TOU_COLORS.
    segment_type : "location" | "tou".
    xlim : optional fixed x-axis range so the three stacked insets align.
    """
    if segment_type == "location":
        colors = LOC_COLORS
    elif segment_type == "tou":
        colors = TOU_COLORS
    else:
        raise ValueError(f"segment_type must be 'location' or 'tou', got {segment_type!r}")
    if segment not in colors:
        raise ValueError(f"unknown segment {segment!r} for segment_type={segment_type!r}")
    fill_c, edge_c = colors[segment]

    sns.kdeplot(data=values, ax=ax, fill=True, color=fill_c,
                linewidth=0, bw_adjust=0.1, cut=0, alpha=1)

    for spine in ["left", "right", "top"]:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color("slategrey")
    ax.spines['bottom'].set_linewidth(0.5)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_ylabel("")
    ax.set_xlabel("")
    if xlim is not None:
        ax.set_xlim(*xlim)
    # Transparent axes background so stacked insets reveal each other.
    ax.set_facecolor((0, 0, 0, 0))
    ax.patch.set_alpha(0)

    label = segment if segment_type == "location" else TOU_INFO[segment][0]
    ax.text(0.4, 0.08, label, fontsize=14, color=edge_c,
            ha="left", va="bottom", transform=ax.transAxes, fontweight="bold")
    if annotate:
        ax.text(0.74, 0.08, f"{values.mean():.2f}", fontsize=12, color=edge_c,
                ha="right", va="bottom", transform=ax.transAxes)
        ax.text(0.74, 0.08,
                f"[{values.quantile(0.25):.1f}, {values.median():.1f}, {values.quantile(0.75):.1f}]",
                fontsize=10, color=edge_c, ha="left", va="bottom",
                transform=ax.transAxes)


# =============================================================================
# Gini trend (Fig. 3 c/d)
# =============================================================================

def plot_gini_trend(ax, gini_df: pd.DataFrame, level: str, dist: int, only_all: bool = False):
    """Plot Gini index over years per segment.

    Parameters
    ----------
    gini_df : DataFrame indexed by year, columns = segment names. Each cell is
        the precomputed Gini coefficient (caller computes this in the notebook
        — the formula stays visible there as part of §2.2 of the paper).
    """
    metrics = list(gini_df.columns) if not only_all else ["all"]
    years = gini_df.index

    for m in metrics:
        if m != "all":
            c0, c1 = LOC_COLORS[m]
            ax.plot(years, gini_df[m], label=m, marker="o", ms=4, color=c0,
                    lw=1.5, alpha=0.8)
            ax.text(years[-1], gini_df[m].iloc[-1] - 0.02, m, fontsize=14,
                    color=c1, ha="center", va="top")
        else:
            c0 = LOC_COLORS[m][0] if not only_all else ("yellowgreen" if level == "L2" else "lightpink")
            c1 = LOC_COLORS[m][1] if not only_all else ("seagreen" if level == "L2" else "crimson")
            txt = "TI-acs" if not only_all else level
            ax.plot(years, gini_df[m], label=m, marker="D", ms=6, color=c0,
                    lw=3, alpha=1, zorder=1000)
            ax.text(years[-1], gini_df[m].iloc[-1] + 0.02, txt, fontsize=14,
                    color=c1, ha="center", va="bottom", fontweight="bold", zorder=1100)

    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    if not only_all:
        ax.text(0.88, 0.95, level, fontsize=18, ha="center", va="bottom",
                fontweight="bold", color="dimgrey", transform=ax.transAxes)
    ax.text(0.88, 0.93, f"within {dist} m", fontsize=14, ha="center", va="top",
            color="dimgrey", transform=ax.transAxes)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Gini Coefficient", fontsize=16)


# =============================================================================
# Race CDF (Fig. 4 a/b/a1/b1)
# =============================================================================

def plot_race_cdf(ax, values_per_group: dict[str, pd.Series], mark_stats: bool = False):
    """Empirical CDF of TI-acs across tracts, one curve per dominant-race group.

    Parameters
    ----------
    values_per_group : dict mapping a race key (matching RACE_LABELS) to a 1-D
        Series of tract-level TI-acs values.
    """
    for i, g in enumerate(RACE_LABELS):
        if g not in values_per_group:
            continue
        vals = values_per_group[g]
        ax.ecdf(vals, lw=2, label=RACE_LABELS[g], color=RACE_COLORS[g])
        if mark_stats:
            ax.set_ylim(0, 1.18)
            pct25, med, pct75 = np.percentile(vals, [25, 50, 75])
            y = 1.05 + i * 0.02
            ax.plot([pct25, pct75], [y, y], color=RACE_COLORS[g], lw=4,
                    alpha=0.2, solid_capstyle='butt')
            ax.plot([med], [y], color=RACE_COLORS[g], marker='s', markersize=4, alpha=1)

    if mark_stats:
        ax.axhline(1.02, color='slategrey', lw=0.8, alpha=0.6)
    ax.set_ylabel("CDF", fontsize=14)
    ax.set_xlabel("avg. Accessible Hours", fontsize=14)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


# =============================================================================
# Race regression coefficients (Fig. 4 c/d, Fig. 6)
# =============================================================================

def plot_race_regression_coefs(
    ax,
    coefs_df: pd.DataFrame,
    years,
    x_offset: float = 0,
    legend: bool = True,
    simplified: bool = False,
    ylim: tuple | None = None,
    yticks=None,
):
    """Plot β_r estimates with CI per year for each non-baseline race group.

    Parameters
    ----------
    coefs_df : DataFrame indexed by "{year}-{group}" with columns
        ["coef", "lo", "hi", "p-value"]. Either freshly fit in the notebook
        or loaded from a cached race_regression_I*.xlsx via
        ti_acs.io.load_cached_race_regression.
    years : iterable of integer years to plot.
    """
    groups = list(RACE_LABELS)
    xticks_pos = np.arange(len(years)) + x_offset

    def _errorbar(x, y, **kw):
        _, _, bars = ax.errorbar(x, y, **kw)
        for bar in bars:
            bar.set_alpha(0.3)

    for i, g in enumerate(groups):
        if g == "No-dominant":
            # Phantom points to seed the legend with the "sig" vs "n.s." markers.
            _errorbar([-2], [100], xerr=1, color="dimgrey", fmt='s', ms=5,
                      label=r"est. $\beta_r$ & CI $_{(p<.05)}$")
            _errorbar([-2], [100], xerr=1, color="dimgrey", fmt='s', ms=5, mfc="w",
                      label=r"est. $\beta_r$ & CI $_{(n.s.)}$")
            continue
        ids = [f"{yr}-{g}" for yr in years if f"{yr}-{g}" in coefs_df.index]
        if not ids:
            continue
        y = coefs_df.loc[ids, "coef"].values
        yerr = abs(coefs_df.loc[ids, ["lo", "hi"]].values.T - y[None, :])
        x = np.arange(len(ids)) + x_offset + 0.06 * (i - 1.5)
        sig = (coefs_df.loc[ids, "p-value"] < 0.05).values
        if sig.any():
            _errorbar(x[sig], y[sig], yerr=yerr[:, sig], color=RACE_COLORS[g],
                      fmt='s', ms=5)
        if (~sig).any():
            _errorbar(x[~sig], y[~sig], yerr=yerr[:, ~sig], color=RACE_COLORS[g],
                      fmt='s', ms=5, mfc="w")

    xmin, xmax = xticks_pos.min() - 0.3, xticks_pos.max() + 0.3
    ax.hlines(0, xmin, xmax, color='silver', lw=0.5, alpha=0.5, zorder=-100)
    ax.set_xlim(xmin - 0.2, xmax + 0.2)
    ax.set_ylabel(r"$\beta_r$", fontsize=14)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.set_xticks(xticks_pos)
    ax.set_xticklabels([f"\'{yr % 100}" for yr in years], fontsize=10)
    ax.tick_params(axis='x', length=0)

    if ylim is None:
        ylim = (-10, 4)
    if yticks is None:
        yticks = [-9, -6, -3, 0, 3]
    ax.set_ylim(*ylim)
    ax.set_yticks(yticks)
    ax.tick_params(axis='y', pad=0)

    if legend:
        ax.legend(frameon=False, loc='lower left', fontsize=10,
                  labelcolor="dimgrey", labelspacing=0.2, ncol=2)

    if simplified:
        ax.spines['left'].set_visible(False)
        ax.set_yticks([])
        ax.set_ylabel('')
        ax.vlines(xmin - 0.03, ylim[0], ylim[1], color='silver', lw=0.5, zorder=-100)
        for yv in yticks:
            ax.text(xmin - 0.05, yv, yv, fontsize=8, color="dimgrey",
                    ha='right', va='center')
        ax.tick_params(axis='x', labelsize=8)
