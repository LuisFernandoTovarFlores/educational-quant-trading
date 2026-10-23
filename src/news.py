"""
News module - Aggregates news from Finnhub and Marketaux.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

import requests

from config.secrets import get_secrets

logger = logging.getLogger(__name__)

FINNHUB_BASE = 'https://finnhub.io/api/v1'
MARKETAUX_URL = 'https://api.marketaux.com/v1/news/all'
REQUEST_TIMEOUT = 10


def get_finnhub_news(symbol: str = 'general', days: int = 7) -> List[Dict]:
    """
    Get news from Finnhub API.

    Args:
        symbol: Ticker symbol or 'general' for market news
        days: Number of days to look back (default: 7)

    Returns:
        List of news articles
    """
    secrets = get_secrets()
    api_key = secrets.get('FINNHUB_API_KEY')

    if not api_key or api_key == 'your_finnhub_api_key_here':
        logger.warning('Finnhub API key not configured')
        return []

    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        if symbol == 'general':
            url = f'{FINNHUB_BASE}/news'
            params = {'category': 'general'}
        else:
            url = f'{FINNHUB_BASE}/company-news'
            params = {
                'symbol': symbol,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
            }

        # Send the token in a header so it never appears in request URLs/logs.
        response = requests.get(
            url,
            params=params,
            headers={'X-Finnhub-Token': api_key},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        articles = response.json()

        # Normalize format
        news_list = []
        for article in articles:
            news_list.append(
                {
                    'source': 'finnhub',
                    'title': article.get('headline', ''),
                    'summary': article.get('summary', ''),
                    'url': article.get('url', ''),
                    'datetime': article.get('datetime', 0),
                    'source_name': article.get('source', ''),
                    'symbol': symbol if symbol != 'general' else None,
                    'sentiment': None,  # Finnhub free tier doesn't include sentiment
                }
            )

        return news_list

    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 'unknown'
        logger.error('Finnhub request failed with HTTP %s', status)
        return []
    except requests.exceptions.RequestException as exc:
        logger.error('Finnhub request failed: %s', exc.__class__.__name__)
        return []
    except Exception as exc:  # noqa: BLE001 - news is optional
        logger.error('Unexpected error fetching Finnhub news: %s', exc.__class__.__name__)
        return []


def get_marketaux_news(tickers: List[str], days: int = 7) -> List[Dict]:
    """
    Get news from Marketaux API with sentiment analysis.

    Args:
        tickers: List of ticker symbols
        days: Number of days to look back (default: 7)

    Returns:
        List of news articles with sentiment
    """
    secrets = get_secrets()
    api_key = secrets.get('MARKETAUX_API_KEY')

    if not api_key or api_key == 'your_marketaux_api_key_here':
        logger.warning('Marketaux API key not configured')
        return []

    try:
        # Calculate date range
        end_date = datetime.now()
        end_date - timedelta(days=days)

        # Marketaux allows multiple tickers separated by comma
        tickers_str = ','.join(tickers)

        url = MARKETAUX_URL
        params = {
            'api_token': api_key,
            'filter_entities': 'true',
            'language': 'en',
            'symbols': tickers_str,
        }

        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        articles = data.get('data', [])

        # Normalize format
        news_list = []
        for article in articles:
            # Extract sentiment if available
            sentiment = None
            if 'entities' in article:
                for entity in article['entities']:
                    if 'sentiment_score' in entity:
                        sentiment = entity.get('sentiment_score')
                        break

            news_list.append(
                {
                    'source': 'marketaux',
                    'title': article.get('title', ''),
                    'summary': article.get('description', ''),
                    'url': article.get('url', ''),
                    'datetime': int(
                        datetime.fromisoformat(
                            article.get('published_at', '').replace('Z', '+00:00')
                        ).timestamp()
                    )
                    if article.get('published_at')
                    else 0,
                    'source_name': article.get('source', ''),
                    'symbol': article.get('symbols', [None])[0] if article.get('symbols') else None,
                    'sentiment': sentiment,
                }
            )

        return news_list

    except requests.exceptions.HTTPError as exc:
        # Never log the exception string: Marketaux's token is a query parameter.
        status = exc.response.status_code if exc.response is not None else 'unknown'
        logger.error('Marketaux request failed with HTTP %s', status)
        return []
    except requests.exceptions.RequestException as exc:
        logger.error('Marketaux request failed: %s', exc.__class__.__name__)
        return []
    except Exception as exc:  # noqa: BLE001 - news is optional
        logger.error('Unexpected error fetching Marketaux news: %s', exc.__class__.__name__)
        return []


def get_portfolio_news(ticker: str, days: int = 7) -> List[Dict]:
    """
    Get aggregated news for a specific ticker from all sources.

    Args:
        ticker: Ticker symbol
        days: Number of days to look back (default: 7)

    Returns:
        List of news articles sorted by date (newest first)
    """
    news_list = []

    # Get from Finnhub
    finnhub_news = get_finnhub_news(symbol=ticker, days=days)
    news_list.extend(finnhub_news)

    # Get from Marketaux
    marketaux_news = get_marketaux_news(tickers=[ticker], days=days)
    news_list.extend(marketaux_news)

    # Sort by datetime (newest first)
    news_list.sort(key=lambda x: x.get('datetime', 0), reverse=True)

    # Remove duplicates based on title
    seen_titles = set()
    unique_news = []
    for article in news_list:
        title = article.get('title', '').lower()
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_news.append(article)

    return unique_news


def get_market_news(days: int = 1) -> List[Dict]:
    """
    Get general market news from all sources.

    Args:
        days: Number of days to look back (default: 1)

    Returns:
        List of news articles sorted by date (newest first)
    """
    news_list = []

    # Get from Finnhub (general news)
    finnhub_news = get_finnhub_news(symbol='general', days=days)
    news_list.extend(finnhub_news)

    # Sort by datetime (newest first)
    news_list.sort(key=lambda x: x.get('datetime', 0), reverse=True)

    return news_list


def analyze_sentiment(news_list: List[Dict]) -> Dict:
    """
    Analyze sentiment from news articles.

    Args:
        news_list: List of news articles

    Returns:
        Dictionary with sentiment analysis
    """
    if not news_list:
        return {
            'total_articles': 0,
            'positive': 0,
            'negative': 0,
            'neutral': 0,
            'average_sentiment': 0.0,
            'sentiment_label': 'NEUTRAL',
        }

    positive = 0
    negative = 0
    neutral = 0
    sentiment_scores = []

    for article in news_list:
        sentiment = article.get('sentiment')

        if sentiment is not None:
            sentiment_scores.append(sentiment)

            if sentiment > 0.2:
                positive += 1
            elif sentiment < -0.2:
                negative += 1
            else:
                neutral += 1
        else:
            # No sentiment data, count as neutral
            neutral += 1

    total = len(news_list)
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0

    # Determine overall sentiment label
    if avg_sentiment > 0.3:
        label = 'POSITIVE'
    elif avg_sentiment < -0.3:
        label = 'NEGATIVE'
    else:
        label = 'NEUTRAL'

    return {
        'total_articles': total,
        'positive': positive,
        'negative': negative,
        'neutral': neutral,
        'average_sentiment': round(avg_sentiment, 3),
        'sentiment_label': label,
    }


def get_news_summary(ticker: str, days: int = 7) -> Dict:
    """
    Get comprehensive news summary for a ticker.

    Args:
        ticker: Ticker symbol
        days: Number of days to look back (default: 7)

    Returns:
        Dictionary with news and sentiment analysis
    """
    news_list = get_portfolio_news(ticker, days)
    sentiment = analyze_sentiment(news_list)

    return {
        'ticker': ticker,
        'days': days,
        'articles': news_list[:10],  # Top 10 most recent
        'total_articles': len(news_list),
        'sentiment': sentiment,
    }


if __name__ == '__main__':
    # Test news fetching
    print('Testing news module...')
    print('=' * 60)

    ticker = 'AAPL'
    print(f'\nFetching news for {ticker}...')

    summary = get_news_summary(ticker, days=7)

    print(f'\nTotal articles: {summary["total_articles"]}')
    print('\nSentiment analysis:')
    print(f'  Positive: {summary["sentiment"]["positive"]}')
    print(f'  Negative: {summary["sentiment"]["negative"]}')
    print(f'  Neutral: {summary["sentiment"]["neutral"]}')
    print(f'  Average sentiment: {summary["sentiment"]["average_sentiment"]}')
    print(f'  Label: {summary["sentiment"]["sentiment_label"]}')

    print('\nTop 5 articles:')
    for i, article in enumerate(summary['articles'][:5], 1):
        print(f'\n{i}. {article["title"]}')
        print(f'   Source: {article["source_name"]}')
        if article.get('sentiment'):
            print(f'   Sentiment: {article["sentiment"]:.2f}')
        print(f'   URL: {article["url"]}')
