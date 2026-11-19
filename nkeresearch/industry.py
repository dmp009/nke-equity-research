"""Charts for the industry deep dive (docs/industry_deep_dive.md), in the deck's palette."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nkeresearch import facts as F
from nkeresearch.style import BLUE, INK, LINE, MUTED, ORANGE, RED, TINT, hexc

plt.rcParams.update({
    "font.family": ["Arial", "DejaVu Sans"], "font.size": 11, "text.color": hexc(INK),
    "axes.labelcolor": hexc(MUTED), "xtick.color": hexc(MUTED), "ytick.color": hexc(MUTED),
    "axes.edgecolor": hexc(LINE), "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlelocation": "left", "axes.titlesize": 14, "axes.titleweight": "bold", "axes.titlepad": 14,
    "text.parse_math": False, "savefig.facecolor": "white",
})


def usd(p: dict, key: str) -> float:
    """Convert a local-currency figure to USD with the snapshot's market-cap FX rate."""
    return p[key] * p["market_cap_usd"] / p["market_cap"]


def _short(p: dict) -> str:
    return p["name"].split(" (")[0]


def charts(snapshot: dict, img: Path) -> None:
    img.mkdir(parents=True, exist_ok=True)
    peers = snapshot["peers"]

    # 1. scale vs profitability; growth is written in the label, colour marks Nike only
    fig, ax = plt.subplots(figsize=(10, 6))
    for p in peers:
        x, y = usd(p, "revenue") / 1e9, p["operating_margin"] * 100
        nke = p["ticker"] == "NKE"
        ax.scatter(x, y, s=max(p["market_cap_usd"] / 1e8, 40), color=hexc(ORANGE if nke else BLUE),
                   alpha=0.9 if nke else 0.55, edgecolor="white", linewidth=2, zorder=3)
        g = f"{p['revenue_growth']:+.0%}".replace("-", "−")
        ax.annotate(f"{_short(p)}  ", (x, y), xytext=(10, 2), textcoords="offset points", fontsize=11,
                    fontweight="bold", color=hexc(INK))
        ax.annotate(f"revenue {g} y/y", (x, y), xytext=(10, -12), textcoords="offset points", fontsize=9,
                    color=hexc(RED if p["revenue_growth"] < 0 else MUTED))
    ax.set_xscale("log")
    ticks = [3, 5, 10, 20, 50]
    ax.set_xticks(ticks, [str(t) for t in ticks])
    ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_xlabel("Revenue, last twelve months (USD bn, log scale)")
    ax.set_ylabel("Operating margin (%)")
    ax.axhline(0, color=hexc(MUTED), lw=0.8)
    ax.grid(color=hexc(LINE), lw=0.8)
    ax.set_axisbelow(True)
    ax.set_title("Scale is not profitability: the specialists earn higher margins")
    ax.text(0, 1.0, "Bubble size = market cap. Nike in orange.", transform=ax.transAxes, fontsize=10,
            color=hexc(MUTED), va="bottom")
    fig.tight_layout()
    fig.savefig(img / "industry_scale_margin.png", dpi=150)

    # 2. gross margin ladder
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ps = sorted(peers, key=lambda p: p["gross_margin"])
    ax.barh([_short(p) for p in ps], [p["gross_margin"] * 100 for p in ps], height=0.62,
            color=[hexc(ORANGE if p["ticker"] == "NKE" else BLUE) for p in ps])
    for i, p in enumerate(ps):
        ax.text(p["gross_margin"] * 100 + 0.8, i, f"{p['gross_margin']:.0%}", va="center", fontsize=10,
                color=hexc(INK), fontweight="bold" if p["ticker"] == "NKE" else "normal")
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    ax.set_title("Gross margin, last twelve months: Nike sits at the bottom of the ladder")
    fig.tight_layout()
    fig.savefig(img / "industry_gross_margin.png", dpi=150)

    # 3. Nike sourcing: one bar per product line, segments labelled in place
    fig, ax = plt.subplots(figsize=(10, 3.4))
    shades = {"Vietnam": ORANGE, "China": BLUE, "Indonesia": "8FB0DE", "Cambodia": "8FB0DE", "Other": "D1D5DB"}
    rows = [("Footwear", F.FOOTWEAR_SOURCING_FY2026), ("Apparel", F.APPAREL_SOURCING_FY2026)]
    for i, (_, d) in enumerate(rows):
        left = 0.0
        for j, (k, v) in enumerate(d.items()):
            ax.barh(i, v * 100, left=left, height=0.58, color=hexc(shades[k]), edgecolor="white", linewidth=2)
            if v >= 0.08:
                dark = shades[k] not in (ORANGE, BLUE)
                ax.text(left + v * 50, i, f"{k}\n{v:.0%}", ha="center", va="center", fontsize=10,
                        color=hexc(INK if dark else "FFFFFF"), fontweight="bold")
            left += v * 100
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=12)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    ax.set_facecolor(hexc(TINT) + "00")
    ax.set_title("Where NIKE Brand products are made, FY2026 (share of units by factory country)")
    fig.tight_layout()
    fig.savefig(img / "industry_sourcing.png", dpi=150)
    plt.close("all")
