"""Three-statement forecast and DCF, in USD millions.

This is the reference implementation. The Excel workbook (excel.py) writes the same
logic as live formulas; tests/test_excel_ties.py checks both give the same answer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from nkeresearch.assumptions import BUYBACKS, COMMON, DRIVERS, FORECAST_YEARS, VALUATION

HIST_YEARS = [2022, 2023, 2024, 2025, 2026]


def notes_payable_plug(h: pd.DataFrame) -> pd.DataFrame:
    """Notes payable & other current liabilities = reported current liabilities - listed items."""
    h = h.copy()
    listed = ["current_debt", "payables", "lease_liab_current", "accrued_liabilities", "income_taxes_payable"]
    h.loc["notes_payable"] = h.loc["total_current_liabilities"] - h.loc[listed].sum()
    return h


def forecast(h: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """Return historical + forecast lines (rows) by fiscal year (columns)."""
    h = notes_payable_plug(h)
    f = pd.DataFrame(0.0, index=h.index, columns=FORECAST_YEARS)
    df = pd.concat([h, f], axis=1)
    c = COMMON
    for i, y in enumerate(FORECAST_YEARS):
        p = y - 1
        d = {k: v[scenario][i] for k, v in DRIVERS.items()}
        rev = df.at["revenue", p] * (1 + d["revenue_growth"])
        cogs = rev * (1 - d["gross_margin"])
        dc = rev * d["demand_creation_pct"]
        oh = rev * d["overhead_pct"]
        ebit = rev - cogs - dc - oh
        debt_prev = df.loc[["current_debt", "notes_payable", "long_term_debt"], p].sum()
        cash_prev = df.loc[["cash", "st_investments"], p].sum()
        nii = cash_prev * c["cash_yield"] - debt_prev * c["cost_of_debt_pretax"]
        ebt = ebit + nii
        tax = ebt * c["tax_rate"]
        ni = ebt - tax
        da, capex, sbc = rev * c["d_and_a_pct"], rev * c["capex_pct"], rev * c["sbc_pct"]
        div = df.at["dividends_paid", p] * (1 + c["dividend_growth"])
        bb = BUYBACKS[scenario][i]
        vals = {
            "revenue": rev, "cogs": cogs, "demand_creation": dc, "operating_overhead": oh,
            "net_interest_income": nii, "other_income": 0.0, "pretax_income": ebt,
            "income_tax": tax, "net_income": ni, "d_and_a": da, "sbc": sbc, "capex": capex,
            "dividends_paid": div, "buybacks": bb,
            "receivables": rev * c["receivable_days"] / 365,
            "inventories": cogs * c["inventory_days"] / 365,
            "prepaid_other_current": rev * c["prepaid_pct"],
            "payables": cogs * c["payable_days"] / 365,
            "accrued_liabilities": rev * c["accrued_pct"],
            "ppe_net": df.at["ppe_net", p] + capex - da,
            "equity": df.at["equity", p] + ni + sbc - div - bb,
        }
        flat = ["st_investments", "rou_assets", "intangibles", "goodwill", "other_noncurrent_assets",
                "current_debt", "notes_payable", "lease_liab_current", "income_taxes_payable",
                "long_term_debt", "lease_liab_noncurrent", "other_noncurrent_liabilities"]
        for k in flat:
            vals[k] = df.at[k, p]
        d_nwc = sum(vals[k] - df.at[k, p] for k in ["receivables", "inventories", "prepaid_other_current"]) \
            - sum(vals[k] - df.at[k, p] for k in ["payables", "accrued_liabilities"])
        vals["cfo"] = ni + da + sbc - d_nwc
        vals["cash"] = df.at["cash", p] + vals["cfo"] - capex - div - bb
        for k, v in vals.items():
            df.at[k, y] = v
        df.at["diluted_shares", y] = df.at["diluted_shares", p]
    add_subtotals(df)
    return df


def add_subtotals(df: pd.DataFrame) -> None:
    df.loc["gross_profit"] = df.loc["revenue"] - df.loc["cogs"]
    df.loc["ebit"] = df.loc["gross_profit"] - df.loc["demand_creation"] - df.loc["operating_overhead"]
    df.loc["ebitda"] = df.loc["ebit"] + df.loc["d_and_a"]
    ca = ["cash", "st_investments", "receivables", "inventories", "prepaid_other_current"]
    nca = ["ppe_net", "rou_assets", "intangibles", "goodwill", "other_noncurrent_assets"]
    cl = ["current_debt", "notes_payable", "payables", "lease_liab_current", "accrued_liabilities",
          "income_taxes_payable"]
    ncl = ["long_term_debt", "lease_liab_noncurrent", "other_noncurrent_liabilities"]
    df.loc["total_current_assets"] = df.loc[ca].sum()
    df.loc["total_assets"] = df.loc[ca + nca].sum()
    df.loc["total_current_liabilities"] = df.loc[cl].sum()
    df.loc["total_liabilities_and_equity"] = df.loc[cl + ncl + ["equity"]].sum()
    df.loc["balance_check"] = df.loc["total_assets"] - df.loc["total_liabilities_and_equity"]
    df.loc["nwc"] = df.loc[["receivables", "inventories", "prepaid_other_current"]].sum() \
        - df.loc[["payables", "accrued_liabilities"]].sum()
    df.loc["total_debt"] = df.loc[["current_debt", "notes_payable", "long_term_debt"]].sum()


def stub_fraction() -> float:
    """Share of FY2027 still ahead of the valuation date."""
    v = date.fromisoformat(VALUATION["valuation_date"])
    fye = date.fromisoformat(VALUATION["fiscal_year_end"])
    return (fye - v).days / 365


@dataclass
class Wacc:
    rf: float
    beta_raw: float
    beta: float
    erp: float
    ke: float
    kd_after_tax: float
    weight_debt: float
    wacc: float


def wacc(snapshot: dict, total_debt: float) -> Wacc:
    beta = 0.67 * snapshot["beta_raw"] + 0.33  # Blume adjustment
    ke = snapshot["rf"] + beta * VALUATION["erp"]
    kd = COMMON["cost_of_debt_pretax"] * (1 - VALUATION["marginal_tax_rate"])
    mcap = snapshot["peers"][0]["market_cap"] / 1e6
    wd = total_debt / (total_debt + mcap)
    return Wacc(snapshot["rf"], snapshot["beta_raw"], beta, VALUATION["erp"], ke, kd, wd,
                (1 - wd) * ke + wd * kd)


def shares_outstanding(snapshot: dict) -> float:
    """Basic shares (m) implied by market cap / price on the snapshot date."""
    return snapshot["peers"][0]["market_cap"] / snapshot["price"] / 1e6


def fcff(df: pd.DataFrame) -> pd.Series:
    yrs = FORECAST_YEARS
    d_nwc = df.loc["nwc", yrs].values - df.loc["nwc", [y - 1 for y in yrs]].values
    nopat = df.loc["ebit", yrs] * (1 - COMMON["tax_rate"])
    return nopat + df.loc["d_and_a", yrs] - df.loc["capex", yrs] - d_nwc


def discount_periods() -> np.ndarray:
    s = stub_fraction()
    return np.array([s + i for i in range(len(FORECAST_YEARS))])


def enterprise_value(cf: pd.Series, w: float, g: float) -> tuple[float, float]:
    """PV of FCFF (FY2027 pro-rated for the stub) + PV of Gordon terminal value."""
    t = discount_periods()
    flows = cf.values.copy()
    flows[0] *= stub_fraction()
    pv = float(np.sum(flows / (1 + w) ** t))
    tv = cf.values[-1] * (1 + g) / (w - g)
    return pv + tv / (1 + w) ** t[-1], tv


@dataclass
class Valuation:
    scenario: str
    ev: float
    pv_tv_share: float
    equity: float
    per_share: float
    upside: float
    tv: float


def value(h: pd.DataFrame, snapshot: dict, scenario: str, w: float | None = None,
          g: float | None = None) -> tuple[Valuation, pd.DataFrame]:
    df = forecast(h, scenario)
    last = df[2026]
    if w is None:
        w = wacc(snapshot, last["total_debt"]).wacc
    g = VALUATION["terminal_growth"] if g is None else g
    cf = fcff(df)
    ev, tv = enterprise_value(cf, w, g)
    equity = ev + last["cash"] + last["st_investments"] - last["total_debt"]
    ps = equity / shares_outstanding(snapshot)
    pv_tv = tv / (1 + w) ** discount_periods()[-1]
    return Valuation(scenario, ev, pv_tv / ev, equity, ps, ps / snapshot["price"] - 1, tv), df


def verdict(upside: float) -> str:
    if upside > 0.10:
        return "BUY"
    if upside < -0.10:
        return "SELL"
    return "HOLD"
