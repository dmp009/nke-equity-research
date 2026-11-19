import json
from pathlib import Path

import pandas as pd
import pytest

from nkeresearch import model as m
from nkeresearch.sec import historicals

ROOT = Path(__file__).resolve().parents[1]
H = historicals(ROOT / "data/raw/nke_companyfacts.json")
SNAP = json.loads((ROOT / "data/market_snapshot.json").read_text())


def test_historicals_tie_to_reported_totals():
    h = m.notes_payable_plug(H)
    df = h.copy()
    m.add_subtotals(df)
    for y in m.HIST_YEARS:
        assert df.at["total_assets", y] == pytest.approx(H.at["total_assets", y])
        assert df.at["total_liabilities_and_equity", y] == pytest.approx(H.at["total_liabilities_and_equity", y])
        ebt = df.at["ebit", y] + H.at["net_interest_income", y] + H.at["other_income", y]
        assert ebt == pytest.approx(H.at["pretax_income", y])


def test_fy2026_matches_10k():
    assert H.at["revenue", 2026] == 46398
    assert H.at["net_income", 2026] == 3108
    assert H.at["total_assets", 2026] == 38410


@pytest.mark.parametrize("scenario", ["Bear", "Base", "Bull"])
def test_balance_sheet_balances_every_year(scenario):
    df = m.forecast(H, scenario)
    assert df.loc["balance_check"].abs().max() < 1e-6


@pytest.mark.parametrize("scenario", ["Bear", "Base", "Bull"])
def test_cash_flow_reconciles_to_balance_sheet_cash(scenario):
    df = m.forecast(H, scenario)
    for y in [2027, 2028, 2029, 2030, 2031]:
        net = df.at["cfo", y] - df.at["capex", y] - df.at["dividends_paid", y] - df.at["buybacks", y]
        assert df.at["cash", y] - df.at["cash", y - 1] == pytest.approx(net)


def test_gordon_terminal_value_by_hand():
    cf = pd.Series([100.0, 100, 100, 100, 110])
    _, tv = m.enterprise_value(cf, 0.10, 0.02)
    assert tv == pytest.approx(110 * 1.02 / 0.08)


def test_scenarios_are_ordered():
    vals = [m.value(H, SNAP, s)[0].per_share for s in ("Bear", "Base", "Bull")]
    assert vals[0] < vals[1] < vals[2]


def test_wacc_components():
    w = m.wacc(SNAP, 7942)
    assert w.beta == pytest.approx(0.67 * SNAP["beta_raw"] + 0.33)
    assert w.ke == pytest.approx(SNAP["rf"] + w.beta * 0.0428)
    assert w.kd_after_tax < w.wacc < w.ke


@pytest.mark.parametrize("upside,rating", [(0.2, "BUY"), (-0.2, "SELL"), (0.05, "HOLD"), (0.10, "HOLD")])
def test_verdict(upside, rating):
    assert m.verdict(upside) == rating
