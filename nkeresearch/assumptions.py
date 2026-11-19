"""Forecast drivers per scenario (FY2027E-FY2031E) and valuation inputs.

Every number here is an analyst judgement; the rationale for each driver is in
docs/assumptions.md. The Excel model writes these as blue input cells.
"""

FORECAST_YEARS = [2027, 2028, 2029, 2030, 2031]
SCENARIOS = ["Bear", "Base", "Bull"]

# driver -> scenario -> one value per forecast year
DRIVERS = {
    "revenue_growth": {
        "Bear": [-0.05, 0.00, 0.02, 0.03, 0.03],
        "Base": [-0.02, 0.03, 0.05, 0.05, 0.04],
        "Bull": [0.00, 0.06, 0.07, 0.07, 0.06],
    },
    "gross_margin": {
        "Bear": [0.410, 0.410, 0.415, 0.420, 0.420],
        "Base": [0.420, 0.425, 0.435, 0.440, 0.445],
        "Bull": [0.430, 0.440, 0.450, 0.455, 0.460],
    },
    "demand_creation_pct": {
        "Bear": [0.105, 0.105, 0.105, 0.105, 0.105],
        "Base": [0.103, 0.103, 0.103, 0.103, 0.103],
        "Bull": [0.102, 0.102, 0.102, 0.102, 0.102],
    },
    "overhead_pct": {
        "Bear": [0.250, 0.250, 0.245, 0.245, 0.245],
        "Base": [0.245, 0.240, 0.235, 0.230, 0.230],
        "Bull": [0.240, 0.230, 0.225, 0.220, 0.220],
    },
}

# drivers shared by all scenarios (single value applied to every forecast year)
COMMON = {
    "tax_rate": 0.20,  # FY2026 effective rate 20.3%
    "d_and_a_pct": 0.016,  # % of revenue, FY2022-26 average 1.6%
    "capex_pct": 0.016,  # % of revenue, FY2022-26 average 1.6%
    "sbc_pct": 0.015,  # % of revenue, treated as a real cost (not added back to FCFF)
    "receivable_days": 44.0,  # on revenue; FY2026 46.7 inflated by tariff refund claims
    "inventory_days": 100.0,  # on COGS; FY2026 103
    "payable_days": 50.0,  # on COGS; FY2026 49.6
    "prepaid_pct": 0.046,  # % of revenue
    "accrued_pct": 0.131,  # % of revenue
    "cash_yield": 0.035,  # interest earned on prior-year cash and short-term investments
    "cost_of_debt_pretax": 0.0597,  # rf + 90 bp spread (A-rated); also the interest rate on debt
    "dividend_growth": 0.03,  # growth of total dividends paid
}

BUYBACKS = {  # USD m per forecast year
    "Bear": [0, 0, 0, 500, 500],
    "Base": [0, 500, 1000, 1500, 1500],
    "Bull": [0, 1000, 2000, 2500, 3000],
}

VALUATION = {
    "erp": 0.0428,  # Damodaran implied ERP, S&P 500, 1 Aug 2026
    "erp_source": "Damodaran implied ERP (S&P 500), 1 Aug 2026",
    "terminal_growth": 0.025,
    "marginal_tax_rate": 0.21,  # US federal statutory rate, for the debt tax shield
    "valuation_date": "2026-11-20",
    "fiscal_year_end": "2027-05-31",
}
