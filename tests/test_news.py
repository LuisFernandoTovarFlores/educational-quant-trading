"""
Tests for news module.
"""

import pytest

from src.news import analyze_sentiment, get_news_summary


def test_analyze_sentiment_empty():
    """Test sentiment analysis with empty news list."""
    news_list = []
    result = analyze_sentiment(news_list)

    assert result['total_articles'] == 0
    assert result['positive'] == 0
    assert result['negative'] == 0
    assert result['neutral'] == 0
    assert result['average_sentiment'] == 0.0
    assert result['sentiment_label'] == 'NEUTRAL'


def test_analyze_sentiment_positive():
    """Test sentiment analysis with positive sentiment."""
    news_list = [
        {'title': 'Good news', 'sentiment': 0.8},
        {'title': 'Great news', 'sentiment': 0.5},
        {'title': 'Excellent', 'sentiment': 0.9},
    ]

    result = analyze_sentiment(news_list)

    assert result['total_articles'] == 3
    assert result['positive'] == 3
    assert result['negative'] == 0
    assert result['neutral'] == 0
    assert result['average_sentiment'] > 0.3
    assert result['sentiment_label'] == 'POSITIVE'


def test_analyze_sentiment_negative():
    """Test sentiment analysis with negative sentiment."""
    news_list = [
        {'title': 'Bad news', 'sentiment': -0.8},
        {'title': 'Terrible news', 'sentiment': -0.6},
        {'title': 'Awful', 'sentiment': -0.9},
    ]

    result = analyze_sentiment(news_list)

    assert result['total_articles'] == 3
    assert result['positive'] == 0
    assert result['negative'] == 3
    assert result['neutral'] == 0
    assert result['average_sentiment'] < -0.3
    assert result['sentiment_label'] == 'NEGATIVE'


def test_analyze_sentiment_mixed():
    """Test sentiment analysis with mixed sentiment."""
    news_list = [
        {'title': 'Good', 'sentiment': 0.5},
        {'title': 'Bad', 'sentiment': -0.5},
        {'title': 'Neutral', 'sentiment': 0.0},
    ]

    result = analyze_sentiment(news_list)

    assert result['total_articles'] == 3
    assert result['positive'] == 1
    assert result['negative'] == 1
    assert result['neutral'] == 1
    assert result['sentiment_label'] == 'NEUTRAL'


def test_analyze_sentiment_no_sentiment_data():
    """Test sentiment analysis when articles have no sentiment data."""
    news_list = [
        {'title': 'News 1', 'sentiment': None},
        {'title': 'News 2', 'sentiment': None},
        {'title': 'News 3', 'sentiment': None},
    ]

    result = analyze_sentiment(news_list)

    assert result['total_articles'] == 3
    assert result['neutral'] == 3
    assert result['average_sentiment'] == 0.0
    assert result['sentiment_label'] == 'NEUTRAL'


@pytest.mark.integration
def test_get_news_summary_structure():
    """Test that get_news_summary returns proper structure."""
    # This test will likely return empty results without API keys configured
    # but we can verify the structure
    result = get_news_summary('AAPL', days=1)

    assert 'ticker' in result
    assert 'days' in result
    assert 'articles' in result
    assert 'total_articles' in result
    assert 'sentiment' in result

    assert result['ticker'] == 'AAPL'
    assert result['days'] == 1
    assert isinstance(result['articles'], list)
    assert isinstance(result['total_articles'], int)
    assert isinstance(result['sentiment'], dict)


def test_sentiment_thresholds():
    """Test sentiment classification thresholds."""
    # Test boundary cases
    news_list = [
        {'title': 'Slightly positive', 'sentiment': 0.25},
        {'title': 'Slightly negative', 'sentiment': -0.25},
        {'title': 'Neutral', 'sentiment': 0.15},
    ]

    result = analyze_sentiment(news_list)

    # 0.25 > 0.2 = positive
    # -0.25 < -0.2 = negative
    # 0.15 is between -0.2 and 0.2 = neutral
    assert result['positive'] == 1
    assert result['negative'] == 1
    assert result['neutral'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
