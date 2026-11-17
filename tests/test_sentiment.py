"""Unit tests for offline financial news sentiment analyzer."""
from stocklens.analysis.sentiment import score_headline, score_news_batch
from stocklens.data.base import NewsItem


def test_positive_headlines():
    """Verify positive and strong positive headlines."""
    res1 = score_headline("Infosys wins record $1 billion cloud transformation deal, net profit surges")
    assert res1.score > 0.3
    assert res1.sentiment in ["Positive", "Strong Positive"]
    assert "wins" in res1.matched_keywords or "surge" in res1.matched_keywords or "profit" in res1.matched_keywords

    res2 = score_headline("TCS beats quarterly revenue estimates with stellar growth")
    assert res2.score > 0.2
    assert res2.sentiment in ["Positive", "Strong Positive"]


def test_negative_headlines():
    """Verify negative and strong negative headlines."""
    res1 = score_headline("Company faces massive fraud probe and regulatory penalty")
    assert res1.score < -0.3
    assert res1.sentiment in ["Negative", "Strong Negative"]
    assert any("fraud" in kw or "penalty" in kw for kw in res1.matched_keywords)

    res2 = score_headline("Quarterly net profit falls 15% amid demand slump and margin decline")
    assert res2.score < -0.2
    assert res2.sentiment in ["Negative", "Strong Negative"]


def test_negation_inversion():
    """Verify that negations ('not', 'failed to') correctly flip polarity."""
    # 'fall' is negative, but 'did not fall' should not be negative
    res_negated = score_headline("Operating profit did not fall despite macro headwinds")
    assert any("not fall" in kw for kw in res_negated.matched_keywords)

    # 'grow' or 'surge' is positive, but 'failed to rise' should invert
    res_failed = score_headline("Company failed to rise to expectations, revenues plunge")
    assert res_failed.score < 0


def test_neutral_headline():
    """Verify neutral or informative headline without sentiment keywords."""
    res = score_headline("Company announces annual general meeting schedule for next month")
    assert res.score == 0.0
    assert res.sentiment == "Neutral"


def test_batch_scoring():
    """Verify batch news scoring correctly updates NewsItem objects."""
    items = [
        NewsItem(title="Record profit beat for Tech Corp"),
        NewsItem(title="Probe initiated into accounting violation"),
        NewsItem(title="Board meeting scheduled on Monday"),
    ]
    results = score_news_batch(items)
    assert len(results) == 3
    assert items[0].sentiment in ["Positive", "Strong Positive"]
    assert items[1].sentiment in ["Negative", "Strong Negative"]
    assert items[2].sentiment == "Neutral"
