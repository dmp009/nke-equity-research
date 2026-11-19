# Assumptions and how to defend them

Every number below is a blue input cell in `outputs/NKE_3statement_DCF.xlsx` (sheet `Inputs`) and
lives in `nkeresearch/assumptions.py`. FY = fiscal year ending 31 May.

## Scenario drivers (FY2027E → FY2031E)

| Driver | Bear | Base | Bull | Why the base case |
|---|---|---|---|---|
| Revenue growth | −5%, 0%, 2%, 3%, 3% | −2%, 3%, 5%, 5%, 4% | 0%, 6%, 7%, 7%, 6% | The latest quarter is still −4% y/y, so FY2027 starts negative. After that the base case returns to Nike's FY2022–24 growth rate (+4.9% CAGR), not above it |
| Gross margin | 41.0% → 42.0% | 42.0% → 44.5% | 43.0% → 46.0% | FY2026 was 42.9%. Less clearance and a better channel mix bring it back toward the 44.6% of FY2024, still below the 46.0% of FY2022 |
| Demand creation, % revenue | 10.5% | 10.3% | 10.2% | FY2026 was 10.2%. Kept flat: Nike needs to keep investing in marketing to regain brand heat |
| Operating overhead, % revenue | 25.0% → 24.5% | 24.5% → 23.0% | 24.0% → 22.0% | FY2026 was 24.5%. Operating leverage as revenue grows on a largely fixed cost base (FY2024 was 23.9%) |
| Buybacks (USD m) | 0 → 500 | 0 → 1,500 | 0 → 3,000 | Paused in FY2026 (USD 146m vs about USD 3–5bn a year before). They restart gradually once FCF recovers |

## Common drivers

| Driver | Value | Basis |
|---|---|---|
| Effective tax rate | 20% | FY2026: 20.3% |
| D&A and capex, % revenue | 1.6% each | FY2022–26 averages; capex = D&A means a stable asset base |
| Stock-based compensation | 1.5% of revenue | FY2026: 1.5%. Treated as a real cost: it is **not** added back to FCFF |
| Receivable / inventory / payable days | 44 / 100 / 50 | FY2026: 46.7 / 103 / 49.6. Receivables were inflated by USD 684m of import-duty recovery claims |
| Accrued liabilities, prepaid | 13.1% / 4.6% of revenue | FY2026 ratios |
| Interest | 3.5% yield on cash, 5.97% on debt | Computed on prior-year balances, so there is no circular reference |
| Dividends | +3% a year | Nike has raised its dividend every year for more than two decades |
| Debt | Held flat (USD 7.9bn) | The USD 2.0bn FY2027 maturity is assumed refinanced |

## Cost of capital

| Input | Value | Source |
|---|---|---|
| Risk-free rate | 5.07% | US 10-year Treasury, FRED series DGS10, 18 Nov 2026 |
| Raw beta | 1.02 | 2 years of weekly returns vs the S&P 500 |
| Adjusted beta | 1.01 | Blume: 0.67 × raw + 0.33 |
| Equity risk premium | 4.28% | Damodaran implied ERP for the S&P 500, 1 Aug 2026 |
| Pre-tax cost of debt | 5.97% | Risk-free + 90 bp, a typical spread for an A-rated issuer |
| Debt weight | 13.5% | Market value of equity vs book debt |
| **WACC** | **8.77%** | |
| Terminal growth | 2.5% | Below long-run US nominal GDP growth |

## Modelling choices an interviewer will ask about

- **Why does FY2027 count for only 53%?** The valuation date is 20 Nov 2026, so only the part of
  FY2027 after that date is still to come. The model counts that part (stub period) and discounts
  each cash flow from the valuation date.
- **Why not subtract lease liabilities?** Under US GAAP, operating lease costs stay in operating
  expenses, so FCFF is already after rent. Subtracting the lease liabilities as well would count
  them twice.
- **Why is cash the balancing item?** The forecast balance sheet balances by construction: cash on
  the balance sheet equals ending cash on the cash flow statement. The `Balance check` row proves
  it, and a test fails if it is not zero.
- **Why is the terminal value 79% of EV?** It is typical for a mature brand. The sensitivity grid
  shows the range, and the implied exit multiple (11.0x FY2031 EBITDA) is in line with Adidas
  (11.3x) and below Asics and On.
