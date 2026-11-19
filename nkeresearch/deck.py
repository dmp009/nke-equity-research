"""10-slide stock pitch (equity analyst to portfolio manager) as a native PowerPoint deck.

Charts are native PowerPoint charts (editable, data inside), tables are native tables and every
slide carries speaker notes with the pitch script. outputs/NKE_stock_pitch.pdf and the PNG previews
in docs/img/ are exported from PowerPoint by scripts/export_pdf.py (macOS, PowerPoint installed).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import (
    XL_CHART_TYPE,
    XL_LABEL_POSITION,
    XL_LEGEND_POSITION,
    XL_MARKER_STYLE,
    XL_TICK_LABEL_POSITION,
)
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from nkeresearch import facts as F
from nkeresearch import model as m
from nkeresearch.assumptions import COMMON, DRIVERS, VALUATION
from nkeresearch.style import (
    BLUE,
    BODY_FONT,
    DARK,
    DARK_MUTED,
    GREEN,
    HEAD_FONT,
    INK,
    LINE,
    MUTED,
    ORANGE,
    RED,
    TINT,
    WARM,
    WHITE,
)

SW, SH = 13.333, 7.5
LM = 0.6  # left margin
CW = SW - 2 * LM  # content width
C_NS = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"


def rgb(c: str) -> RGBColor:
    return RGBColor.from_string(c)


# --------------------------------------------------------------------------- valuation helpers
def comps_stats(snapshot: dict) -> dict:
    """Peer EV/EBITDA and EV/Sales quartiles (Nike excluded; negative EBITDA excluded), as in Excel."""
    peers = snapshot["peers"][1:]
    ev_ebitda = [p["enterprise_value"] / p["ebitda"] for p in peers if p["ebitda"] and p["ebitda"] > 0]
    ev_sales = [p["enterprise_value"] / p["revenue"] for p in peers]
    # numpy's default percentile = Excel QUARTILE (inclusive)
    return {"ev_ebitda": np.percentile(ev_ebitda, [25, 50, 75]), "ev_sales": np.percentile(ev_sales, [25, 50, 75])}


def implied_prices(snapshot: dict, df: pd.DataFrame) -> dict:
    nke = snapshot["peers"][0]
    net_cash = df.at["cash", 2026] + df.at["st_investments", 2026] - df.at["total_debt", 2026]
    sh = m.shares_outstanding(snapshot)
    s = comps_stats(snapshot)
    return {
        "EV/EBITDA (peer IQR)": (s["ev_ebitda"] * nke["ebitda"] / 1e6 + net_cash) / sh,
        "EV/Sales (peer IQR)": (s["ev_sales"] * nke["revenue"] / 1e6 + net_cash) / sh,
    }


# --------------------------------------------------------------------------- drawing primitives
def text(slide, x, y, w, h, content, size=14, bold=False, color=INK, font=BODY_FONT, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, italic=False, name=None, spacing=None):
    """content: str, or list of paragraphs; a paragraph is str or a list of (text, {opts}) runs."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = content if isinstance(content, list) else [content]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.space_after = Pt(spacing)
        runs = para if isinstance(para, list) else [(para, {})]
        for t, o in runs:
            r = p.add_run()
            r.text = t
            f = r.font
            f.name = o.get("font", font)
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", italic)
            f.color.rgb = rgb(o.get("color", color))
    return tb


def box(slide, x, y, w, h, fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06, name=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    s.line.fill.background()
    s.shadow.inherit = False
    if name:
        s.name = name
    return s


def badge(slide, x, y, label, d=0.46, fill=ORANGE, color=WHITE, size=14):
    """Numbered circle: the deck's visual motif."""
    c = box(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    tf = c.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.size, r.font.bold, r.font.name = Pt(size), True, HEAD_FONT
    r.font.color.rgb = rgb(color)
    return c


def _plain(ln):
    st = ln._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if st is not None:
        ln._element.remove(st)
    return ln


def hline(slide, x1, y, x2, color=LINE, width=0.75):
    ln = _plain(slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y), Inches(x2), Inches(y)))
    ln.line.color.rgb, ln.line.width = rgb(color), Pt(width)
    return ln


def vline(slide, x, y1, y2, color, width=2.0, dash=False):
    ln = _plain(slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y1), Inches(x), Inches(y2)))
    ln.line.color.rgb, ln.line.width = rgb(color), Pt(width)
    if dash:
        ln.line.dash_style = 4  # MSO_LINE_DASH_STYLE.DASH
    return ln


def stat(slide, x, y, w, value, label, color=INK, vsize=36, lsize=12, lcolor=MUTED):
    text(slide, x, y, w, vsize / 72 + 0.15, value, size=vsize, bold=True, color=color, font=HEAD_FONT)
    text(slide, x, y + vsize / 72 + 0.12, w, 0.6, label, size=lsize, color=lcolor)


def style_chart(chart, legend=False, size=11, label_color=MUTED, grid=LINE, title=None):
    chart.font.size = Pt(size)
    chart.font.name = BODY_FONT
    chart.font.color.rgb = rgb(label_color)
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(size)
    va = chart.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb(grid)
    va.major_gridlines.format.line.width = Pt(0.75)
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(size)
    va.tick_labels.font.color.rgb = rgb(label_color)
    ca = chart.category_axis
    ca.format.line.color.rgb = rgb(grid)
    ca.tick_labels.font.size = Pt(size)
    ca.tick_labels.font.color.rgb = rgb(label_color)
    ca.has_major_gridlines = False
    if title:
        chart.has_title = True
        chart.chart_title.text_frame.text = title
        r = chart.chart_title.text_frame.paragraphs[0].runs[0]
        r.font.size, r.font.bold, r.font.color.rgb = Pt(13), True, rgb(INK)
    else:
        chart.has_title = False


def fill_series(series, color):
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = rgb(color)


def data_labels(plot, fmt, size=11, color=INK, pos=XL_LABEL_POSITION.OUTSIDE_END):
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = fmt, False
    dl.font.size, dl.font.color.rgb = Pt(size), rgb(color)
    dl.position = pos


def table(slide, x, y, w, rows, col_w, size=12, row_h=0.36, highlight_cols=(), bold_rows=()):
    nr, nc = len(rows), len(rows[0])
    gt = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr)).table
    for j, cw in enumerate(col_w):
        gt.columns[j].width = Inches(cw)
    for i in range(nr):
        gt.rows[i].height = Inches(row_h)
        for j in range(nc):
            cell = gt.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if i == 0:
                cell.fill.fore_color.rgb = rgb(ORANGE if j in highlight_cols else INK)
            else:
                cell.fill.fore_color.rgb = rgb("FFF4EE" if j in highlight_cols else (TINT if i % 2 == 0 else WHITE))
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.RIGHT
            r = p.add_run()
            r.text = str(rows[i][j])
            r.font.size = Pt(size)
            r.font.name = BODY_FONT
            r.font.bold = i == 0 or i in bold_rows
            r.font.color.rgb = rgb(WHITE if i == 0 else INK)
    return gt


class Deck:
    def __init__(self, total: int):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(SW), Inches(SH)
        self.total, self.n = total, 0

    def slide(self, kicker: str, title: str, dark: bool = False, notes: str = ""):
        self.n += 1
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(DARK if dark else WHITE)
        text(s, LM, 0.42, CW, 0.3, kicker.upper(), size=12, bold=True, color=ORANGE, font=HEAD_FONT, name="Kicker")
        if title:
            text(s, LM, 0.72, CW, 0.7, title, size=32, bold=True, color=WHITE if dark else INK, font=HEAD_FONT,
                 name="Title")
        foot = DARK_MUTED if dark else MUTED
        text(s, LM, SH - 0.42, 9, 0.25, "Nike (NKE) equity research pitch  ·  Educational project, not investment "
             "advice", size=10, color=foot)
        text(s, SW - LM - 1, SH - 0.42, 1, 0.25, f"{self.n} / {self.total}", size=10, color=foot,
             align=PP_ALIGN.RIGHT)
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s


def fy(y: int) -> str:
    return f"FY{str(y)[2:]}{'A' if y <= 2026 else 'E'}"


# --------------------------------------------------------------------------- the deck
def build(h: pd.DataFrame, snapshot: dict, out_dir: Path) -> dict:
    vals = {s: m.value(h, snapshot, s) for s in ("Bear", "Base", "Bull")}
    base, df = vals["Base"]
    w = m.wacc(snapshot, df.at["total_debt", 2026])
    price = snapshot["price"]
    pt = round(base.per_share)
    up = pt / price - 1
    rating = m.verdict(up)
    rev, ebit = df.loc["revenue"], df.loc["ebit"]
    margin = ebit / rev
    gm = df.loc["gross_profit"] / rev
    imp = implied_prices(snapshot, df)
    net_cash = df.at["cash", 2026] + df.at["st_investments", 2026] - df.at["total_debt", 2026]
    peak = max(snapshot["price_history"].values())
    d = Deck(10)

    # 1 ------------------------------------------------------------------ title (dark)
    s = d.slide(f"Equity research  ·  Consumer discretionary  ·  "
                f"{date.fromisoformat(snapshot['price_date']):%d %B %Y}", "", dark=True, notes=(
                    f"Our call is {rating} on Nike with a ${pt} target, {up:+.0%} from ${price:.2f}. The market "
                    f"is pricing the FY2026 EBIT margin of {margin[2026]:.1%} as if it were permanent. We think it "
                    "is a reset, and the next slides show what has to be true for that."))
    text(s, LM, 1.3, 9, 1.1, "Nike (NKE)", size=60, bold=True, color=WHITE, font=HEAD_FONT)
    text(s, LM, 2.45, 10, 0.6, "A margin reset the market is pricing as permanent", size=24, color=DARK_MUTED)
    box(s, LM, 3.3, 2.3, 0.62, fill=ORANGE, radius=0.5)
    text(s, LM, 3.3, 2.3, 0.62, f"{rating}  ·  ${pt}", size=22, bold=True, color=WHITE, font=HEAD_FONT,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    stats = [(f"${price:.2f}", "Share price"), (f"${pt}", "Target price, base-case DCF"),
             (f"{up:+.0%}", "Upside to target"),
             (f"${snapshot['peers'][0]['market_cap'] / 1e9:.0f}bn", "Market capitalisation")]
    for i, (v, lab) in enumerate(stats):
        x = LM + i * 3.07
        box(s, x, 4.55, 2.85, 1.6, fill="1C1F24", radius=0.08)
        stat(s, x + 0.3, 4.78, 2.4, v, lab, color=ORANGE if i == 2 else WHITE, vsize=36, lsize=13,
             lcolor=DARK_MUTED)
    text(s, LM, 6.5, CW, 0.3, "Sources: Nike Form 10-K FY2022–FY2026 (SEC EDGAR), FRED, Damodaran, Yahoo Finance. "
         "Model: NKE_3statement_DCF.xlsx", size=10, color=DARK_MUTED)

    # 2 ------------------------------------------------------------------ thesis
    s = d.slide("01  ·  Investment thesis", "Three reasons the market is too pessimistic", notes=(
        "First, the reset is already visible in the numbers: inventory is back to normal and wholesale is "
        "growing again. Second, margin recovery is mostly operating leverage on a fixed cost base. Third, "
        "the balance sheet lets Nike be patient."))
    inv26 = df.at["inventories", 2026] / df.at["cogs", 2026] * 365
    inv22 = df.at["inventories", 2022] / df.at["cogs", 2022] * 365
    sga = (df.at["demand_creation", 2026] + df.at["operating_overhead", 2026]) / rev[2026]
    cards = [
        ("The reset is in the numbers", [
            f"Inventory down to {inv26:.0f} days of COGS, from {inv22:.0f} in FY2022",
            "Wholesale revenue +6% in FY2026 as Nike re-opens partner doors",
            f"North America EBIT +14% to ${F.EBIT_BY_SEGMENT['North America'][0] / 1e3:.1f}bn"]),
        ("Margin recovery is operating leverage", [
            f"Demand creation and overhead are {sga:.0%} of revenue and largely fixed",
            f"Gross margin {DRIVERS['gross_margin']['Base'][-1]:.1%} by FY2031, below FY2022's {gm[2022]:.1%}",
            f"${F.IMPORT_DUTY_RECOVERY_RECEIVABLE}m of import duties to be recovered"]),
        ("The balance sheet funds patience", [
            f"Net cash of ${net_cash / 1e3:.1f}bn at FY2026",
            f"${df.at['dividends_paid', 2026] / 1e3:.1f}bn dividend covered by free cash flow every year",
            "Buybacks paused ($0.1bn vs $3.0bn): a lever, not a need"]),
    ]
    cw_, gap = 3.85, 0.33
    for i, (head, items) in enumerate(cards):
        x = LM + i * (cw_ + gap)
        box(s, x, 1.75, cw_, 3.6)
        badge(s, x + 0.3, 2.0, f"{i + 1}")
        text(s, x + 0.3, 2.65, cw_ - 0.6, 0.75, head, size=18, bold=True, font=HEAD_FONT)
        text(s, x + 0.3, 3.45, cw_ - 0.6, 1.85, items, size=14, spacing=8)
    box(s, LM, 5.65, CW, 1.0, fill=WARM)
    text(s, LM + 0.35, 5.65, CW - 0.7, 1.0, [[
        ("What we need to believe: ", {"bold": True, "color": ORANGE}),
        ((f"EBIT margin back to {margin[2031]:.1%} by FY2031, still below the {margin[2022]:.1%} Nike "
         "earned in FY2022."), {})]], size=17, anchor=MSO_ANCHOR.MIDDLE)

    # 3 ------------------------------------------------------------------ company overview
    s = d.slide("02  ·  Company", "The largest athletic brand, with two weak spots", notes=(
        "Nike sold $46.4bn in FY2026. North America is half of segment profit. Greater China and Converse "
        "shrank most; both are small enough that the group recovery does not depend on them."))
    seg = F.REVENUE_BY_SEGMENT
    keys = list(seg)
    cd = CategoryChartData()
    cd.categories = ["North America", "EMEA", "Greater China", "APLA", "Converse"]
    cd.add_series("FY2024", [seg[k][2] / 1e3 for k in keys])
    cd.add_series("FY2026", [seg[k][0] / 1e3 for k in keys])
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(LM), Inches(1.7), Inches(7.2), Inches(4.85),
                            cd).chart
    style_chart(ch, legend=True, title="Revenue by segment, USD bn")
    fill_series(ch.plots[0].series[0], BLUE)
    fill_series(ch.plots[0].series[1], ORANGE)
    ch.plots[0].gap_width, ch.plots[0].overlap = 60, -8
    data_labels(ch.plots[0], "0.0", size=10)
    ch.value_axis.tick_label_position = XL_TICK_LABEL_POSITION.NONE
    ch.value_axis.has_major_gridlines = False
    callouts = [
        (f"{F.NIKE_BRAND_BY_PRODUCT_FY2026['Footwear'] / sum(F.NIKE_BRAND_BY_PRODUCT_FY2026.values()):.0%}",
         "of NIKE Brand sales are footwear", ORANGE),
        (f"${F.JORDAN_BRAND[0] / 1e3:.1f}bn", "Jordan Brand revenue, a business on its own", ORANGE),
        (f"{F.EBIT_BY_SEGMENT['North America'][0] / sum(v[0] for v in F.EBIT_BY_SEGMENT.values()):.0%}",
         "of segment EBIT comes from North America", ORANGE),
        (f"{seg['Greater China'][0] / seg['Greater China'][2] - 1:+.0%}".replace("-", "−"),
         "Greater China revenue over two years", RED),
    ]
    for i, (v, lab, col) in enumerate(callouts):
        x = 8.15 + (i % 2) * 2.35
        y = 1.7 + (i // 2) * 2.45
        box(s, x, y, 2.18, 2.2)
        stat(s, x + 0.22, y + 0.25, 1.8, v, lab, color=col, vsize=32, lsize=13)
    text(s, LM, 6.68, CW, 0.3, f"Source: {F.SOURCE}. APLA = Asia Pacific & Latin America.", size=10, color=MUTED)

    # 4 ------------------------------------------------------------------ what went wrong
    s = d.slide("03  ·  What went wrong", "A margin reset that the market prices as permanent", notes=(
        "The share price has lost most of its value since 2021, but revenue is only modestly below its peak. "
        "What collapsed is the margin, through discounting to clear inventory and the direct-to-consumer push. "
        "Margins stopped falling in FY2026."))
    stat(s, LM, 1.65, 5.8, f"{price / peak - 1:.0%}".replace("-", "−"), "share price from its 5-year high",
         color=RED, vsize=40, lsize=13)
    stat(s, 6.95, 1.65, 5.8, f"{rev[2026] / rev[2023] - 1:.0%}".replace("-", "−"),
         "FY2026 revenue vs the FY2023 peak", color=INK, vsize=40, lsize=13)
    ph = pd.Series(snapshot["price_history"])
    cd = CategoryChartData()
    cd.categories = [pd.Timestamp(k).strftime("%b %y") for k in ph.index]
    cd.add_series("NKE share price (USD)", list(ph.values))
    ch = s.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(LM), Inches(2.85), Inches(5.9), Inches(3.75), cd).chart
    style_chart(ch, title="Monthly share price, USD")
    ser = ch.plots[0].series[0]
    ser.format.line.color.rgb, ser.format.line.width, ser.smooth = rgb(ORANGE), Pt(2.25), False
    ser.marker.style = XL_MARKER_STYLE.NONE
    ca = ch.category_axis._element
    for tag in ("tickLblSkip", "tickMarkSkip"):
        etree.SubElement(ca, C_NS + tag).set("val", "12")
    hy = m.HIST_YEARS
    cd = CategoryChartData()
    cd.categories = [f"FY{str(y)[2:]}" for y in hy]
    cd.add_series("Gross margin", [gm[y] for y in hy])
    cd.add_series("EBIT margin", [margin[y] for y in hy])
    ch = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(6.95), Inches(2.85), Inches(5.8), Inches(3.75),
                            cd).chart
    style_chart(ch, legend=True, title="Margins, % of revenue")
    for ser, col in zip(ch.plots[0].series, (BLUE, ORANGE), strict=True):
        ser.format.line.color.rgb, ser.format.line.width, ser.smooth = rgb(col), Pt(2.25), False
        ser.marker.style = XL_MARKER_STYLE.CIRCLE
        ser.marker.size = 8
        ser.marker.format.fill.solid()
        ser.marker.format.fill.fore_color.rgb = rgb(col)
        ser.marker.format.line.color.rgb = rgb(WHITE)
    data_labels(ch.plots[0], "0.0%", size=10, pos=XL_LABEL_POSITION.ABOVE)
    ch.value_axis.minimum_scale, ch.value_axis.maximum_scale = 0, 0.55
    ch.value_axis.tick_labels.number_format, ch.value_axis.tick_labels.number_format_is_linked = "0%", False

    # 5 ------------------------------------------------------------------ what to believe
    s = d.slide("04  ·  What we need to believe", "The base case asks for less than Nike already delivered",
                notes=("Every driver in the base case is at or below Nike's own track record. Revenue growth "
                       "returns to the FY2022–24 pace, gross margin recovers toward FY2024's level, not FY2022's."))
    rows = [
        ["Driver", "Base case", "Track record"],
        ["Revenue growth FY27–31", " / ".join(f"{x:+.0%}" for x in DRIVERS["revenue_growth"]["Base"]),
         f"FY22–24 CAGR {(rev[2024] / rev[2022]) ** 0.5 - 1:+.1%}"],
        ["Gross margin FY2031", f"{DRIVERS['gross_margin']['Base'][-1]:.1%}",
         f"FY22 {gm[2022]:.1%} · FY26 {gm[2026]:.1%}"],
        ["EBIT margin FY2031", f"{margin[2031]:.1%}", f"FY22 {margin[2022]:.1%} · FY26 {margin[2026]:.1%}"],
        ["Capex, % of revenue", f"{COMMON['capex_pct']:.1%}", "FY22–26 average 1.6%"],
        ["Terminal growth", f"{VALUATION['terminal_growth']:.1%}", "Below US nominal GDP"],
    ]
    table(s, LM, 1.75, 7.45, rows, [2.35, 2.6, 2.5], size=14, row_h=0.66, highlight_cols=(1,))
    text(s, 8.6, 1.75, 4.15, 0.4, "Catalysts in the next 12 months", size=18, bold=True, font=HEAD_FONT)
    cats = [("Gross margin expands", "as clearance and discounting fall away in quarterly results"),
            ("Wholesale order books", "show partners restocking; NIKE Direct returns to full-price selling"),
            ("Capital returns restart", "buybacks resume and import duties are recovered in cash")]
    for i, (a, b) in enumerate(cats):
        y = 2.45 + i * 1.38
        badge(s, 8.6, y, str(i + 1))
        text(s, 9.25, y - 0.02, 3.5, 1.25, [[(a, {"bold": True})], b], size=14, spacing=2)

    # 6 ------------------------------------------------------------------ forecast
    s = d.slide("05  ·  Forecast", "Base case: margins rebuild from FY2028", notes=(
        "Three linked statements, five forecast years. The balance sheet balances in every year, with cash "
        "as the balancing item. Free cash flow stays above the dividend throughout."))
    show = [2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031]
    fcf = df.loc["cfo"] - df.loc["capex"]
    rows = [["USD m"] + [fy(y) for y in show],
            ["Revenue"] + [f"{rev[y]:,.0f}" for y in show],
            ["Growth"] + [f"{rev[y] / rev[y - 1] - 1:+.1%}" for y in show],
            ["Gross margin"] + [f"{gm[y]:.1%}" for y in show],
            ["EBIT"] + [f"{ebit[y]:,.0f}" for y in show],
            ["Net income"] + [f"{df.at['net_income', y]:,.0f}" for y in show],
            ["Diluted EPS (USD)"] + [f"{df.at['net_income', y] / df.at['diluted_shares', y]:.2f}" for y in show],
            ["Free cash flow"] + [f"{fcf[y]:,.0f}" for y in show]]
    table(s, LM, 1.65, CW, rows, [1.97] + [1.27] * 8, size=12, row_h=0.35, highlight_cols=(4, 5, 6, 7, 8))
    years = list(df.columns)
    text(s, LM, 4.6, 8, 0.3, [[("EBIT margin   ", {"bold": True, "color": INK, "size": 14}),
                               ("■ ", {"color": BLUE}), ("actual    ", {}), ("■ ", {"color": ORANGE}),
                               ("forecast", {})]], size=12, color=MUTED)
    cd = CategoryChartData()
    cd.categories = [fy(y) for y in years]
    cd.add_series("EBIT margin", [margin[y] for y in years])
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(LM), Inches(4.95), Inches(CW), Inches(1.95),
                            cd).chart
    style_chart(ch)
    ch.plots[0].gap_width = 70
    ser = ch.plots[0].series[0]
    for i, y in enumerate(years):
        pnt = ser.points[i]
        pnt.format.fill.solid()
        pnt.format.fill.fore_color.rgb = rgb(BLUE if y <= 2026 else ORANGE)
    data_labels(ch.plots[0], "0.0%", size=11)
    ch.value_axis.visible = False
    ch.value_axis.has_major_gridlines = False
    ch.value_axis.minimum_scale, ch.value_axis.maximum_scale = 0, 0.19

    # 7 ------------------------------------------------------------------ DCF
    s = d.slide("06  ·  Valuation", f"DCF: ${base.per_share:.2f} per share at a {w.wacc:.1%} WACC", notes=(
        f"We discount free cash flow to the firm at {w.wacc:.2%}. The terminal value is {base.pv_tv_share:.0%} "
        "of enterprise value, so the grid on the right matters: our value is above the share price in every "
        "combination of WACC and terminal growth shown."))
    box(s, LM, 1.7, 4.4, 5.0)
    text(s, LM + 0.3, 1.92, 3.8, 0.4, "Cost of capital", size=16, bold=True, font=HEAD_FONT)
    items = [("Risk-free (US 10Y)", f"{w.rf:.2%}"), ("Beta (Blume-adjusted)", f"{w.beta:.2f}"),
             ("Equity risk premium", f"{w.erp:.2%}"), ("Cost of equity", f"{w.ke:.2%}"),
             ("After-tax cost of debt", f"{w.kd_after_tax:.2%}"), ("Debt weight", f"{w.weight_debt:.1%}")]
    for i, (a, b) in enumerate(items):
        y = 2.4 + i * 0.36
        text(s, LM + 0.3, y, 2.6, 0.3, a, size=14)
        text(s, LM + 2.9, y, 1.2, 0.3, b, size=14, bold=True, align=PP_ALIGN.RIGHT)
    hline(s, LM + 0.3, 4.62, LM + 4.1, color="D1D5DB")
    text(s, LM + 0.3, 4.75, 2.6, 0.4, "WACC", size=16, bold=True, font=HEAD_FONT)
    text(s, LM + 2.6, 4.7, 1.5, 0.45, f"{w.wacc:.2%}", size=20, bold=True, color=ORANGE, align=PP_ALIGN.RIGHT,
         font=HEAD_FONT)
    bridge = [("Enterprise value", base.ev), ("+ Net cash", net_cash), ("Equity value", base.equity)]
    for i, (a, b) in enumerate(bridge):
        y = 5.4 + i * 0.38
        text(s, LM + 0.3, y, 2.6, 0.3, a, size=14, bold=i != 1)
        text(s, LM + 2.6, y, 1.5, 0.3, f"${b / 1e3:,.1f}bn", size=14, bold=i != 1, align=PP_ALIGN.RIGHT)
    ws_ = [w.wacc + x for x in (-0.01, -0.005, 0, 0.005, 0.01)]
    gs_ = [VALUATION["terminal_growth"] + x for x in (-0.01, -0.005, 0, 0.005, 0.01)]
    grid = np.array([[m.value(h, snapshot, "Base", wv, gv)[0].per_share for gv in gs_] for wv in ws_])
    text(s, 5.45, 1.75, 7.3, 0.4, [[("Value per share, USD", {"bold": True, "color": INK, "size": 16,
                                                               "font": HEAD_FONT}),
                                    (f"     greener = further above the ${price:.2f} share price", {})]],
         size=12, color=MUTED)
    rows = [["WACC  \\  g"] + [f"{g:.1%}" for g in gs_]] + [[f"{wv:.1%}"] + [f"${v:.0f}" for v in r]
                                                             for wv, r in zip(ws_, grid, strict=True)]
    gt = table(s, 5.45, 2.3, 7.28, rows, [1.28] + [1.2] * 5, size=15, row_h=0.62)
    span = np.abs(grid - price).max()
    for i in range(5):
        for j in range(5):
            cell = gt.cell(i + 1, j + 1)
            g_ = (grid[i, j] - price) / span
            tgt = np.array([0x1F, 0x9D, 0x55]) if g_ > 0 else np.array([0xC2, 0x36, 0x2B])
            c = 255 + (tgt - 255) * min(abs(g_), 1) * 0.5
            cell.fill.fore_color.rgb = RGBColor(*[int(v) for v in c])
            r = cell.text_frame.paragraphs[0].runs[0]
            r.font.bold = (i, j) == (2, 2)
            r.font.size = Pt(18 if (i, j) == (2, 2) else 15)
    text(s, 5.45, 6.2, 7.3, 0.5, f"Terminal value is {base.pv_tv_share:.0%} of EV; implied exit multiple "
         f"{base.tv / df.at['ebitda', 2031]:.1f}x FY2031 EBITDA. Stock-based pay is treated as a cash cost.",
         size=12, color=MUTED)

    # 8 ------------------------------------------------------------------ comps + football field
    s = d.slide("07  ·  Cross-checks", "Comparables frame the floor; the DCF sets the target", notes=(
        "Peers are priced on trailing earnings, which are depressed for Nike, so multiples give a floor near "
        "today's price. Our target sits inside every range except trailing EV/EBITDA."))
    st = comps_stats(snapshot)
    rows = [["Company", "Mkt cap $bn", "EV/Sales", "EV/EBITDA", "Op. margin"]]
    for p in snapshot["peers"]:
        eve = p["enterprise_value"] / p["ebitda"] if p["ebitda"] and p["ebitda"] > 0 else None
        rows.append([p["name"].split(" (")[0], f"{p['market_cap_usd'] / 1e9:.1f}",
                     f"{p['enterprise_value'] / p['revenue']:.2f}x", f"{eve:.1f}x" if eve else "n.m.",
                     f"{p['operating_margin']:.0%}"])
    rows.append(["Peer median", "", f"{st['ev_sales'][1]:.2f}x", f"{st['ev_ebitda'][1]:.1f}x", ""])
    table(s, LM, 1.7, 5.9, rows, [1.65, 1.15, 1.0, 1.1, 1.0], size=12, row_h=0.41, bold_rows=(1, len(rows) - 1))
    text(s, LM, 1.7 + 0.41 * len(rows) + 0.12, 5.9, 0.5, "Last twelve months, Yahoo Finance. EV = market cap + "
         "debt incl. leases – cash. Puma EBITDA negative.", size=10, color=MUTED)
    fx0, fw, hi_v = 7.3, 5.4, 80  # football field scale: 0 to 80 USD across fw inches

    def X(v):
        return fx0 + v / hi_v * fw

    text(s, 7.1, 1.75, 5.6, 0.4, "Football field, USD per share", size=16, bold=True, font=HEAD_FONT)
    bars = [("DCF, bear to bull", vals["Bear"][0].per_share, vals["Bull"][0].per_share, ORANGE),
            ("EV/EBITDA, peer IQR", *imp["EV/EBITDA (peer IQR)"][[0, 2]], BLUE),
            ("EV/Sales, peer IQR", *imp["EV/Sales (peer IQR)"][[0, 2]], BLUE),
            ("52-week range", snapshot["week52_low"], snapshot["week52_high"], MUTED)]
    top, step = 2.75, 0.95
    bottom = top + len(bars) * step - 0.2
    # reference lines first, so the bars and their labels sit on top of them
    for v, lab, col, dash, left in ((price, f"Price ${price:.2f}", RED, True, True),
                                    (pt, f"Target ${pt}", GREEN, False, False)):
        vline(s, X(v), top - 0.05, bottom, col, dash=dash)
        text(s, X(v) - 1.55 if left else X(v) + 0.05, top - 0.4, 1.5, 0.3, lab, size=12, bold=True, color=col,
             align=PP_ALIGN.RIGHT if left else PP_ALIGN.LEFT)
    for i, (lab, lo, hi, col) in enumerate(bars):
        y = top + i * step
        text(s, X(0), y, 3, 0.3, lab, size=12, color=MUTED)
        box(s, X(lo), y + 0.3, X(hi) - X(lo), 0.42, fill=col, radius=0.25)
        text(s, X(lo) + 0.1, y + 0.3, 0.6, 0.42, f"${lo:.0f}", size=12, bold=True, color=WHITE,
             anchor=MSO_ANCHOR.MIDDLE)
        text(s, X(hi) - 0.7, y + 0.3, 0.6, 0.42, f"${hi:.0f}", size=12, bold=True, color=WHITE,
             align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    hline(s, X(0), bottom + 0.1, X(hi_v), color="D1D5DB")
    for v in (0, 20, 40, 60, 80):
        text(s, X(v) - 0.3, bottom + 0.17, 0.6, 0.25, f"${v}", size=10, color=MUTED, align=PP_ALIGN.CENTER)

    # 9 ------------------------------------------------------------------ risks
    s = d.slide("08  ·  Risks", "What would prove us wrong, and what to watch", notes=(
        f"The bear case is ${vals['Bear'][0].per_share:.0f}, {vals['Bear'][0].upside:+.0%}: growth stalls and "
        "gross margin stays near 41%. Each risk has a signpost we can check every quarter."))
    risks = [
        ("Challengers keep taking share", "On, Hoka and Asics are growing fast in running",
         "Running and NIKE Direct growth each quarter"),
        ("Tariffs and sourcing concentration",
         (f"{F.FOOTWEAR_SOURCING_FY2026['Vietnam']:.0%} of footwear made in Vietnam; top 4 suppliers make "
         f"{F.TOP4_FOOTWEAR_MANUFACTURERS_SHARE:.0%}"), "Gross-margin bridge in each 10-Q"),
        ("Greater China does not recover",
         (f"Revenue {F.REVENUE_BY_SEGMENT['Greater China'][0] / F.REVENUE_BY_SEGMENT['Greater China'][2] - 1:.0%}"
         " in two years; Anta and Li Ning gaining"), "China EBIT margin, 22% in FY2026"),
        ("Wholesale concentration", f"Top 3 US customers are {F.TOP3_US_CUSTOMERS_SHARE_OF_US_SALES:.0%} of US sales",
         "Partner inventory and order books"),
        ("Terminal value dependence", (f"{base.pv_tv_share:.0%} of EV; ±1pt WACC moves value by about "
         f"${(grid[0, 2] - grid[4, 2]) / 2:.0f}"), "Bear case still has positive free cash flow"),
    ]
    for j, hd in enumerate(["Risk", "Evidence", "Signpost"]):
        text(s, (1.35, 5.3, 9.35)[j], 1.72, 3, 0.3, hd.upper(), size=11, bold=True, color=MUTED, font=HEAD_FONT)
    for i, (a, b, c) in enumerate(risks):
        y = 2.15 + i * 0.88
        badge(s, LM, y + 0.06, str(i + 1), d=0.42, fill=INK, size=13)
        text(s, 1.35, y + 0.1, 3.75, 0.7, a, size=15, bold=True)
        text(s, 5.3, y + 0.1, 3.85, 0.7, b, size=14)
        text(s, 9.35, y + 0.1, 3.4, 0.7, c, size=14, color=MUTED)
        if i < len(risks) - 1:
            hline(s, LM, y + 0.8, SW - LM)

    # 10 ----------------------------------------------------------------- recommendation (dark)
    s = d.slide("09  ·  Recommendation", f"{rating}, target price ${pt}", dark=True, notes=(
        "Downside to the bear case is about a quarter; upside to the bull case is about three quarters. We would "
        "start at half weight, add as gross margin expands, and review the position if gross margin stays "
        "below 41% for two quarters."))
    sc = ["Bear", "Base", "Bull"]
    cd = CategoryChartData()
    cd.categories = [f"{k}  ({vals[k][0].upside:+.0%})" for k in sc]
    cd.add_series("Value per share", [vals[k][0].per_share for k in sc])
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(LM), Inches(1.75), Inches(6.2), Inches(4.85),
                            cd).chart
    style_chart(ch, label_color=DARK_MUTED, grid="2A2E35")
    ch.plots[0].gap_width = 55
    for i, col in enumerate((RED, ORANGE, GREEN)):
        p_ = ch.plots[0].series[0].points[i]
        p_.format.fill.solid()
        p_.format.fill.fore_color.rgb = rgb(col)
    data_labels(ch.plots[0], '"$"0', size=18, color=WHITE)
    ch.value_axis.minimum_scale, ch.value_axis.maximum_scale = 0, 70
    ch.value_axis.visible = False
    ch.value_axis.has_major_gridlines = False
    ch.category_axis.tick_labels.font.size = Pt(14)
    text(s, LM, 6.62, 6.2, 0.3, f"Value per share by scenario vs the ${price:.2f} share price", size=11,
         color=DARK_MUTED)
    recs = [(f"{rating} with a ${pt} target", (f"{up:+.0%} upside; bear ${vals['Bear'][0].per_share:.0f}, "
             f"bull ${vals['Bull'][0].per_share:.0f}")),
            ("Size the position in steps", "Start at half weight; add on evidence of gross-margin expansion"),
            ("Know when to exit", (f"Review if gross margin stays below {DRIVERS['gross_margin']['Bear'][1]:.0%} "
             "for two quarters, which is the bear case"))]
    for i, (a, b) in enumerate(recs):
        y = 2.0 + i * 1.45
        badge(s, 7.4, y, str(i + 1))
        text(s, 8.05, y - 0.02, 4.7, 1.3, [[(a, {"bold": True, "color": WHITE, "size": 18})], b], size=14,
             color=DARK_MUTED, spacing=3)

    out_dir.mkdir(parents=True, exist_ok=True)
    d.prs.save(out_dir / "NKE_stock_pitch.pptx")
    return {"price": price, "target": pt, "rating": rating, "upside": up,
            "scenarios": {k: round(vals[k][0].per_share, 2) for k in sc}, "wacc": w.wacc,
            "implied": {k: [round(x, 2) for x in v] for k, v in imp.items()}}
