"""Recalculate the Excel workbook with the `formulas` engine and compare with the Python model."""
import json
import shutil
from pathlib import Path

import pytest

from nkeresearch import model as m
from nkeresearch.excel import DCF_CELLS, write_workbook
from nkeresearch.sec import historicals

ROOT = Path(__file__).resolve().parents[1]


def calc(path: Path) -> dict:
    import formulas

    sol = formulas.ExcelModel().loads(str(path)).finish().calculate()
    out = {}
    for k, v in sol.items():
        if "!" in k and ":" not in k:
            sheet, cell = k.split("]")[1].split("!")
            name = sheet.strip("'").upper()
            out[f"{name}!{cell.replace('$', '')}"] = v.value[0][0]
    return out


@pytest.mark.slow
def test_excel_matches_python_model(tmp_path):
    h = historicals(ROOT / "data/raw/nke_companyfacts.json")
    snap = json.loads((ROOT / "data/market_snapshot.json").read_text())
    base = m.value(h, snap, "Base")[0]
    p = write_workbook(h, snap, tmp_path / "model.xlsx", [base])
    shutil.copy(p, tmp_path / "m.xlsx")
    v = calc(tmp_path / "m.xlsx")

    def cell(name):
        return v["DCF!" + DCF_CELLS[name].replace("$", "")]

    assert cell("per_share") == pytest.approx(base.per_share, rel=1e-9)
    assert cell("ev") == pytest.approx(base.ev, rel=1e-9)
    assert cell("rating") == m.verdict(base.upside)
    checks = [x for k, x in v.items() if k.startswith("COVER!B13")]
    assert checks and abs(checks[0]) < 1e-6
    # the base cell of the sensitivity grid equals the headline value
    assert v["DCF!" + DCF_CELLS["grid_base"]] == pytest.approx(base.per_share, rel=1e-9)
