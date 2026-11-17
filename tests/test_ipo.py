"""Unit tests for Indian IPO Tracker and Outcome Explainer."""
from stocklens.analysis.ipo import fetch_ipos, IPOItem


def test_fetch_ipos_structure():
    """Verify IPO objects contain complete issue parameters and outcome explanations."""
    ipos = fetch_ipos()
    assert len(ipos) > 0
    for ipo in ipos:
        assert isinstance(ipo, IPOItem)
        assert ipo.company_name
        assert ipo.category in ["Mainboard", "SME"]
        assert ipo.lot_size > 0
        assert ipo.issue_size_cr > 0
        assert len(ipo.verdict) > 0
        assert len(ipo.detailed_outcome) > 10


def test_ipo_gmp_and_subscription():
    """Verify IPO demand multiplier and GMP logic."""
    ipos = fetch_ipos()
    high_gmp_ipos = [i for i in ipos if i.gmp_percent >= 30.0]
    for ipo in high_gmp_ipos:
        assert "High" in ipo.verdict or "Listing" in ipo.verdict
