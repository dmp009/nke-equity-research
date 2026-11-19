"""Write the 3-statement + DCF model as an Excel workbook with live formulas.

Layout: column A = labels, B-F = FY2022A-FY2026A (10-K values), G-K = FY2027E-FY2031E (formulas).
Blue font = hard-coded input, black = formula. Change Inputs!C4 (1 Bear, 2 Base, 3 Bull) or any
blue driver and every statement, the DCF and the sensitivity grid recalculate.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from nkeresearch import model as m
from nkeresearch.assumptions import BUYBACKS, COMMON, DRIVERS, FORECAST_YEARS, SCENARIOS, VALUATION

HIST = m.HIST_YEARS
YEARS = HIST + FORECAST_YEARS
COL = {y: get_column_letter(2 + i) for i, y in enumerate(YEARS)}  # 2022 -> B ... 2031 -> K
HC, FC = [COL[y] for y in HIST], [COL[y] for y in FORECAST_YEARS]
F0, FN = FC[0], FC[-1]  # G, K

BLUE = Font(color="1F4E99")
BOLD = Font(bold=True)
HEAD = Font(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="111111")
SUB_FILL = PatternFill("solid", fgColor="EDEDED")
TOP = Border(top=Side(style="thin"))
USD = '#,##0;(#,##0);"–"'
PCT = '0.0%;(0.0%);"–"'
X = '0.0"x"'


def prev(col: str) -> str:
    return get_column_letter(ord(col) - ord("A"))


class Sheet:
    """Small helper: named rows so formulas can reference other lines by name."""

    def __init__(self, ws, title: str, first_row: int = 4):
        self.ws, self.rows, self.r = ws, {}, first_row
        ws["A1"] = title
        ws["A1"].font = Font(bold=True, size=14)
        ws["A2"] = "USD millions unless stated. Blue = input, black = formula."
        ws["A2"].font = Font(italic=True, color="666666")
        ws.column_dimensions["A"].width = 44
        for c in COL.values():
            ws.column_dimensions[c].width = 12

    def header(self):
        ws, r = self.ws, self.r
        ws.cell(r, 1, "Fiscal year ending 31 May")
        for y, c in COL.items():
            ws[f"{c}{r}"] = f"FY{y}{'A' if y in HIST else 'E'}"
        for cell in ws[r][: 1 + len(YEARS)]:
            cell.font, cell.fill = HEAD, HEAD_FILL
            cell.alignment = Alignment(horizontal="center") if cell.column > 1 else Alignment()
        ws.freeze_panes = f"B{r + 1}"
        self.r += 1

    def section(self, label: str):
        self.r += 1
        self.ws.cell(self.r, 1, label).font = BOLD
        self.ws.cell(self.r, 1).fill = SUB_FILL
        self.r += 1

    def line(self, name, label, hist=None, fcst=None, every=None, fmt=USD, bold=False, sign=1):
        """hist: series by year (hard-coded); fcst/every: formula template with {c} {p} {r}."""
        ws, r = self.ws, self.r
        self.rows[name] = r
        ws.cell(r, 1, label)
        for y in YEARS:
            c = COL[y]
            tpl = every if every is not None else (fcst if y in FORECAST_YEARS else None)
            if tpl is not None:
                ws[f"{c}{r}"] = tpl.format(c=c, p=prev(c), r=r)
            elif hist is not None and y in HIST:
                ws[f"{c}{r}"] = round(float(hist[y]) * sign, 3)
                ws[f"{c}{r}"].font = BLUE
            ws[f"{c}{r}"].number_format = fmt
        if bold:
            for cell in ws[r][: 1 + len(YEARS)]:
                cell.font = Font(bold=True, color=cell.font.color)
                cell.border = TOP
        self.r += 1
        return r

    def __getitem__(self, name):
        return self.rows[name]


def write_inputs(ws, snapshot: dict, hist_shares: float) -> dict:
    ref = {}
    ws["A1"] = "Inputs and scenario drivers"
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 16
    for c in FC:
        ws.column_dimensions[c].width = 11

    ws["A4"], ws["C4"] = "Active scenario (1 = Bear, 2 = Base, 3 = Bull)", 2
    ws["C4"].font = Font(bold=True, color="1F4E99")
    ws["C4"].fill = PatternFill("solid", fgColor="FFF2CC")
    ws["D4"] = '=CHOOSE(C4,"Bear","Base","Bull")'
    ref["scenario"] = "Inputs!$C$4"

    rows = [
        ("price", "Share price (USD), " + snapshot["price_date"], snapshot["price"], "0.00"),
        ("shares", "Shares outstanding (m) = market cap / price", m.shares_outstanding(snapshot), "#,##0.0"),
        ("rf", "Risk-free rate: " + snapshot["rf_source"] + ", " + snapshot["rf_date"], snapshot["rf"], "0.00%"),
        ("beta_raw", "Raw beta, " + snapshot["beta_window"], snapshot["beta_raw"], "0.000"),
        ("erp", "Equity risk premium: " + VALUATION["erp_source"], VALUATION["erp"], "0.00%"),
        ("g", "Terminal growth rate", VALUATION["terminal_growth"], "0.00%"),
        ("tax_marginal", "Marginal tax rate (debt tax shield)", VALUATION["marginal_tax_rate"], "0.0%"),
        ("stub", "Share of FY2027 after valuation date " + VALUATION["valuation_date"], m.stub_fraction(), "0.000"),
    ]
    r = 6
    ws.cell(r, 1, "Market and valuation inputs").font = BOLD
    for key, label, val, fmt in rows:
        r += 1
        ws.cell(r, 1, label)
        ws.cell(r, 3, val).font = BLUE
        ws.cell(r, 3).number_format = fmt
        ref[key] = f"Inputs!$C${r}"

    r += 2
    ws.cell(r, 1, "Operating drivers (all scenarios)").font = BOLD
    labels = {
        "tax_rate": "Effective tax rate", "d_and_a_pct": "D&A, % of revenue", "capex_pct": "Capex, % of revenue",
        "sbc_pct": "Stock-based compensation, % of revenue", "receivable_days": "Receivable days (on revenue)",
        "inventory_days": "Inventory days (on COGS)", "payable_days": "Payable days (on COGS)",
        "prepaid_pct": "Prepaid & other current assets, % of revenue",
        "accrued_pct": "Accrued liabilities, % of revenue",
        "cash_yield": "Interest yield on cash & short-term investments",
        "cost_of_debt_pretax": "Pre-tax cost of debt (rf + 90 bp)",
        "dividend_growth": "Growth in dividends paid",
    }
    for key, label in labels.items():
        r += 1
        ws.cell(r, 1, label)
        ws.cell(r, 3, COMMON[key]).font = BLUE
        ws.cell(r, 3).number_format = "0.0" if key.endswith("days") else "0.0%"
        ref[key] = f"Inputs!$C${r}"

    r += 2
    ws.cell(r, 1, "Scenario drivers").font = BOLD
    for i, y in enumerate(FORECAST_YEARS):
        ws[f"{FC[i]}{r}"] = f"FY{y}E"
        ws[f"{FC[i]}{r}"].font = HEAD
        ws[f"{FC[i]}{r}"].fill = HEAD_FILL
    names = {
        "revenue_growth": ("Revenue growth", PCT), "gross_margin": ("Gross margin", PCT),
        "demand_creation_pct": ("Demand creation, % of revenue", PCT),
        "overhead_pct": ("Operating overhead, % of revenue", PCT),
        "buybacks": ("Share buybacks (USD m)", USD),
    }
    for key, (label, fmt) in names.items():
        values = BUYBACKS if key == "buybacks" else DRIVERS[key]
        r += 1
        start = r + 1
        for s in SCENARIOS:
            r += 1
            ws.cell(r, 1, f"  {label} – {s}")
            for i in range(len(FORECAST_YEARS)):
                cell = ws[f"{FC[i]}{r}"]
                cell.value, cell.font, cell.number_format = values[s][i], BLUE, fmt
        r += 1
        ws.cell(r, 1, f"{label} – ACTIVE").font = BOLD
        for c in FC:
            ws[f"{c}{r}"] = f"=CHOOSE($C$4,{c}{start},{c}{start + 1},{c}{start + 2})"
            ws[f"{c}{r}"].number_format = fmt
            ws[f"{c}{r}"].font = BOLD
        ref[key] = r  # row of the ACTIVE line, columns G-K
    return ref


def write_workbook(h: pd.DataFrame, snapshot: dict, out: Path, scenario_table: list[m.Valuation]) -> Path:
    h = m.notes_payable_plug(h)
    wb = Workbook()
    cover = wb.active
    cover.title = "Cover"
    inp = wb.create_sheet("Inputs")
    ws_is, ws_bs, ws_cf = wb.create_sheet("IS"), wb.create_sheet("BS"), wb.create_sheet("CF")
    ws_dcf, ws_comps = wb.create_sheet("DCF"), wb.create_sheet("Comps")
    ref = write_inputs(inp, snapshot, h.at["diluted_shares", 2026])

    def drv(key):  # active scenario driver, same column as the statement
        return f"Inputs!{{c}}${ref[key]}"

    IS, BS, CF = Sheet(ws_is, "Nike, Inc. – Income statement"), Sheet(ws_bs, "Nike, Inc. – Balance sheet"), \
        Sheet(ws_cf, "Nike, Inc. – Cash flow statement")
    for s in (IS, BS, CF):
        s.header()

    # ---- row numbers needed before formulas reference them (fixed layout) ----
    # Income statement
    IS.section("Income statement")
    IS.line("revenue", "Revenues", h.loc["revenue"], f"={{p}}{{r}}*(1+{drv('revenue_growth')})")
    IS.line("cogs", "Cost of sales", h.loc["cogs"], f"={{c}}{IS['revenue']}*(1-{drv('gross_margin')})")
    IS.line("gross_profit", "Gross profit", every=f"={{c}}{IS['revenue']}-{{c}}{IS['cogs']}", bold=True)
    IS.line("demand_creation", "Demand creation expense", h.loc["demand_creation"],
            f"={{c}}{IS['revenue']}*{drv('demand_creation_pct')}")
    IS.line("operating_overhead", "Operating overhead expense", h.loc["operating_overhead"],
            f"={{c}}{IS['revenue']}*{drv('overhead_pct')}")
    IS.line("ebit", "EBIT (operating income)",
            every=f"={{c}}{IS['gross_profit']}-{{c}}{IS['demand_creation']}-{{c}}{IS['operating_overhead']}",
            bold=True)
    # BS rows referenced below are known after BS is written; use placeholders resolved later
    IS.line("net_interest_income", "Interest income (expense), net", h.loc["net_interest_income"], "__NII__")
    IS.line("other_income", "Other income (expense), net", h.loc["other_income"], "=0")
    IS.line("pretax_income", "Income before taxes",
            every=f"={{c}}{IS['ebit']}+{{c}}{IS['net_interest_income']}+{{c}}{IS['other_income']}", bold=True)
    IS.line("income_tax", "Income tax expense", h.loc["income_tax"],
            f"={{c}}{IS['pretax_income']}*{ref['tax_rate']}")
    IS.line("net_income", "Net income", every=f"={{c}}{IS['pretax_income']}-{{c}}{IS['income_tax']}", bold=True)
    IS.line("diluted_shares", "Diluted shares (m)", h.loc["diluted_shares"], "={p}{r}", fmt="#,##0.0")
    IS.line("eps", "Diluted EPS (USD)", every=f"={{c}}{IS['net_income']}/{{c}}{IS['diluted_shares']}", fmt="0.00")
    IS.section("Margins and growth")
    IS.line("growth", "Revenue growth", every=f"=IFERROR({{c}}{IS['revenue']}/{{p}}{IS['revenue']}-1,\"\")", fmt=PCT)
    IS.line("gm", "Gross margin", every=f"={{c}}{IS['gross_profit']}/{{c}}{IS['revenue']}", fmt=PCT)
    IS.line("ebit_margin", "EBIT margin", every=f"={{c}}{IS['ebit']}/{{c}}{IS['revenue']}", fmt=PCT)
    IS.line("ebitda", "EBITDA (EBIT + D&A)", every="__EBITDA__")
    IS.line("tax_rate", "Effective tax rate", every=f"={{c}}{IS['income_tax']}/{{c}}{IS['pretax_income']}", fmt=PCT)
    ws_is["B" + str(IS['growth'])] = None

    # Balance sheet
    rev, cogs = f"IS!{{c}}{IS['revenue']}", f"IS!{{c}}{IS['cogs']}"
    BS.section("Assets")
    BS.line("cash", "Cash and equivalents", h.loc["cash"], "__CASH__")
    BS.line("st_investments", "Short-term investments", h.loc["st_investments"], "={p}{r}")
    BS.line("receivables", "Accounts receivable, net", h.loc["receivables"], f"={rev}*{ref['receivable_days']}/365")
    BS.line("inventories", "Inventories", h.loc["inventories"], f"={cogs}*{ref['inventory_days']}/365")
    BS.line("prepaid_other_current", "Prepaid expenses and other current assets", h.loc["prepaid_other_current"],
            f"={rev}*{ref['prepaid_pct']}")
    BS.line("tca", "Total current assets", every=f"=SUM({{c}}{BS['cash']}:{{c}}{BS['prepaid_other_current']})",
            bold=True)
    BS.line("ppe_net", "Property, plant and equipment, net", h.loc["ppe_net"], "__PPE__")
    BS.line("rou_assets", "Operating lease right-of-use assets", h.loc["rou_assets"], "={p}{r}")
    BS.line("intangibles", "Identifiable intangible assets, net", h.loc["intangibles"], "={p}{r}")
    BS.line("goodwill", "Goodwill", h.loc["goodwill"], "={p}{r}")
    BS.line("other_noncurrent_assets", "Deferred income taxes and other assets", h.loc["other_noncurrent_assets"],
            "={p}{r}")
    BS.line("total_assets", "Total assets",
            every=f"={{c}}{BS['tca']}+SUM({{c}}{BS['ppe_net']}:{{c}}{BS['other_noncurrent_assets']})", bold=True)
    BS.section("Liabilities and shareholders' equity")
    BS.line("current_debt", "Current portion of long-term debt", h.loc["current_debt"], "={p}{r}")
    BS.line("notes_payable", "Notes payable and other", h.loc["notes_payable"], "={p}{r}")
    BS.line("payables", "Accounts payable", h.loc["payables"], f"={cogs}*{ref['payable_days']}/365")
    BS.line("lease_liab_current", "Current portion of operating lease liabilities", h.loc["lease_liab_current"],
            "={p}{r}")
    BS.line("accrued_liabilities", "Accrued liabilities", h.loc["accrued_liabilities"], f"={rev}*{ref['accrued_pct']}")
    BS.line("income_taxes_payable", "Income taxes payable", h.loc["income_taxes_payable"], "={p}{r}")
    BS.line("tcl", "Total current liabilities",
            every=f"=SUM({{c}}{BS['current_debt']}:{{c}}{BS['income_taxes_payable']})", bold=True)
    BS.line("long_term_debt", "Long-term debt", h.loc["long_term_debt"], "={p}{r}")
    BS.line("lease_liab_noncurrent", "Operating lease liabilities", h.loc["lease_liab_noncurrent"], "={p}{r}")
    BS.line("other_noncurrent_liabilities", "Deferred income taxes and other liabilities",
            h.loc["other_noncurrent_liabilities"], "={p}{r}")
    BS.line("total_liabilities", "Total liabilities",
            every=f"={{c}}{BS['tcl']}+SUM({{c}}{BS['long_term_debt']}:{{c}}{BS['other_noncurrent_liabilities']})",
            bold=True)
    BS.line("equity", "Total shareholders' equity", h.loc["equity"], "__EQUITY__")
    BS.line("total_le", "Total liabilities and shareholders' equity",
            every=f"={{c}}{BS['total_liabilities']}+{{c}}{BS['equity']}", bold=True)
    BS.line("check", "Balance check (assets – liabilities – equity), must be 0",
            every=f"=ROUND({{c}}{BS['total_assets']}-{{c}}{BS['total_le']},3)")
    BS.section("Memo")
    BS.line("total_debt", "Total debt",
            every=f"={{c}}{BS['current_debt']}+{{c}}{BS['notes_payable']}+{{c}}{BS['long_term_debt']}")
    BS.line("nwc", "Operating net working capital",
            every=f"=SUM({{c}}{BS['receivables']}:{{c}}{BS['prepaid_other_current']})"
                  f"-{{c}}{BS['payables']}-{{c}}{BS['accrued_liabilities']}")

    # Cash flow
    def delta_asset(k):
        return f"=BS!{{p}}{BS[k]}-BS!{{c}}{BS[k]}"

    def delta_liab(k):
        return f"=BS!{{c}}{BS[k]}-BS!{{p}}{BS[k]}"

    CF.section("Operating activities")
    CF.line("net_income", "Net income", every=f"=IS!{{c}}{IS['net_income']}")
    CF.line("d_and_a", "Depreciation and amortization", h.loc["d_and_a"], f"={rev}*{ref['d_and_a_pct']}")
    CF.line("sbc", "Stock-based compensation", h.loc["sbc"], f"={rev}*{ref['sbc_pct']}")
    CF.line("d_rec", "(Increase) decrease in receivables", fcst=delta_asset("receivables"))
    CF.line("d_inv", "(Increase) decrease in inventories", fcst=delta_asset("inventories"))
    CF.line("d_pre", "(Increase) decrease in prepaid and other", fcst=delta_asset("prepaid_other_current"))
    CF.line("d_pay", "Increase (decrease) in payables", fcst=delta_liab("payables"))
    CF.line("d_acc", "Increase (decrease) in accrued liabilities", fcst=delta_liab("accrued_liabilities"))
    CF.line("cfo", "Cash from operations (FY2022-26 as reported)", h.loc["cfo"],
            f"=SUM({{c}}{CF['net_income']}:{{c}}{CF['d_acc']})", bold=True)
    CF.section("Investing and financing")
    CF.line("capex", "Capital expenditures", h.loc["capex"], f"=-{rev}*{ref['capex_pct']}", sign=-1)
    CF.line("dividends", "Dividends paid", h.loc["dividends_paid"], f"={{p}}{{r}}*(1+{ref['dividend_growth']})",
            sign=-1)
    CF.line("buybacks", "Share repurchases", h.loc["buybacks"], f"=-{drv('buybacks')}", sign=-1)
    CF.line("d_debt", "Net debt issuance (repayment)", fcst=delta_liab("total_debt"))
    CF.line("net_change", "Net change in cash (forecast)",
            fcst=f"={{c}}{CF['cfo']}+SUM({{c}}{CF['capex']}:{{c}}{CF['d_debt']})", bold=True)
    CF.line("begin_cash", "Beginning cash", fcst=f"=BS!{{p}}{BS['cash']}")
    CF.line("end_cash", "Ending cash", fcst=f"={{c}}{CF['begin_cash']}+{{c}}{CF['net_change']}", bold=True)
    CF.line("fcf", "Free cash flow (CFO – capex)", every=f"={{c}}{CF['cfo']}+{{c}}{CF['capex']}")

    # resolve cross-sheet placeholders
    fills = {
        (ws_is, "__NII__"): f"=(BS!{{p}}{BS['cash']}+BS!{{p}}{BS['st_investments']})*{ref['cash_yield']}"
                            f"-BS!{{p}}{BS['total_debt']}*{ref['cost_of_debt_pretax']}",
        (ws_is, "__EBITDA__"): f"={{c}}{IS['ebit']}+CF!{{c}}{CF['d_and_a']}",
        (ws_bs, "__CASH__"): f"=CF!{{c}}{CF['end_cash']}",
        (ws_bs, "__PPE__"): f"={{p}}{{r}}-CF!{{c}}{CF['capex']}-CF!{{c}}{CF['d_and_a']}",
        (ws_bs, "__EQUITY__"): f"={{p}}{{r}}+IS!{{c}}{IS['net_income']}+CF!{{c}}{CF['sbc']}"
                               f"+CF!{{c}}{CF['dividends']}+CF!{{c}}{CF['buybacks']}",
    }
    for ws in (ws_is, ws_bs):
        for row in ws.iter_rows(min_row=4):
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("__"):
                    c = cell.column_letter
                    cell.value = fills[(ws, cell.value)].format(c=c, p=prev(c), r=cell.row)

    write_dcf(ws_dcf, ref, IS, BS, CF)
    write_comps(ws_comps, snapshot, ref)
    write_cover(cover, snapshot, scenario_table, BS['check'])
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


DCF_CELLS = {}  # name -> absolute cell on the DCF sheet, filled by write_dcf


def write_dcf(ws, ref, IS, BS, CF):
    ws["A1"] = "Discounted cash flow valuation (FCFF, Gordon growth terminal value)"
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 46
    for c in "BCDEFGHIJK":
        ws.column_dimensions[c].width = 12
    last = HC[-1]  # FY2026 balance sheet (column F)
    wacc_rows = [
        ("rf", "Risk-free rate", f"={ref['rf']}", "0.00%"),
        ("beta_raw", "Raw beta", f"={ref['beta_raw']}", "0.000"),
        ("beta", "Adjusted beta (Blume: 0.67 × raw + 0.33)", "=0.67*B5+0.33", "0.000"),
        ("erp", "Equity risk premium", f"={ref['erp']}", "0.00%"),
        ("ke", "Cost of equity (CAPM)", "=B4+B6*B7", "0.00%"),
        ("kd", "Pre-tax cost of debt", f"={ref['cost_of_debt_pretax']}", "0.00%"),
        ("kd_at", "After-tax cost of debt", f"=B9*(1-{ref['tax_marginal']})", "0.00%"),
        ("mcap", "Market value of equity (USD m)", f"={ref['price']}*{ref['shares']}", USD),
        ("debt", "Total debt, FY2026 (USD m)", f"=BS!{last}{BS['total_debt']}", USD),
        ("wd", "Debt weight D/(D+E)", "=B12/(B11+B12)", "0.0%"),
        ("wacc", "WACC", "=(1-B13)*B8+B13*B10", "0.00%"),
        ("g", "Terminal growth", f"={ref['g']}", "0.00%"),
    ]
    ws["A3"] = "Cost of capital"
    ws["A3"].font = BOLD
    for i, (k, label, f, fmt) in enumerate(wacc_rows):
        r = 4 + i
        ws.cell(r, 1, label)
        ws.cell(r, 2, f).number_format = fmt
        DCF_CELLS[k] = f"$B${r}"
    for k in ("wacc", "ke"):
        ws[DCF_CELLS[k].replace("$", "")].font = BOLD

    r0 = 18
    ws.cell(r0, 1, "Free cash flow to the firm").font = BOLD
    for i, y in enumerate(FORECAST_YEARS):
        cell = ws[f"{FC[i]}{r0}"]
        cell.value, cell.font, cell.fill = f"FY{y}E", HEAD, HEAD_FILL
    lines = [
        ("ebit", "EBIT", f"=IS!{{c}}{IS['ebit']}", USD),
        ("tax", "Less: taxes on EBIT", f"=-{{c}}{r0 + 1}*{ref['tax_rate']}", USD),
        ("nopat", "NOPAT", f"={{c}}{r0 + 1}+{{c}}{r0 + 2}", USD),
        ("da", "Plus: D&A", f"=CF!{{c}}{CF['d_and_a']}", USD),
        ("capex", "Less: capex", f"=CF!{{c}}{CF['capex']}", USD),
        ("dnwc", "Less: increase in operating NWC", f"=-(BS!{{c}}{BS['nwc']}-BS!{{p}}{BS['nwc']})", USD),
        ("fcff", "FCFF (stock-based comp. treated as a cash cost)", f"=SUM({{c}}{r0 + 3}:{{c}}{r0 + 6})", USD),
        ("frac", "Share of year counted (FY2027 stub)", None, "0.000"),
        ("period", "Discount period (years from valuation date)", None, "0.000"),
        ("counted", "FCFF counted", f"={{c}}{r0 + 7}*{{c}}{r0 + 8}", USD),
        ("df", "Discount factor", f"=1/(1+{DCF_CELLS['wacc']})^{{c}}{r0 + 9}", "0.0000"),
        ("pv", "Present value of FCFF", f"={{c}}{r0 + 10}*{{c}}{r0 + 11}", USD),
    ]
    rows = {}
    for i, (k, label, f, fmt) in enumerate(lines):
        r = r0 + 1 + i
        rows[k] = r
        ws.cell(r, 1, label)
        for c in FC:
            if k == "frac":
                v = f"={ref['stub']}" if c == F0 else 1
            elif k == "period":
                v = f"={ref['stub']}" if c == F0 else f"={prev(c)}{r}+1"
            else:
                v = f.format(c=c, p=prev(c))
            ws[f"{c}{r}"] = v
            ws[f"{c}{r}"].number_format = fmt
        if k in ("fcff", "pv"):
            for c in ["A"] + FC:
                ws[f"{c}{r}"].font = BOLD

    def rng(k):
        return f"${F0}${rows[k]}:${FN}${rows[k]}"

    b = rows["pv"] + 2
    bridge = [
        ("sum_pv", "Sum of PV of FCFF", f"=SUM({rng('pv')})", USD),
        ("tv", "Terminal value at FY2031 (Gordon)",
         f"=${FN}${rows['fcff']}*(1+{DCF_CELLS['g']})/({DCF_CELLS['wacc']}-{DCF_CELLS['g']})", USD),
        ("pv_tv", "PV of terminal value", f"=B{b + 1}*${FN}${rows['df']}", USD),
        ("ev", "Enterprise value", f"=B{b}+B{b + 2}", USD),
        ("tv_share", "Terminal value as % of EV", f"=B{b + 2}/B{b + 3}", PCT),
        ("cash", "Plus: cash and short-term investments (FY2026)",
         f"=BS!{last}{BS['cash']}+BS!{last}{BS['st_investments']}", USD),
        ("less_debt", "Less: total debt (FY2026)", f"=-BS!{last}{BS['total_debt']}", USD),
        ("equity", "Equity value", f"=B{b + 3}+B{b + 5}+B{b + 6}", USD),
        ("shares", "Shares outstanding (m)", f"={ref['shares']}", "#,##0.0"),
        ("per_share", "Equity value per share (USD)", f"=B{b + 7}/B{b + 8}", "0.00"),
        ("price", "Current share price (USD)", f"={ref['price']}", "0.00"),
        ("upside", "Upside / (downside)", f"=B{b + 9}/B{b + 10}-1", PCT),
        ("rating", "Rating (BUY > +10%, SELL < -10%, else HOLD)",
         f'=IF(B{b + 11}>0.1,"BUY",IF(B{b + 11}<-0.1,"SELL","HOLD"))', None),
        ("exit_multiple", "Implied terminal EV/EBITDA (TV / FY2031 EBITDA)", f"=B{b + 1}/IS!{FN}{IS['ebitda']}", X),
    ]
    ws.cell(b - 1, 1, "Enterprise value to equity value").font = BOLD
    for i, (k, label, f, fmt) in enumerate(bridge):
        r = b + i
        ws.cell(r, 1, label)
        ws.cell(r, 2, f)
        if fmt:
            ws.cell(r, 2).number_format = fmt
        DCF_CELLS[k] = f"$B${r}"
        if k in ("ev", "equity", "per_share", "rating"):
            ws.cell(r, 1).font = ws.cell(r, 2).font = BOLD

    # sensitivity grid: value per share for WACC x terminal growth
    s = b + len(bridge) + 2
    ws.cell(s, 1, "Sensitivity: value per share (USD), WACC (rows) × terminal growth (columns)").font = BOLD
    gs = [-0.01, -0.005, 0, 0.005, 0.01]
    ws.cell(s + 1, 1, "WACC \\ g")
    for j, dg in enumerate(gs):
        cell = ws.cell(s + 1, 3 + j, f"={DCF_CELLS['g']}+{dg}")
        cell.number_format, cell.font = "0.0%", BOLD
    for i, dw in enumerate([-0.01, -0.005, 0, 0.005, 0.01]):
        r = s + 2 + i
        wc = ws.cell(r, 2, f"={DCF_CELLS['wacc']}+{dw}")
        wc.number_format, wc.font = "0.0%", BOLD
        for j in range(len(gs)):
            col = get_column_letter(3 + j)
            w, g = f"$B{r}", f"{col}${s + 1}"
            f = (f"=(SUMPRODUCT({rng('counted')}/(1+{w})^{rng('period')})"
                 f"+${FN}${rows['fcff']}*(1+{g})/({w}-{g})/(1+{w})^${FN}${rows['period']}"
                 f"+{DCF_CELLS['cash']}+{DCF_CELLS['less_debt']})/{DCF_CELLS['shares']}")
            ws[f"{col}{r}"] = f
            ws[f"{col}{r}"].number_format = "0.00"
    DCF_CELLS["grid_base"] = f"E{s + 4}"


def write_comps(ws, snapshot: dict, ref: dict):
    ws["A1"] = "Trading comparables (global athletic footwear and apparel)"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = (f"yfinance snapshot {snapshot['as_of']}, last twelve months, local reporting currency. "
                "EV = market cap + total debt (incl. leases) – cash. Negative EBITDA multiples left blank.")
    ws["A2"].font = Font(italic=True, color="666666")
    heads = ["Company", "Ticker", "Currency", "Market cap (m)", "EV (m)", "Revenue (m)", "EBITDA (m)",
             "Net income (m)", "EV/Sales", "EV/EBITDA", "P/E", "Gross margin", "Op. margin", "Rev. growth"]
    for j, t in enumerate(heads):
        cell = ws.cell(4, 1 + j, t)
        cell.font, cell.fill = HEAD, HEAD_FILL
        ws.column_dimensions[get_column_letter(1 + j)].width = 14 if j else 22
    for i, p in enumerate(snapshot["peers"]):
        r = 5 + i
        vals = [p["name"], p["ticker"], p["currency"], p["market_cap"] / 1e6, p["enterprise_value"] / 1e6,
                p["revenue"] / 1e6, p["ebitda"] / 1e6, p["net_income"] / 1e6]
        for j, v in enumerate(vals):
            cell = ws.cell(r, 1 + j, v)
            if j >= 3:
                cell.number_format, cell.font = USD, BLUE
        ws.cell(r, 9, f"=E{r}/F{r}").number_format = X
        ws.cell(r, 10, f'=IF(G{r}>0,E{r}/G{r},"")').number_format = X
        ws.cell(r, 11, f'=IF(H{r}>0,D{r}/H{r},"")').number_format = X
        for j, k in enumerate(["gross_margin", "operating_margin", "revenue_growth"]):
            cell = ws.cell(r, 12 + j, p[k])
            cell.number_format, cell.font = PCT, BLUE
    n = len(snapshot["peers"])
    first, lastr = 6, 4 + n  # peers exclude Nike (row 5)
    stats = [("Peer median (excl. Nike)", "MEDIAN"), ("Peer 25th percentile", "Q1"), ("Peer 75th percentile", "Q3")]
    for i, (label, fn) in enumerate(stats):
        r = lastr + 2 + i
        ws.cell(r, 1, label).font = BOLD
        for col in "IJKLMN":
            rg = f"{col}{first}:{col}{lastr}"
            f = {"MEDIAN": f"=MEDIAN({rg})", "Q1": f"=QUARTILE({rg},1)", "Q3": f"=QUARTILE({rg},3)"}[fn]
            ws[f"{col}{r}"] = f
            ws[f"{col}{r}"].number_format = PCT if col in "LMN" else X
    med = lastr + 2
    r = med + 4
    ws.cell(r, 1, "Implied Nike value per share (USD)").font = BOLD
    net_cash = "(DCF!" + DCF_CELLS["cash"] + "+DCF!" + DCF_CELLS["less_debt"] + ")"
    impl = [
        ("EV/EBITDA, peer median", f"=(J{med}*G5+{net_cash})/{ref['shares']}"),
        ("EV/EBITDA, 25th percentile", f"=(J{med + 1}*G5+{net_cash})/{ref['shares']}"),
        ("EV/EBITDA, 75th percentile", f"=(J{med + 2}*G5+{net_cash})/{ref['shares']}"),
        ("EV/Sales, peer median", f"=(I{med}*F5+{net_cash})/{ref['shares']}"),
        ("EV/Sales, 25th percentile", f"=(I{med + 1}*F5+{net_cash})/{ref['shares']}"),
        ("EV/Sales, 75th percentile", f"=(I{med + 2}*F5+{net_cash})/{ref['shares']}"),
    ]
    for i, (label, f) in enumerate(impl):
        ws.cell(r + 1 + i, 1, label)
        ws.cell(r + 1 + i, 2, f).number_format = "0.00"


def write_cover(ws, snapshot: dict, table: list[m.Valuation], check_row: int):
    ws.column_dimensions["A"].width = 48
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    ws["A1"] = "Nike, Inc. (NYSE: NKE) – 3-statement model and DCF"
    ws["A1"].font = Font(bold=True, size=16)
    ws["A2"] = ("Educational project – not investment advice. Source: Nike Form 10-K filings via SEC EDGAR "
                "XBRL API; market data via yfinance and FRED.")
    ws["A2"].font = Font(italic=True, color="666666")
    live = [
        ("Active scenario", "=Inputs!D4", None),
        ("Value per share, active scenario (USD)", f"=DCF!{DCF_CELLS['per_share']}", "0.00"),
        ("Share price (USD)", f"=DCF!{DCF_CELLS['price']}", "0.00"),
        ("Upside / (downside)", f"=DCF!{DCF_CELLS['upside']}", PCT),
        ("Rating", f"=DCF!{DCF_CELLS['rating']}", None),
        ("Enterprise value (USD m)", f"=DCF!{DCF_CELLS['ev']}", USD),
        ("WACC", f"=DCF!{DCF_CELLS['wacc']}", "0.00%"),
        ("Terminal growth", f"=DCF!{DCF_CELLS['g']}", "0.00%"),
        ("Balance sheet checks (sum of absolute differences, must be 0)", f"=SUMPRODUCT(ABS(BS!B{check_row}:K{check_row}))", USD),
    ]
    ws["A4"] = "Live outputs (change Inputs!C4 to switch scenario)"
    ws["A4"].font = BOLD
    for i, (label, f, fmt) in enumerate(live):
        ws.cell(5 + i, 1, label)
        ws.cell(5 + i, 2, f)
        if fmt:
            ws.cell(5 + i, 2).number_format = fmt
    r = 16
    ws.cell(r, 1, "Scenario summary (values written by the build script)").font = BOLD
    for j, t in enumerate(["Scenario", "Value / share", "Upside", "Rating"]):
        cell = ws.cell(r + 1, 1 + j, t)
        cell.font, cell.fill = HEAD, HEAD_FILL
    for i, v in enumerate(table):
        ws.cell(r + 2 + i, 1, v.scenario)
        ws.cell(r + 2 + i, 2, round(v.per_share, 2)).number_format = "0.00"
        ws.cell(r + 2 + i, 3, round(v.upside, 4)).number_format = PCT
        ws.cell(r + 2 + i, 4, m.verdict(v.upside))
    notes = [
        "Sheets: Inputs (drivers, scenario switch) → IS / BS / CF (linked statements) → DCF → Comps.",
        "Forecast cash is the balancing item: BS cash = CF ending cash; the balance check row must read 0.",
        "Interest is computed on prior-year cash and debt, so the model has no circular reference.",
        "Operating leases stay in operating costs (US GAAP), so lease liabilities are not deducted from EV.",
    ]
    for i, t in enumerate(notes):
        ws.cell(22 + i, 1, t)
