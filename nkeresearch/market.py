"""Market data snapshot: share price, beta, risk-free rate and trading peers.

Run once with network access; the result is committed as data/market_snapshot.json
so every later build is reproducible offline.
"""
from __future__ import annotations

import io
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests

PEERS = {
    "NKE": "Nike",
    "ADS.DE": "Adidas",
    "PUM.DE": "Puma",
    "2020.HK": "Anta Sports",
    "7936.T": "Asics",
    "LULU": "Lululemon",
    "DECK": "Deckers (Hoka, UGG)",
    "ONON": "On Holding",
}
FRED_DGS10 = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"


def regress_beta(stock: pd.Series, index: pd.Series) -> float:
    """OLS beta of weekly stock returns on weekly index returns."""
    r = pd.concat([stock, index], axis=1).pct_change().dropna()
    cov = np.cov(r.iloc[:, 0], r.iloc[:, 1])
    return float(cov[0, 1] / cov[1, 1])


def fetch_rf() -> tuple[float, str]:
    text = requests.get(FRED_DGS10, timeout=30).text
    df = pd.read_csv(io.StringIO(text))
    df.columns = ["date", "rate"]
    df = df[pd.to_numeric(df["rate"], errors="coerce").notna()]
    last = df.iloc[-1]
    return float(last["rate"]) / 100, str(last["date"])


def fx_rate(src: str, dst: str) -> float:
    import yfinance as yf

    if src == dst:
        return 1.0
    return float(yf.Ticker(f"{src}{dst}=X").history(period="5d")["Close"].iloc[-1])


def peer_row(ticker: str) -> dict:
    import yfinance as yf

    info = yf.Ticker(ticker).info
    quote, fin = info.get("currency"), info.get("financialCurrency") or info.get("currency")
    # market cap is in the quote currency; debt, cash, revenue and EBITDA in the reporting one
    fx = fx_rate(quote, fin)
    mcap = info.get("marketCap")
    # own EV (yfinance's EV mixes currencies for some dual-currency listings)
    ev = mcap * fx + (info.get("totalDebt") or 0) - (info.get("totalCash") or 0) if mcap else None
    return {
        "ticker": ticker,
        "name": PEERS[ticker],
        "currency": fin,
        "market_cap": mcap * fx if mcap else None,
        "enterprise_value": ev,
        "revenue": info.get("totalRevenue"),
        "ebitda": info.get("ebitda"),
        "net_income": info.get("netIncomeToCommon"),
        "gross_margin": info.get("grossMargins"),
        "operating_margin": info.get("operatingMargins"),
        "revenue_growth": info.get("revenueGrowth"),
        "forward_pe": info.get("forwardPE"),
        "market_cap_usd": mcap * fx_rate(quote, "USD") if mcap else None,
    }


def build_snapshot() -> dict:
    import yfinance as yf

    px = yf.download(["NKE", "^GSPC"], period="2y", interval="1wk", auto_adjust=True, progress=False)["Close"]
    beta = regress_beta(px["NKE"], px["^GSPC"])
    daily = yf.Ticker("NKE").history(period="5d")["Close"]
    rf, rf_date = fetch_rf()
    info = yf.Ticker("NKE").info
    hist = yf.Ticker("NKE").history(period="5y", interval="1mo", auto_adjust=True)["Close"]
    return {
        "as_of": date.today().isoformat(),
        "price": round(float(daily.iloc[-1]), 2),
        "price_date": str(daily.index[-1].date()),
        "week52_low": info.get("fiftyTwoWeekLow"),
        "week52_high": info.get("fiftyTwoWeekHigh"),
        "beta_raw": round(beta, 3),
        "beta_window": "2y weekly vs S&P 500",
        "rf": rf,
        "rf_date": rf_date,
        "rf_source": "US 10Y Treasury constant maturity (FRED DGS10)",
        "price_history": {str(k.date()): round(float(v), 2) for k, v in hist.items()},
        "peers": [peer_row(t) for t in PEERS],
    }


def load_snapshot(path: Path) -> dict:
    return json.loads(Path(path).read_text())


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "market_snapshot.json"
    out.write_text(json.dumps(build_snapshot(), indent=2))
    print(out)
