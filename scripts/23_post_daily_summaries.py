#!/usr/bin/env python
# coding: utf-8

"""
Fetches daily team summary data and posts updates to Twitter.
"""

import os
import re
import json
import argparse
import logging
from datetime import datetime
import requests
import tweepy
import boto3
from botocore.exceptions import ClientError
from zoneinfo import ZoneInfo

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Environment Variables & AWS/S3 ---
DODGERS_TWITTER_API_KEY = os.environ.get("DODGERS_TWITTER_API_KEY")
DODGERS_TWITTER_API_SECRET = os.environ.get("DODGERS_TWITTER_API_SECRET")
DODGERS_TWITTER_ACCESS_TOKEN = os.environ.get("DODGERS_TWITTER_API_ACCESS_TOKEN")
DODGERS_TWITTER_ACCESS_SECRET = os.environ.get("DODGERS_TWITTER_API_ACCESS_SECRET")

is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
s3_bucket_name = "stilesdata.com"

if is_github_actions:
    session = boto3.Session(
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name="us-west-1"
    )
    logging.info("Running in GitHub Actions. Using environment variables for AWS credentials.")
else:
    profile_name = os.environ.get("AWS_PERSONAL_PROFILE", "haekeo")
    session = boto3.Session(profile_name=profile_name, region_name="us-west-1")
    logging.info(f"Running locally. Using AWS profile: {profile_name}")

s3_resource = session.resource("s3")

# --- Twitter & S3 Functions ---
def get_last_tweet_date(tweet_type):
    """Reads the last tweet date for a given type from S3."""
    s3_key = f"dodgers/data/tweets/last_tweet_date_{tweet_type}.txt"
    try:
        obj = s3_resource.Object(s3_bucket_name, s3_key)
        last_date_str = obj.get()['Body'].read().decode('utf-8').strip()
        logging.info(f"Last tweet date for '{tweet_type}' found in S3: {last_date_str}")
        return last_date_str
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logging.info(f"{s3_key} not found. This is expected for the first run of the day.")
            return None
        else:
            logging.error(f"An unexpected S3 error occurred in get_last_tweet_date: {e}")
            raise

def set_last_tweet_date(date_str, tweet_type):
    """Writes the last tweet date for a given type to S3."""
    s3_key = f"dodgers/data/tweets/last_tweet_date_{tweet_type}.txt"
    try:
        obj = s3_resource.Object(s3_bucket_name, s3_key)
        obj.put(Body=date_str)
        logging.info(f"Successfully updated last tweet date in S3 for '{tweet_type}' to: {date_str}")
    except Exception as e:
        logging.error(f"Failed to write last tweet date to S3: {e}")

def post_tweet(tweet_text, tweet_type):
    """Posts a tweet and updates the last tweet date on success."""
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
        # Use timezone-aware date for setting last tweet
        la_tz = ZoneInfo("America/Los_Angeles")
        today_str = datetime.now(la_tz).strftime('%Y-%m-%d')
        set_last_tweet_date(today_str, tweet_type)
    except Exception as e:
        logging.error(f"Failed to post tweet: {e}")

# --- Main Logic ---
def main():
    parser = argparse.ArgumentParser(description="Post daily Dodgers summary updates to Twitter.")
    parser.add_argument("--type", type=str, required=True, choices=['summary', 'batting', 'pitching'], help="The type of update to post.")
    args = parser.parse_args()

    # Use timezone-aware date for all checks
    la_tz = ZoneInfo("America/Los_Angeles")
    today_date = datetime.now(la_tz).date()
    today_str = today_date.strftime('%Y-%m-%d')

    # Check if we've already tweeted this type of update today
    last_tweet_date = get_last_tweet_date(args.type)
    if last_tweet_date == today_str:
        logging.info(f"An update of type '{args.type}' has already been posted today. Skipping.")
        return

    # Fetch data
    url = "https://stilesdata.com/dodgers/data/standings/season_summary_latest.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch data from {url}: {e}")
        return

    # Process data into a dictionary for easy access
    stats = {item['stat']: item for item in data}
    tweet_text = ""

    # Format tweet based on type
    if args.type == 'summary':
        summary_html = stats.get('summary', {}).get('value', 'No summary available.')
        
        # Extract date from summary to ensure we're not posting about a future game
        date_match = re.search(r"\((\w+\s\d+)\)", summary_html)
        if date_match:
            game_date_str = date_match.group(1)
            # Get current year since it's not in the string
            current_year = today_date.year
            game_date = datetime.strptime(f"{game_date_str} {current_year}", "%B %d %Y").date()
            
            if game_date != today_date:
                logging.info(f"Game date ({game_date}) is not today. Halting tweet.")
                return

        summary_text = re.sub('<[^<]+?>', '', summary_html).replace('\\/','/')
        tweet_text = f"⚾️ Dodgers daily summary ⚾️\n\n{summary_text}\n\nMore: https://DodgersData.bot"

    elif args.type == 'batting':
        ba = stats.get('batting_average', {}).get('value', 'N/A')
        obp = stats.get('on_base_pct', {}).get('value', 'N/A')
        hr = stats.get('home_runs', {})
        hr_val = hr.get('value', 'N/A')
        hr_rank = hr.get('context_value', 'N/A')
        sb = stats.get('stolen_bases', {})
        sb_val = sb.get('value', 'N/A')
        sb_rank = sb.get('context_value', 'N/A')
        tweet_text = (
            f" Dodgers batting report ⚾️\n\n"
            f"• BA: {ba}\n"
            f"• OBP: {obp}\n"
            f"• Home Runs: {hr_val} ({hr_rank} in MLB)\n"
            f"• Stolen Bases: {sb_val} ({sb_rank} in MLB)\n\n"
            f"More: https://DodgersData.bot"
        )

    elif args.type == 'pitching':
        era = stats.get('era', {})
        era_val = era.get('value', 'N/A')
        era_rank = era.get('context_value', 'N/A')
        so = stats.get('strikeouts', {})
        so_val = so.get('value', 'N/A')
        so_rank = so.get('context_value', 'N/A')
        walks = stats.get('walks', {})
        walks_val = walks.get('value', 'N/A')
        walks_rank = walks.get('context_value', 'N/A')
        tweet_text = (
            f" Dodgers pitching report ⚾️\n\n"
            f"• ERA: {era_val} ({era_rank} in MLB)\n"
            f"• Strikeouts: {so_val} ({so_rank} in MLB)\n"
            f"• Walks: {walks_val} ({walks_rank} in MLB)\n\n"
            f"More: https://DodgersData.bot"
        )

    if tweet_text:
        logging.info(f"Generated tweet for type '{args.type}':\n{tweet_text}")
        post_tweet(tweet_text, args.type)
    else:
        logging.error("Failed to generate tweet text.")

if __name__ == "__main__":
    main() 