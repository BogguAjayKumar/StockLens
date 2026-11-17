"""Local offline news sentiment analysis using a domain-tuned financial lexicon.
No paid APIs or external network calls required.
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from stocklens.data.base import NewsItem


# Domain-specific financial dictionary with polarity weights (-2.0 to +2.0)
FINANCIAL_LEXICON: Dict[str, float] = {
    # Strong Positives (+1.5 to +2.0)
    "multibagger": 2.0,
    "blowout": 1.8,
    "blockbuster": 1.8,
    "record high": 1.7,
    "record profit": 1.7,
    "breakthrough": 1.6,
    "all-time high": 1.6,
    "order win": 1.5,
    "contract win": 1.5,
    "buyback": 1.4,
    "upgrade": 1.4,
    "outperform": 1.4,
    
    # Standard Positives (+0.8 to +1.3)
    "surge": 1.3,
    "beat": 1.2,
    "beats": 1.2,
    "soar": 1.2,
    "soars": 1.2,
    "jump": 1.1,
    "jumps": 1.1,
    "rally": 1.1,
    "rallies": 1.1,
    "growth": 1.0,
    "profit": 1.0,
    "gain": 0.9,
    "gains": 0.9,
    "rise": 0.9,
    "rises": 0.9,
    "boost": 0.9,
    "bullish": 1.2,
    "strong": 1.0,
    "robust": 1.0,
    "stellar": 1.3,
    "dividend": 0.8,
    "expansion": 0.9,
    "partnership": 0.8,
    "recovery": 0.9,
    "rebound": 0.9,
    "acquisition": 0.7,
    "win": 0.9,
    "wins": 0.9,

    # Standard Negatives (-0.8 to -1.3)
    "drop": -0.9,
    "drops": -0.9,
    "fall": -0.9,
    "falls": -0.9,
    "decline": -0.9,
    "declines": -0.9,
    "loss": -1.0,
    "losses": -1.0,
    "miss": -1.1,
    "misses": -1.1,
    "weak": -1.0,
    "downgrade": -1.3,
    "cut": -0.9,
    "cuts": -0.9,
    "slump": -1.2,
    "slumps": -1.2,
    "plunge": -1.3,
    "plunges": -1.3,
    "bearish": -1.2,
    "debt": -0.8,
    "headwind": -0.8,
    "headwinds": -0.8,
    "delay": -0.8,
    "caution": -0.7,
    "cautious": -0.7,
    "subdued": -0.8,

    # Strong Negatives (-1.5 to -2.0)
    "fraud": -2.0,
    "scam": -2.0,
    "default": -1.9,
    "defaults": -1.9,
    "bankruptcy": -2.0,
    "insolvency": -1.9,
    "probe": -1.6,
    "raid": -1.7,
    "scrutiny": -1.4,
    "fine": -1.3,
    "penalty": -1.5,
    "arrest": -1.8,
    "resignation": -1.1,
    "crash": -1.8,
    "collapse": -1.9,
    "banned": -1.6,
    "violation": -1.5,
    "lawsuit": -1.4,
}

INTENSIFIERS: Dict[str, float] = {
    "sharply": 1.5,
    "significantly": 1.4,
    "massively": 1.6,
    "substantially": 1.4,
    "strongly": 1.4,
    "heavily": 1.4,
    "dramatically": 1.5,
    "very": 1.3,
    "slightly": 0.6,
    "marginally": 0.5,
}

NEGATORS: Set[str] = {
    "not", "no", "never", "hardly", "failed", "fails", "unable", "without", "despite"
}


@dataclass
class NewsSentimentResult:
    headline: str
    score: float  # Bounded between -1.0 and +1.0
    sentiment: str  # Strong Positive, Positive, Neutral, Negative, Strong Negative
    matched_keywords: List[str] = field(default_factory=list)


def score_headline(headline: str) -> NewsSentimentResult:
    """Analyze sentiment of a single financial news headline."""
    if not headline or not headline.strip():
        return NewsSentimentResult(headline="", score=0.0, sentiment="Neutral")

    lower = headline.lower()
    # Normalize punctuation
    words = re.findall(r"\b[a-z0-9\-]+\b", lower)
    
    total_score = 0.0
    matched: List[str] = []
    
    # Check multi-word keys first (e.g., "record profit", "all-time high")
    for phrase, weight in FINANCIAL_LEXICON.items():
        if " " in phrase and phrase in lower:
            total_score += weight
            matched.append(phrase)

    # Word-by-word scan with negation & intensifier context window (up to 2 previous words)
    for i, word in enumerate(words):
        if word in FINANCIAL_LEXICON and word not in " ".join(matched):
            weight = FINANCIAL_LEXICON[word]
            
            # Check previous words for negators or intensifiers
            context_window = words[max(0, i - 2) : i]
            negated = any(nw in NEGATORS for nw in context_window)
            
            multiplier = 1.0
            for cw in context_window:
                if cw in INTENSIFIERS:
                    multiplier = INTENSIFIERS[cw]
                    break
            
            final_word_score = (weight * -1.0 if negated else weight) * multiplier
            total_score += final_word_score
            matched.append(f"{'not ' if negated else ''}{word}")

    # Normalize score to [-1.0, 1.0] using hyperbolic tangent or bounded scaling
    normalized_score = max(-1.0, min(1.0, total_score / 3.0)) if matched else 0.0

    if normalized_score >= 0.4:
        label = "Strong Positive"
    elif normalized_score > 0.05:
        label = "Positive"
    elif normalized_score <= -0.4:
        label = "Strong Negative"
    elif normalized_score < -0.05:
        label = "Negative"
    else:
        label = "Neutral"

    return NewsSentimentResult(
        headline=headline,
        score=round(normalized_score, 2),
        sentiment=label,
        matched_keywords=matched,
    )


def score_news_batch(items: List[NewsItem]) -> List[NewsSentimentResult]:
    """Score a list of NewsItem objects and update their sentiment attributes."""
    results: List[NewsSentimentResult] = []
    for item in items:
        res = score_headline(item.title)
        item.sentiment = res.sentiment
        item.sentiment_score = res.score
        results.append(res)
    return results
