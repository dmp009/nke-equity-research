"""Build every deliverable from the committed snapshots: Excel model, pitch deck, deep-dive charts."""
import json
from pathlib import Path

from nkeresearch import deck, industry
from nkeresearch import model as m
from nkeresearch.excel import write_workbook
from nkeresearch.sec import historicals

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    h = historicals(ROOT / "data/raw/nke_companyfacts.json")
    snap = json.loads((ROOT / "data/market_snapshot.json").read_text())
    table = [m.value(h, snap, s)[0] for s in ("Bear", "Base", "Bull")]
    write_workbook(h, snap, ROOT / "outputs/NKE_3statement_DCF.xlsx", table)
    summary = deck.build(h, snap, ROOT / "outputs")
    industry.charts(snap, ROOT / "docs/img")
    (ROOT / "outputs/summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
