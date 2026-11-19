"""Charts for the industry deep dive (docs/industry_deep_dive.md)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nkeresearch import facts as F
from nkeresearch.deck import ACCENT, BAD, GRID, INK, LIGHT, MUTED


def usd(p: dict, key: str) -> float:
    """Convert a local-currency figure to USD with the snapshot's market-cap FX rate."""
    return p[key] * p["market_cap_usd"] / p["market_cap"]


def charts(snapshot: dict, img: Path) -> None:
    img.mkdir(parents=True, exist_ok=True)
    peers = snapshot["peers"]

    # 1. scale vs profitability vs growth
    fig, ax = plt.subplots(figsize=(10, 6))
    for p in peers:
        x, y = usd(p, "revenue") / 1e9, p["operating_margin"] * 100
        ax.scatter(x, y, s=max(p["market_cap_usd"] / 1e8, 30), alpha=0.6,
                   color=BAD if p["revenue_growth"] < 0 else ACCENT, edgecolor="white")
        ax.annotate(f"{p['name'].split(' (')[0]}\n{p['revenue_growth']:+.0%} q growth", (x, y), fontsize=9,
                    xytext=(8, 4), textcoords="offset points", color=INK)
    ax.set_xscale("log")
    ticks = [3, 5, 10, 20, 50]
    ax.set_xticks(ticks, [str(t) for t in ticks])
    ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_xlabel("Revenue, last twelve months (USD bn, log scale)")
    ax.set_ylabel("Operating margin (%)")
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.grid(color=GRID)
    ax.set_title("Scale is not profitability: the smaller specialists earn higher margins\n"
                 "(bubble = market cap; red = shrinking revenue)", loc="left", fontsize=12)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(img / "industry_scale_margin.png", dpi=120)

    # 2. gross margin ladder
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ps = sorted(peers, key=lambda p: p["gross_margin"])
    ax.barh([p["name"].split(" (")[0] for p in ps], [p["gross_margin"] * 100 for p in ps],
            color=[ACCENT if p["ticker"] == "NKE" else LIGHT for p in ps])
    for i, p in enumerate(ps):
        ax.text(p["gross_margin"] * 100 + 0.5, i, f"{p['gross_margin']:.0%}", va="center", fontsize=9)
    ax.set_xlabel("Gross margin, LTM (%)")
    ax.set_title("Gross margin: premium specialists price above the scale players", loc="left", fontsize=12)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(img / "industry_gross_margin.png", dpi=120)

    # 3. Nike footwear sourcing
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, (title, d) in zip(axes, [("NIKE Brand footwear", F.FOOTWEAR_SOURCING_FY2026),
                                     ("NIKE Brand apparel", F.APPAREL_SOURCING_FY2026)], strict=True):
        ax.pie(d.values(), labels=[f"{k} {v:.0%}" for k, v in d.items()], startangle=90, counterclock=False,
               colors=[ACCENT, "#4A73B5", LIGHT, "#DDDDDD"], wedgeprops={"width": 0.4, "edgecolor": "white"})
        ax.set_title(title, fontsize=12)
    fig.suptitle("Where Nike's products are made, FY2026 (share of units by factory country)", fontsize=12, x=0.02,
                 ha="left")
    fig.tight_layout()
    fig.savefig(img / "industry_sourcing.png", dpi=120)
    plt.close("all")
