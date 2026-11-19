"""10-slide stock pitch (equity analyst to portfolio manager), rendered with matplotlib.

Outputs: outputs/NKE_stock_pitch.pdf (reads on GitHub), outputs/NKE_stock_pitch.pptx (one slide image per
page, for presenting) and docs/img/slide_XX.png previews.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from nkeresearch import facts as F
from nkeresearch import model as m
from nkeresearch.assumptions import COMMON, DRIVERS, VALUATION

INK, MUTED, ACCENT, GOOD, BAD, GRID = "#1A1A1A", "#6B6B6B", "#1F4E99", "#2E7D32", "#C62828", "#E6E6E6"
LIGHT = "#A9BEDF"
W, H = 13.333, 7.5
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "text.parse_math": False,  # dollar signs are currency, not LaTeX
})


def comps_stats(snapshot: dict) -> dict:
    """Peer EV/EBITDA and EV/Sales quartiles (Nike excluded; negative EBITDA excluded), as in Excel."""
    peers = snapshot["peers"][1:]
    ev_ebitda = [p["enterprise_value"] / p["ebitda"] for p in peers if p["ebitda"] and p["ebitda"] > 0]
    ev_sales = [p["enterprise_value"] / p["revenue"] for p in peers]
    q = lambda xs: np.percentile(xs, [25, 50, 75])
    return {"ev_ebitda": q(ev_ebitda), "ev_sales": q(ev_sales)}


def implied_prices(snapshot: dict, df: pd.DataFrame) -> dict:
    nke = snapshot["peers"][0]
    net_cash = df.at["cash", 2026] + df.at["st_investments", 2026] - df.at["total_debt", 2026]
    sh = m.shares_outstanding(snapshot)
    s = comps_stats(snapshot)
    return {
        "EV/EBITDA (peer IQR)": (s["ev_ebitda"] * nke["ebitda"] / 1e6 + net_cash) / sh,
        "EV/Sales (peer IQR)": (s["ev_sales"] * nke["revenue"] / 1e6 + net_cash) / sh,
    }


class Deck:
    def __init__(self, n_total: int):
        self.figs, self.n_total = [], n_total

    def slide(self, title: str, kicker: str = ""):
        fig = plt.figure(figsize=(W, H), facecolor="white")
        fig.text(0.04, 0.925, title, fontsize=24, weight="bold", color=INK, va="center")
        if kicker:
            fig.text(0.04, 0.865, kicker, fontsize=13, color=MUTED, va="center")
        fig.add_artist(plt.Line2D([0.04, 0.96], [0.83, 0.83], color=ACCENT, lw=2))
        n = len(self.figs) + 1
        fig.text(0.04, 0.03, "Nike (NKE) stock pitch | Educational project – not investment advice", fontsize=9,
                 color=MUTED)
        fig.text(0.96, 0.03, f"{n} / {self.n_total}", fontsize=9, color=MUTED, ha="right")
        self.figs.append(fig)
        return fig

    def save(self, pdf: Path, pptx: Path, img_dir: Path):
        img_dir.mkdir(parents=True, exist_ok=True)
        with PdfPages(pdf) as pp:
            for i, fig in enumerate(self.figs, 1):
                pp.savefig(fig)
                fig.savefig(img_dir / f"slide_{i:02d}.png", dpi=110)
        from pptx import Presentation
        from pptx.util import Inches

        prs = Presentation()
        prs.slide_width, prs.slide_height = Inches(W), Inches(H)
        for i in range(1, len(self.figs) + 1):
            s = prs.slides.add_slide(prs.slide_layouts[6])
            s.shapes.add_picture(str(img_dir / f"slide_{i:02d}.png"), 0, 0, prs.slide_width, prs.slide_height)
        prs.save(pptx)
        plt.close("all")


def bullets(fig, x, y, items, width=60, size=13, gap=0.012, color=INK, marker="■"):
    for it in items:
        lines = textwrap.wrap(it, width)
        fig.text(x, y, marker, fontsize=size - 5, color=ACCENT, va="top")
        fig.text(x + 0.018, y, "\n".join(lines), fontsize=size, color=color, va="top", linespacing=1.35)
        y -= (0.043 * len(lines)) * size / 13 + gap
    return y


def kpi(fig, x, y, label, value, color=INK, w=0.2):
    fig.text(x, y, value, fontsize=26, weight="bold", color=color, va="top")
    fig.text(x, y - 0.075, label, fontsize=11, color=MUTED, va="top")


def fy(y):
    return f"FY{str(y)[2:]}{'A' if y <= 2026 else 'E'}"


def build(h: pd.DataFrame, snapshot: dict, out_dir: Path, img_dir: Path) -> dict:
    vals = {s: m.value(h, snapshot, s) for s in ("Bear", "Base", "Bull")}
    base, df = vals["Base"]
    w = m.wacc(snapshot, df.at["total_debt", 2026])
    price = snapshot["price"]
    pt = round(base.per_share)
    rating = m.verdict(pt / price - 1)
    years = list(df.columns)
    rev, ebit = df.loc["revenue"], df.loc["ebit"]
    margin = ebit / rev
    imp = implied_prices(snapshot, df)
    d = Deck(10)

    # 1 ---------------------------------------------------------------- title
    fig = d.slide(f"Nike (NKE): {rating}, 12-month target price ${pt}",
                  f"Equity research pitch to the portfolio manager  |  Priced {snapshot['price_date']}")
    kpi(fig, 0.04, 0.74, "Share price (USD)", f"${price:.2f}")
    kpi(fig, 0.26, 0.74, "Target price, base-case DCF", f"${pt}", ACCENT)
    kpi(fig, 0.48, 0.74, "Upside to target", f"{pt / price - 1:+.0%}", GOOD if pt > price else BAD)
    kpi(fig, 0.70, 0.74, "Market cap (USD bn)", f"{snapshot['peers'][0]['market_cap'] / 1e9:.0f}")
    fig.text(0.04, 0.52, "The call in one sentence", fontsize=15, weight="bold", color=INK)
    bullets(fig, 0.04, 0.47, [
        (f"The market prices Nike as if FY2026's {margin[2026]:.1%} EBIT margin were permanent. "
        f"Our base case only needs a partial recovery to {margin[2031]:.1%} by FY2031, still below the "
        f"{margin[2022]:.1%} of FY2022, to be worth ${pt} a share."),
        (f"Range: bear ${vals['Bear'][0].per_share:.0f} / base ${base.per_share:.0f} / bull "
        f"${vals['Bull'][0].per_share:.0f}. The stock trades near the bottom of its 52-week range "
        f"(${snapshot['week52_low']:.0f}–${snapshot['week52_high']:.0f})."),
    ], width=120, size=14)
    fig.text(0.04, 0.12, "Sources: Nike Form 10-K FY2022–FY2026 (SEC EDGAR XBRL), FRED, Damodaran, yfinance. "
             "Model: outputs/NKE_3statement_DCF.xlsx", fontsize=10, color=MUTED)

    # 2 ---------------------------------------------------------------- thesis
    fig = d.slide("Investment thesis: three reasons the market is too pessimistic",
                  "What we believe that the share price does not")
    cols = [
        ("1. The reset is in the numbers",
         [(f"Inventory is clean: {df.at['inventories', 2026] / df.at['cogs', 2026] * 365:.0f} days of COGS in FY2026 "
          f"vs {df.at['inventories', 2022] / df.at['cogs', 2022] * 365:.0f} in FY2022."),
          "Wholesale is growing again (+6% in FY2026) as Nike re-opens doors it closed in its direct-to-consumer push.",
          f"North America EBIT rose 14% in FY2026 to ${F.EBIT_BY_SEGMENT['North America'][0] / 1e3:.1f}bn."]),
        ("2. Margin recovery is operating leverage, not heroics",
         ["Demand creation and overhead are ~34% of revenue; a return to mid-single-digit growth spreads them.",
          (f"Base case gross margin {DRIVERS['gross_margin']['Base'][-1]:.1%} by FY2031, below the "
          f"{df.at['gross_profit', 2022] / rev[2022]:.1%} reached in FY2022."),
          (f"${F.IMPORT_DUTY_RECOVERY_RECEIVABLE}m receivable for recovery of import duties already on the balance "
          "sheet.")]),
        ("3. Balance sheet funds patience",
         [(f"Net cash of ${(df.at['cash', 2026] + df.at['st_investments', 2026] - df.at['total_debt', 2026]) / 1e3:.1f}bn"
          " at FY2026."),
          (f"Dividend of ${df.at['dividends_paid', 2026] / 1e3:.1f}bn a year covered by free cash flow in every "
          "forecast year."),
          "Buybacks were paused in FY2026 ($0.1bn vs $3.0bn): restarting them is a lever, not a need."]),
    ]
    for i, (head, items) in enumerate(cols):
        x = 0.04 + i * 0.315
        fig.text(x, 0.77, "\n".join(textwrap.wrap(head, 30)), fontsize=14, weight="bold", color=ACCENT, va="top")
        bullets(fig, x, 0.65, items, width=36, size=12)

    # 3 ---------------------------------------------------------------- company overview
    fig = d.slide("Company overview: the world's largest athletic brand",
                  f"FY2026 revenue ${rev[2026] / 1e3:.1f}bn, {F.EMPLOYEES:,} employees, "
                  f"{F.US_SHARE_OF_REVENUE_FY2026:.0%} of sales in the United States")
    ax = fig.add_axes([0.20, 0.12, 0.29, 0.62])
    seg = F.REVENUE_BY_SEGMENT
    names = list(seg)[::-1]
    v26 = [seg[n][0] / 1e3 for n in names]
    v24 = [seg[n][2] / 1e3 for n in names]
    yy = np.arange(len(names))
    ax.barh(yy + 0.2, v24, 0.4, color=LIGHT, label="FY2024")
    ax.barh(yy - 0.2, v26, 0.4, color=ACCENT, label="FY2026")
    ax.set_yticks(yy, names)
    ax.set_xlabel("Revenue (USD bn)")
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("Revenue by segment", loc="left", fontsize=13, color=INK)
    for i, n in enumerate(names):
        ax.text(v26[i] + 0.2, yy[i] - 0.2, f"{seg[n][0] / seg[n][2] - 1:+.0%} vs FY24", va="center", fontsize=9,
                color=MUTED)
    bullets(fig, 0.53, 0.75, [
        (f"Footwear is {F.NIKE_BRAND_BY_PRODUCT_FY2026['Footwear'] / sum(F.NIKE_BRAND_BY_PRODUCT_FY2026.values()):.0%}"
        f" of NIKE Brand sales; Jordan Brand alone is ${F.JORDAN_BRAND[0] / 1e3:.1f}bn."),
        (f"Two channels: wholesale ${F.NIKE_BRAND_BY_CHANNEL['Wholesale'][0] / 1e3:.1f}bn and NIKE Direct "
        f"(own stores and digital) ${F.NIKE_BRAND_BY_CHANNEL['NIKE Direct'][0] / 1e3:.1f}bn."),
        ("Asset-light: nearly all products are made by independent contract manufacturers "
        f"({F.FOOTWEAR_SOURCING_FY2026['Vietnam']:.0%} of footwear in Vietnam)."),
        ("North America is the profit engine: "
        f"{F.EBIT_BY_SEGMENT['North America'][0] / sum(v[0] for v in F.EBIT_BY_SEGMENT.values()):.0%} of segment EBIT."),
        (f"Greater China and Converse are the problem areas: revenue "
        f"{seg['Greater China'][0] / seg['Greater China'][2] - 1:+.0%} and "
        f"{seg['Converse'][0] / seg['Converse'][2] - 1:+.0%} over two years."),
    ], width=58, size=12)
    fig.text(0.53, 0.1, f"Source: {F.SOURCE}", fontsize=9, color=MUTED)

    # 4 ---------------------------------------------------------------- what went wrong
    peak = max(snapshot["price_history"].values())
    fig = d.slide("What went wrong: a margin reset priced as permanent",
                  f"Share price {price / peak - 1:.0%} from its 5-year high while FY2026 revenue is only "
                  f"{rev[2026] / rev[2023] - 1:.0%} below FY2023")
    ax = fig.add_axes([0.06, 0.13, 0.42, 0.6])
    ph = pd.Series(snapshot["price_history"])
    ph.index = pd.to_datetime(ph.index)
    ax.plot(ph.index, ph.values, color=ACCENT, lw=2)
    ax.set_title("NKE monthly share price (USD)", loc="left", fontsize=13)
    ax.grid(axis="y", color=GRID)
    ax2 = fig.add_axes([0.56, 0.13, 0.4, 0.6])
    hy = m.HIST_YEARS
    ax2.plot([fy(y) for y in hy], (df.loc["gross_profit", hy] / rev[hy]) * 100, marker="o", color=ACCENT,
             label="Gross margin")
    ax2.plot([fy(y) for y in hy], margin[hy] * 100, marker="o", color=BAD, label="EBIT margin")
    for y in hy:
        ax2.annotate(f"{margin[y]:.1%}", (fy(y), margin[y] * 100), textcoords="offset points", xytext=(0, -16),
                     ha="center", fontsize=9, color=BAD)
    ax2.set_ylim(0, 50)
    ax2.set_ylabel("% of revenue")
    ax2.legend(frameon=False, loc="center right")
    ax2.grid(axis="y", color=GRID)
    ax2.set_title("Margins, FY2022–FY2026", loc="left", fontsize=13)

    # 5 ---------------------------------------------------------------- catalysts
    fig = d.slide("Catalysts and what we need to believe",
                  "The base case asks for less than Nike delivered in FY2022–FY2024")
    rows = [
        ("Revenue growth FY27–31", " / ".join(f"{x:+.0%}" for x in DRIVERS["revenue_growth"]["Base"]),
         f"FY2022–24 CAGR {(rev[2024] / rev[2022]) ** 0.5 - 1:+.1%}"),
        ("Gross margin FY2031", f"{DRIVERS['gross_margin']['Base'][-1]:.1%}",
         f"FY2022 {df.at['gross_profit', 2022] / rev[2022]:.1%}, FY2026 {df.at['gross_profit', 2026] / rev[2026]:.1%}"),
        ("EBIT margin FY2031", f"{margin[2031]:.1%}", f"FY2022 {margin[2022]:.1%}, FY2026 {margin[2026]:.1%}"),
        ("Capex, % of revenue", f"{COMMON['capex_pct']:.1%}", "FY2022–26 average 1.6%"),
        ("Terminal growth", f"{VALUATION['terminal_growth']:.1%}", "Below long-run US nominal GDP"),
    ]
    fig.text(0.04, 0.76, "Driver", fontsize=12, weight="bold", color=MUTED)
    fig.text(0.27, 0.76, "Base case", fontsize=12, weight="bold", color=MUTED)
    fig.text(0.56, 0.76, "Track record", fontsize=12, weight="bold", color=MUTED)
    for i, (a, b, c) in enumerate(rows):
        y = 0.70 - i * 0.075
        fig.text(0.04, y, a, fontsize=12, color=INK)
        fig.text(0.27, y, b, fontsize=12, color=ACCENT, weight="bold")
        fig.text(0.56, y, c, fontsize=12, color=INK)
    fig.text(0.04, 0.27, "Catalysts (next 12 months)", fontsize=14, weight="bold", color=INK)
    bullets(fig, 0.04, 0.22, [
        "Quarterly results showing gross-margin expansion as clearance and discounting fall away.",
        "Wholesale order books for the next seasons; reacceleration of NIKE Direct as full-price selling returns.",
        "Restart of buybacks (bull case) and cash recovery of import duties.",
    ], width=130, size=12)

    # 6 ---------------------------------------------------------------- financial forecast
    fig = d.slide("Base-case forecast: three linked statements",
                  "USD millions, fiscal years ending 31 May. The balance sheet balances in every year. Full model: outputs/NKE_3statement_DCF.xlsx")
    ax = fig.add_axes([0.05, 0.40, 0.9, 0.38])
    ax.axis("off")
    fcf = df.loc["cfo"] - df.loc["capex"]
    show = [2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031]
    table = [
        ["Revenue"] + [f"{rev[y]:,.0f}" for y in show],
        ["Growth"] + [f"{rev[y] / rev[y - 1] - 1:+.1%}" for y in show],
        ["Gross margin"] + [f"{df.at['gross_profit', y] / rev[y]:.1%}" for y in show],
        ["EBIT"] + [f"{ebit[y]:,.0f}" for y in show],
        ["EBIT margin"] + [f"{margin[y]:.1%}" for y in show],
        ["Net income"] + [f"{df.at['net_income', y]:,.0f}" for y in show],
        ["Diluted EPS (USD)"] + [f"{df.at['net_income', y] / df.at['diluted_shares', y]:.2f}" for y in show],
        ["Free cash flow (CFO – capex)"] + [f"{fcf[y]:,.0f}" for y in show],
        ["Cash, end of year"] + [f"{df.at['cash', y]:,.0f}" for y in show],
        ["Balance check"] + [f"{abs(df.at['balance_check', y]):.0f}" for y in show],
    ]
    t = ax.table(cellText=table, colLabels=[""] + [fy(y) for y in show], loc="upper left", cellLoc="right",
                 colLoc="right", colWidths=[0.22] + [0.0975] * len(show))
    t.auto_set_font_size(False)
    t.set_fontsize(11)
    t.scale(1, 1.55)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor(GRID)
        if r == 0:
            cell.set_text_props(weight="bold", color="white")
            cell.set_facecolor(INK if c == 0 or show[c - 1] <= 2026 else ACCENT)
        if c == 0:
            cell.set_text_props(ha="left")
            cell._loc = "left"
    ax3 = fig.add_axes([0.07, 0.11, 0.86, 0.17])
    ax3.bar([fy(y) for y in years], rev / 1e3, color=[LIGHT if y <= 2026 else ACCENT for y in years])
    ax3.set_ylabel("Revenue, USD bn")
    ax4 = ax3.twinx()
    ax4.plot([fy(y) for y in years], margin * 100, color=BAD, marker="o")
    ax4.set_ylabel("EBIT margin %", color=BAD)
    ax4.spines["top"].set_visible(False)

    # 7 ---------------------------------------------------------------- DCF
    fig = d.slide(f"DCF: ${base.per_share:.2f} per share in the base case",
                  f"FCFF discounted at a {w.wacc:.2%} WACC, Gordon terminal value at "
                  f"{VALUATION['terminal_growth']:.1%} growth")
    wacc_rows = [
        ("Risk-free (US 10Y, FRED)", f"{w.rf:.2%}"), ("Beta (2y weekly, Blume-adjusted)", f"{w.beta:.2f}"),
        ("Equity risk premium (Damodaran)", f"{w.erp:.2%}"), ("Cost of equity", f"{w.ke:.2%}"),
        ("After-tax cost of debt", f"{w.kd_after_tax:.2%}"), ("Debt / (debt + equity)", f"{w.weight_debt:.1%}"),
        ("WACC", f"{w.wacc:.2%}"),
    ]
    fig.text(0.04, 0.76, "Cost of capital", fontsize=14, weight="bold", color=INK)
    for i, (a, b) in enumerate(wacc_rows):
        y = 0.70 - i * 0.05
        fig.text(0.04, y, a, fontsize=11.5, color=INK, weight="bold" if a == "WACC" else "normal")
        fig.text(0.30, y, b, fontsize=11.5, color=ACCENT, ha="right", weight="bold")
    cash = df.at["cash", 2026] + df.at["st_investments", 2026]
    bridge = [
        ("PV of FCFF FY27–31", base.ev * (1 - base.pv_tv_share)), ("PV of terminal value", base.ev * base.pv_tv_share),
        ("Enterprise value", base.ev), ("+ Cash & investments", cash), ("– Debt", -df.at["total_debt", 2026]),
        ("Equity value", base.equity),
    ]
    fig.text(0.04, 0.30, "EV to equity (USD m)", fontsize=14, weight="bold", color=INK)
    for i, (a, b) in enumerate(bridge):
        y = 0.25 - i * 0.033
        bold = a in ("Enterprise value", "Equity value")
        fig.text(0.04, y, a, fontsize=10.5, color=INK, weight="bold" if bold else "normal")
        fig.text(0.30, y, f"{b:,.0f}", fontsize=10.5, color=INK, ha="right", weight="bold" if bold else "normal")
    ax = fig.add_axes([0.42, 0.17, 0.53, 0.56])
    ws_ = [w.wacc + x for x in (-0.01, -0.005, 0, 0.005, 0.01)]
    gs_ = [VALUATION["terminal_growth"] + x for x in (-0.01, -0.005, 0, 0.005, 0.01)]
    grid = np.array([[m.value(h, snapshot, "Base", wv, gv)[0].per_share for gv in gs_] for wv in ws_])
    ax.imshow(grid - price, cmap="RdYlGn", vmin=-abs(grid - price).max(), vmax=abs(grid - price).max(),
              aspect="auto")
    for i in range(5):
        for j in range(5):
            ax.text(j, i, f"${grid[i, j]:.0f}", ha="center", va="center", fontsize=11,
                    weight="bold" if (i, j) == (2, 2) else "normal")
    ax.set_xticks(range(5), [f"{g:.1%}" for g in gs_])
    ax.set_yticks(range(5), [f"{x:.1%}" for x in ws_])
    ax.set_xlabel("Terminal growth")
    ax.set_ylabel("WACC")
    ax.set_title(f"Value per share sensitivity (green = above ${price:.2f} price)", loc="left", fontsize=12)
    fig.text(0.42, 0.065, f"Terminal value = {base.pv_tv_share:.0%} of EV; implied exit multiple "
             f"{base.tv / df.at['ebitda', 2031]:.1f}x FY2031 EBITDA.\nStock-based compensation is treated as a "
             "cash cost (not added back).", fontsize=10, color=MUTED)

    # 8 ---------------------------------------------------------------- comps + football field
    fig = d.slide("Cross-checks: trading comparables and valuation range",
                  "Comps are on depressed trailing earnings, so they frame the floor rather than the target")
    peers = snapshot["peers"]
    ax = fig.add_axes([0.04, 0.12, 0.42, 0.62])
    ax.axis("off")
    rows = []
    for p in peers:
        eve = p["enterprise_value"] / p["ebitda"] if p["ebitda"] and p["ebitda"] > 0 else None
        rows.append([p["name"].split(" (")[0], f"{p['market_cap_usd'] / 1e9:.1f}",
                     f"{p['enterprise_value'] / p['revenue']:.2f}x", f"{eve:.1f}x" if eve else "n.m.",
                     f"{p['operating_margin']:.0%}", f"{p['revenue_growth']:+.0%}"])
    s = comps_stats(snapshot)
    rows.append(["Peer median", "", f"{s['ev_sales'][1]:.2f}x", f"{s['ev_ebitda'][1]:.1f}x", "", ""])
    t = ax.table(cellText=rows, colLabels=["Company", "Mkt cap\n$bn", "EV/\nSales", "EV/\nEBITDA", "Op.\nmargin",
                                           "Rev.\ngrowth"], loc="upper left", cellLoc="right", colLoc="right",
                 colWidths=[0.28, 0.15, 0.14, 0.15, 0.14, 0.14])
    t.auto_set_font_size(False)
    t.set_fontsize(10)
    t.scale(1, 1.6)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor(GRID)
        if r == 0:
            cell.set_text_props(weight="bold", color="white")
            cell.set_facecolor(INK)
            cell.set_height(cell.get_height() * 1.8)
        if r == 1 or r == len(rows):
            cell.set_text_props(weight="bold")
    ax.text(0, -0.02, "LTM, yfinance; revenue growth = latest quarter y/y. EV = market cap + debt (incl. leases) – cash. Puma n.m.",
            fontsize=8.5, color=MUTED, transform=ax.transAxes, va="top")
    ax = fig.add_axes([0.66, 0.14, 0.30, 0.56])
    bars = {
        "52-week trading range": (snapshot["week52_low"], snapshot["week52_high"]),
        "EV/Sales (peer IQR)": (imp["EV/Sales (peer IQR)"][0], imp["EV/Sales (peer IQR)"][2]),
        "EV/EBITDA (peer IQR)": (imp["EV/EBITDA (peer IQR)"][0], imp["EV/EBITDA (peer IQR)"][2]),
        "DCF bear – bull": (vals["Bear"][0].per_share, vals["Bull"][0].per_share),
    }
    for i, (k, (lo, hi)) in enumerate(bars.items()):
        ax.barh(i, hi - lo, left=lo, color=ACCENT if "DCF" in k else LIGHT, height=0.5)
        ax.text(lo - 1, i, f"${lo:.0f}", ha="right", va="center", fontsize=9)
        ax.text(hi + 1, i, f"${hi:.0f}", ha="left", va="center", fontsize=9)
    ax.axvline(price, color=BAD, lw=1.5, ls="--")
    ax.axvline(pt, color=GOOD, lw=1.5)
    ax.text(price, -0.6, f"Price ${price:.0f} ", color=BAD, ha="right", fontsize=9)
    ax.text(pt, -0.6, f" Target ${pt}", color=GOOD, ha="left", fontsize=9)
    ax.set_yticks(range(len(bars)), list(bars))
    ax.set_xlabel("USD per share")
    ax.set_xlim(0, max(hi for _, hi in bars.values()) * 1.15)
    ax.set_ylim(-0.8, len(bars) - 0.5)
    fig.text(0.50, 0.74, "Football field (USD per share)", fontsize=13, color=INK)

    # 9 ---------------------------------------------------------------- risks
    fig = d.slide("Key risks and how we would know we are wrong",
                  f"Bear case: ${vals['Bear'][0].per_share:.0f} per share "
                  f"({vals['Bear'][0].upside:+.0%}) – growth stalls and gross margin stays near 41%")
    risks = [
        ("Brand heat keeps moving to challengers",
         "On, Hoka (Deckers) and Asics are growing double digits in running.",
         "Watch: NIKE Direct and running category growth each quarter."),
        ("Tariffs and sourcing concentration",
         (f"{F.FOOTWEAR_SOURCING_FY2026['Vietnam']:.0%} of footwear made in Vietnam; "
         f"top 4 manufacturers make {F.TOP4_FOOTWEAR_MANUFACTURERS_SHARE:.0%} of footwear."),
         "Watch: gross-margin bridge in the 10-Q, duty recoveries."),
        ("Greater China does not recover",
         (f"Revenue {F.REVENUE_BY_SEGMENT['Greater China'][0] / F.REVENUE_BY_SEGMENT['Greater China'][2] - 1:+.0%}"
         " in two years; local brands (Anta, Li Ning) gaining share."),
         "Watch: China EBIT margin (22% in FY2026)."),
        ("Wholesale concentration",
         f"Top 3 US customers = {F.TOP3_US_CUSTOMERS_SHARE_OF_US_SALES:.0%} of US sales.",
         "Watch: partner inventory and order books."),
        ("Valuation depends on the terminal value",
         (f"{base.pv_tv_share:.0%} of EV is terminal value; ±1pt WACC moves value by "
         f"${grid[0, 2] - grid[2, 2]:.0f}/${grid[2, 2] - grid[4, 2]:.0f}."),
         "Mitigant: even the bear case keeps a positive FCF."),
    ]
    fig.text(0.04, 0.77, "Risk", fontsize=12, weight="bold", color=MUTED)
    fig.text(0.30, 0.77, "Evidence", fontsize=12, weight="bold", color=MUTED)
    fig.text(0.66, 0.77, "Signpost", fontsize=12, weight="bold", color=MUTED)
    for i, (a, b, c) in enumerate(risks):
        y = 0.71 - i * 0.12
        fig.text(0.04, y, "\n".join(textwrap.wrap(a, 28)), fontsize=12, weight="bold", color=INK, va="top")
        fig.text(0.30, y, "\n".join(textwrap.wrap(b, 52)), fontsize=11, color=INK, va="top")
        fig.text(0.66, y, "\n".join(textwrap.wrap(c, 42)), fontsize=11, color=MUTED, va="top")

    # 10 --------------------------------------------------------------- recommendation
    fig = d.slide(f"Recommendation: {rating} with a ${pt} target price",
                  "Asymmetric: limited downside to the bear case, large upside if margins normalise")
    ax = fig.add_axes([0.06, 0.15, 0.45, 0.58])
    sc = ["Bear", "Base", "Bull"]
    ps = [vals[s][0].per_share for s in sc]
    ax.bar(sc, ps, color=[BAD, ACCENT, GOOD], width=0.55)
    ax.axhline(price, color=INK, ls="--", lw=1)
    ax.text(-0.4, price + 0.6, f"Price ${price:.2f}", va="bottom", ha="left", fontsize=10)
    for i, v in enumerate(ps):
        ax.text(i, v + 1, f"${v:.0f}\n({v / price - 1:+.0%})", ha="center", fontsize=11, weight="bold")
    ax.set_ylim(0, max(ps) * 1.25)
    ax.set_ylabel("Value per share (USD)")
    ax.set_title("DCF value by scenario", loc="left", fontsize=13)
    bullets(fig, 0.56, 0.74, [
        f"{rating} NKE, target ${pt} ({pt / price - 1:+.0%}) from the base-case DCF.",
        "Position sizing: start at half weight; add on evidence of gross-margin expansion.",
        (f"Exit / review if the gross margin is below {DRIVERS['gross_margin']['Bear'][1]:.0%} for two consecutive "
        "quarters, which is the bear case."),
        "Every assumption is a blue cell in the Excel model and can be challenged live.",
    ], width=48, size=13)
    d.save(out_dir / "NKE_stock_pitch.pdf", out_dir / "NKE_stock_pitch.pptx", img_dir)
    return {"price": price, "target": pt, "rating": rating, "upside": pt / price - 1,
            "scenarios": {s: round(vals[s][0].per_share, 2) for s in sc}, "wacc": w.wacc,
            "implied": {k: [round(x, 2) for x in v] for k, v in imp.items()}}
