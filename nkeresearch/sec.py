"""Historical financial statements from the SEC EDGAR XBRL company-facts API (Nike, CIK 320187)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests

CIK = "0000320187"
URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"
# SEC asks automated clients for a User-Agent; a generic one is used on purpose
USER_AGENT = "nke-equity-research portfolio-project admin@example.com"
YEARS = [2022, 2023, 2024, 2025, 2026]  # Nike fiscal years end on 31 May

# model line -> XBRL tags (first tag with a value wins). Signs follow the 10-K presentation.
TAGS = {
    # income statement (flows)
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue"],
    "demand_creation": ["MarketingAndAdvertisingExpense"],
    "operating_overhead": ["GeneralAndAdministrativeExpense"],
    "net_interest_income": ["InterestIncomeExpenseNonoperatingNet"],
    "other_income": ["OtherNonoperatingIncomeExpense"],
    "pretax_income": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
    "income_tax": ["IncomeTaxExpenseBenefit"],
    "net_income": ["NetIncomeLoss"],
    "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    # cash flow (flows)
    "d_and_a": ["DepreciationDepletionAndAmortization", "Depreciation"],
    "sbc": ["ShareBasedCompensation"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "dividends_paid": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    # balance sheet (instants)
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "st_investments": ["DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent", "ShortTermInvestments"],
    "receivables": ["AccountsReceivableNetCurrent"],
    "inventories": ["InventoryFinishedGoodsNetOfReserves", "InventoryNet"],
    "prepaid_other_current": ["PrepaidExpenseAndOtherAssetsCurrent"],
    "total_current_assets": ["AssetsCurrent"],
    "ppe_net": ["PropertyPlantAndEquipmentNet"],
    "rou_assets": ["OperatingLeaseRightOfUseAsset"],
    "intangibles": ["IntangibleAssetsNetExcludingGoodwill"],
    "goodwill": ["Goodwill"],
    "other_noncurrent_assets": ["DeferredIncomeTaxesAndOtherAssetsNoncurrent"],
    "total_assets": ["Assets"],
    "current_debt": ["LongTermDebtCurrent"],
    "notes_payable": ["ShortTermBorrowings"],
    "payables": ["AccountsPayableCurrent"],
    "lease_liab_current": ["OperatingLeaseLiabilityCurrent"],
    "accrued_liabilities": ["AccruedLiabilitiesCurrent"],
    "income_taxes_payable": ["AccruedIncomeTaxesCurrent"],
    "total_current_liabilities": ["LiabilitiesCurrent"],
    "long_term_debt": ["LongTermDebtNoncurrent"],
    "lease_liab_noncurrent": ["OperatingLeaseLiabilityNoncurrent"],
    "other_noncurrent_liabilities": ["DeferredIncomeTaxesAndOtherLiabilitiesNoncurrent"],
    "equity": ["StockholdersEquity"],
    "total_liabilities_and_equity": ["LiabilitiesAndStockholdersEquity"],
}


def download(path: Path) -> None:
    r = requests.get(URL, headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    Path(path).write_text(r.text)


def _value(facts: dict, tag: str, fy: int) -> float | None:
    """Latest-filed 10-K value for the fiscal year ending 31 May `fy` (annual duration or instant)."""
    node = facts.get(tag)
    if not node:
        return None
    end = f"{fy}-05-31"
    rows = [
        x for u in node["units"].values() for x in u
        if x.get("form") == "10-K" and x["end"] == end
        and ("start" not in x or pd.Timestamp(end) - pd.Timestamp(x["start"]) > pd.Timedelta(days=350))
    ]
    if not rows:
        return None
    return float(max(rows, key=lambda x: x["filed"])["val"])


def historicals(path: Path) -> pd.DataFrame:
    """One row per model line, one column per fiscal year, in USD millions. Missing items are 0."""
    facts = json.loads(Path(path).read_text())["facts"]["us-gaap"]
    data = {}
    for line, tags in TAGS.items():
        vals = {}
        for fy in YEARS:
            v = next((x for x in (_value(facts, t, fy) for t in tags) if x is not None), None)
            vals[fy] = 0.0 if v is None else v / 1e6
        data[line] = vals
    return pd.DataFrame(data).T[YEARS]
