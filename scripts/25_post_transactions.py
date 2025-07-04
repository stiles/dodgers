import os
import json
import boto3
import tweepy
import logging
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
from botocore.exceptions import ClientError

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment Variables & AWS/S3
is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
s3_bucket_name = "stilesdata.com"
s3_key_transactions_archive = "dodgers/data/roster/dodgers_transactions_archive.json"

if is_github_actions:
    session = boto3.Session(region_name="us-west-1")
else:
    profile_name = os.environ.get("AWS_PERSONAL_PROFILE", "haekeo")
    session = boto3.Session(profile_name=profile_name, region_name="us-west-1")

s3_resource = session.resource("s3")

def get_posted_transactions():
    """Reads the list of already posted transaction IDs from S3."""
    s3_key = "dodgers/data/tweets/posted_transactions.json"
    try:
        obj = s3_resource.Object(s3_bucket_name, s3_key)
        posted_data = json.loads(obj.get()['Body'].read().decode('utf-8'))
        return set(posted_data.get('transaction_ids', []))
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return set()
        raise

def add_posted_transaction(transaction_id):
    """Adds a transaction ID to the list of posted transactions in S3."""
    s3_key = "dodgers/data/tweets/posted_transactions.json"
    
    # Get existing posted transactions
    posted_ids = get_posted_transactions()
    posted_ids.add(transaction_id)
    
    # Keep only the most recent 1000 to prevent the file from growing too large
    posted_list = list(posted_ids)
    if len(posted_list) > 1000:
        posted_list = posted_list[-1000:]
    
    # Save back to S3
    posted_data = {"transaction_ids": posted_list}
    obj = s3_resource.Object(s3_bucket_name, s3_key)
    obj.put(Body=json.dumps(posted_data, indent=2))
    logging.info(f"Added transaction ID to posted list: {transaction_id}")

def create_transaction_id(transaction_row):
    """Creates a unique ID for a transaction based on date and transaction text."""
    # Use first 50 characters of transaction text to create a unique but manageable ID
    transaction_snippet = transaction_row['transaction'][:50].replace(' ', '_').replace(',', '').replace('.', '')
    return f"{transaction_row['date']}_{transaction_snippet}"

def post_tweet(tweet_text, transaction_id):
    """Posts a tweet and marks the transaction as posted on success."""
    DODGERS_TWITTER_API_KEY = os.environ.get("DODGERS_TWITTER_API_KEY")
    DODGERS_TWITTER_API_SECRET = os.environ.get("DODGERS_TWITTER_API_SECRET")
    DODGERS_TWITTER_TOKEN = os.environ.get("DODGERS_TWITTER_TOKEN")
    DODGERS_TWITTER_TOKEN_SECRET = os.environ.get("DODGERS_TWITTER_TOKEN_SECRET")
    
    if not all([DODGERS_TWITTER_API_KEY, DODGERS_TWITTER_API_SECRET, DODGERS_TWITTER_TOKEN, DODGERS_TWITTER_TOKEN_SECRET]):
        logging.error("Twitter API credentials are not fully set. Cannot post tweet.")
        return False

    try:
        client = tweepy.Client(
            consumer_key=DODGERS_TWITTER_API_KEY,
            consumer_secret=DODGERS_TWITTER_API_SECRET,
            access_token=DODGERS_TWITTER_TOKEN,
            access_token_secret=DODGERS_TWITTER_TOKEN_SECRET
        )
        response = client.create_tweet(text=tweet_text)
        logging.info(f"Tweet posted successfully: {response.data['id']}")
        add_posted_transaction(transaction_id)
        return True
    except Exception as e:
        logging.error(f"Failed to post tweet: {e}")
        return False

def format_transaction_tweet(transaction_row):
    """Formats a transaction into a tweet."""
    date = transaction_row['date']
    transaction_text = transaction_row['transaction']
    
    # Format the date nicely
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%B %d, %Y')
    except:
        formatted_date = date
    
    # Create the tweet
    tweet_text = f"🏟️ Dodgers transaction ({formatted_date}):\n\n{transaction_text}"
    
    # Ensure tweet fits in character limit (280 chars)
    if len(tweet_text) > 280:
        # Truncate the transaction text if needed
        max_transaction_length = 280 - len(f"🏟️ Dodgers transaction ({formatted_date}):\n\n") - 3  # 3 for "..."
        truncated_transaction = transaction_text[:max_transaction_length] + "..."
        tweet_text = f"🏟️ Dodgers transaction ({formatted_date}):\n\n{truncated_transaction}"
    
    return tweet_text

def fetch_new_transactions():
    """Fetches new transactions that haven't been posted yet."""
    try:
        # Download the transaction archive from S3
        obj = s3_resource.Object(s3_bucket_name, s3_key_transactions_archive)
        transactions_data = json.loads(obj.get()['Body'].read().decode('utf-8'))
        
        # Get posted transaction IDs
        posted_ids = get_posted_transactions()
        
        # Find new transactions (not already posted)
        new_transactions = []
        for transaction in transactions_data:
            transaction_id = create_transaction_id(transaction)
            if transaction_id not in posted_ids:
                new_transactions.append(transaction)
        
        # Sort by date (newest first) and limit to recent ones
        new_transactions.sort(key=lambda x: x['date'], reverse=True)
        
        # Only consider transactions from the last 7 days to avoid posting very old ones
        # that might not have been posted due to script not running
        la_tz = ZoneInfo("America/Los_Angeles")
        seven_days_ago = datetime.now(la_tz).date().strftime('%Y-%m-%d')
        from datetime import timedelta
        seven_days_ago_obj = datetime.now(la_tz).date() - timedelta(days=7)
        seven_days_ago = seven_days_ago_obj.strftime('%Y-%m-%d')
        
        recent_new_transactions = [
            t for t in new_transactions 
            if t['date'] >= seven_days_ago
        ]
        
        return recent_new_transactions
        
    except Exception as e:
        logging.error(f"Error fetching transactions: {e}")
        return []

def should_post_transactions():
    """Determines if transactions should be posted based on time."""
    la_tz = ZoneInfo("America/Los_Angeles")
    current_hour = datetime.now(la_tz).hour
    
    # Post transactions during reasonable hours (7 AM to 10 PM PT)
    if 7 <= current_hour <= 22:
        logging.info(f"Good time to post transactions (hour: {current_hour})")
        return True
    else:
        logging.info(f"Outside prime posting hours (hour: {current_hour}). Skipping transaction posts.")
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Post new Dodgers transactions to Twitter.")
    parser.add_argument("--post-tweet", action="store_true", help="Post new transactions to Twitter.")
    parser.add_argument("--force", action="store_true", help="Force posting regardless of time constraints.")
    args = parser.parse_args()

    # Check if we should post (unless forced)
    if not args.force and not should_post_transactions():
        exit()

    # Fetch new transactions
    new_transactions = fetch_new_transactions()
    
    if new_transactions:
        logging.info(f"Found {len(new_transactions)} new transactions to potentially post")
        
        posts_made = 0
        for transaction in new_transactions:
            transaction_id = create_transaction_id(transaction)
            tweet_text = format_transaction_tweet(transaction)
            
            print(f"--- Transaction Tweet {posts_made + 1} ---")
            print(f"ID: {transaction_id}")
            print(f"Tweet: {tweet_text}")
            print()
            
            if args.post_tweet:
                success = post_tweet(tweet_text, transaction_id)
                if success:
                    posts_made += 1
                    # Add a small delay between posts to be respectful to Twitter's API
                    import time
                    time.sleep(2)
            else:
                logging.info("Dry run: --post-tweet flag not provided. Not posting to Twitter.")
                
        if args.post_tweet:
            logging.info(f"Successfully posted {posts_made} transaction tweets")
    else:
        logging.info("No new transactions found to post.") 