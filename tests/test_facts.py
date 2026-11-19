"""Every quoted 10-K figure must appear in the committed 10-K text."""
from pathlib import Path

from nkeresearch import facts as F
from scripts.tenk_text import to_text

TEXT = to_text(Path(__file__).resolve().parents[1] / "data/raw/10k/nke-20260531.htm")


def n(x: int) -> str:
    return f"{x:,}"


def test_segment_revenue_and_ebit_quoted_in_10k():
    for v in list(F.REVENUE_BY_SEGMENT.values()) + list(F.EBIT_BY_SEGMENT.values()):
        assert f"{n(v[0])} $ {n(v[1])}" in TEXT or f"$ {n(v[0])} $ {n(v[1])}" in TEXT


def test_sourcing_and_customer_facts_quoted_in_10k():
    assert "Vietnam, Indonesia and China manufactured approximately 52%, 27% and 16%" in TEXT
    assert "approximately 60% of NIKE Brand foo" in TEXT
    assert "three largest United States customers accounted for approximately 29%" in TEXT
    assert "approximately 73,000 employees" in TEXT
    assert "accounted for approximately 44% of total revenues" in TEXT


def test_channel_product_and_jordan_quoted_in_10k():
    assert "Sales to Wholesale Customers $ 27,453 $ 25,883" in TEXT
    assert "Sales through NIKE Direct 17,720 18,783" in TEXT
    assert "Footwear $ 29,525" in TEXT and "Apparel 13,449" in TEXT and "Equipment 2,199" in TEXT
    assert "Jordan Brand products of $7,034 million" in TEXT
