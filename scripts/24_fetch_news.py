import requests
from bs4 import BeautifulSoup
import json
import os
import tweepy
import argparse
import logging

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Environment Variables ---
DODGERS_TWITTER_API_KEY = os.environ.get("DODGERS_TWITTER_API_KEY")
DODGERS_TWITTER_API_SECRET = os.environ.get("DODGERS_TWITTER_API_SECRET")
DODGERS_TWITTER_ACCESS_TOKEN = os.environ.get("DODGERS_TWITTER_API_ACCESS_TOKEN")
DODGERS_TWITTER_ACCESS_SECRET = os.environ.get("DODGERS_TWITTER_API_ACCESS_SECRET")

def post_tweet(tweet_text):
    """Posts a tweet."""
    if not all([DODGERS_TWITTER_API_KEY, DODGERS_TWITTER_API_SECRET, DODGERS_TWITTER_ACCESS_TOKEN, DODGERS_TWITTER_ACCESS_SECRET]):
        logging.error("Twitter API credentials are not fully set. Cannot post tweet.")
        return

    try:
        client = tweepy.Client(
            consumer_key=DODGERS_TWITTER_API_KEY,
            consumer_secret=DODGERS_TWITTER_API_SECRET,
            access_token=DODGERS_TWITTER_ACCESS_TOKEN,
            access_token_secret=DODGERS_TWITTER_ACCESS_SECRET
        )
        response = client.create_tweet(text=tweet_text)
        logging.info(f"Tweet posted successfully: {response.data['id']}")
    except Exception as e:
        logging.error(f"Failed to post tweet: {e}")

def fetch_latimes_news():
    """
    Fetches the top Dodgers story from the LA Times.
    """
    url = "https://www.latimes.com/sports/dodgers"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the first promo content div
    promo_content = soup.find('div', class_='promo-content')
    
    if not promo_content:
        print("Could not find the main story promo content.")
        return None
        
    story_data = {}
    
    # Extract title and URL
    title_tag = promo_content.find(['h1', 'h2'], class_='promo-title')
    if title_tag and title_tag.find('a'):
        story_data['title'] = title_tag.find('a').get_text(strip=True)
        story_data['url'] = title_tag.find('a')['href']
    else:
        story_data['title'] = None
        story_data['url'] = None

    # Extract description
    description_tag = promo_content.find('p', class_='promo-description')
    if description_tag:
        story_data['description'] = description_tag.get_text(strip=True)
    else:
        story_data['description'] = None
        
    # Extract time
    time_tag = promo_content.find('time', class_='promo-timestamp')
    if time_tag:
        story_data['time'] = time_tag.get('datetime')
    else:
        story_data['time'] = None

    story_data['source'] = 'LA Times'
    return story_data

def fetch_dodgers_nation_news():
    """
    Fetches the top story from Dodgers Nation.
    """
    url = "https://dodgersnation.com/news/team/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the first post item
    post_item = soup.find('li', class_='post-item')

    if not post_item:
        print("Could not find the main story on Dodgers Nation.")
        return None

    story_data = {}

    # Extract title and URL
    title_tag = post_item.find('h2', class_='post-title')
    if title_tag and title_tag.find('a'):
        story_data['title'] = title_tag.find('a').get_text(strip=True)
        story_data['url'] = title_tag.find('a')['href']
    else:
        story_data['title'] = None
        story_data['url'] = None
    
    # Extract description
    description_tag = post_item.find('p', class_='post-excerpt')
    if description_tag:
        story_data['description'] = description_tag.get_text(strip=True)
    else:
        story_data['description'] = None
    
    # Extract time
    time_tag = post_item.find('span', class_='date')
    if time_tag:
        story_data['time'] = time_tag.get_text(strip=True)
    else:
        story_data['time'] = None

    story_data['source'] = 'Dodgers Nation'
    return story_data

def fetch_mlb_news():
    """
    Fetches the top story from MLB.com.
    """
    url = "https://www.mlb.com/dodgers/news"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the first article item
    article_item = soup.find('li', class_='article-navigation__item')

    if not article_item:
        print("Could not find the main story on MLB.com.")
        return None

    story_data = {}

    # Extract title and URL
    headline_tag = article_item.find('span', class_='article-navigation__item__meta-headline')
    link_tag = article_item.find('a')

    if headline_tag:
        story_data['title'] = headline_tag.get_text(strip=True)
    else:
        story_data['title'] = None

    if link_tag and link_tag.has_attr('href'):
        story_data['url'] = f"https://www.mlb.com{link_tag['href']}"
    else:
        story_data['url'] = None

    # Description and time are not available in the list view
    story_data['description'] = None
    story_data['time'] = None

    story_data['source'] = 'MLB.com'
    return story_data

def format_news_tweet(articles):
    """Formats a list of articles into a tweet."""
    tweet_lines = ["Dodgers news update:"]
    for article in articles:
        if article and article.get('title') and article.get('url'):
            tweet_lines.append(f"- {article['source']}: {article['title']} {article['url']}")
    return "\n\n".join(tweet_lines)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fetch Dodgers news and optionally post to Twitter.")
    parser.add_argument("--post-tweet", action="store_true", help="Post the news roundup to Twitter.")
    args = parser.parse_args()

    articles = []
    
    latimes_news = fetch_latimes_news()
    if latimes_news:
        articles.append(latimes_news)

    dodgers_nation_news = fetch_dodgers_nation_news()
    if dodgers_nation_news:
        articles.append(dodgers_nation_news)
    
    mlb_news = fetch_mlb_news()
    if mlb_news:
        articles.append(mlb_news)

    if articles:
        tweet_text = format_news_tweet(articles)
        print("--- Generated Tweet ---")
        print(tweet_text)

        if args.post_tweet:
            post_tweet(tweet_text)
        else:
            logging.info("Dry run: --post-tweet flag not provided. Not posting to Twitter.")
    else:
        logging.info("No articles found to tweet.") 