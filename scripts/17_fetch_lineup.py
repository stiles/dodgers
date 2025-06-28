#!/usr/bin/env python
# coding: utf-8

"""
Fetches and parses the Dodgers daily starting lineup from MLB.com.
Saves the data locally and uploads to S3.
"""

import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import boto3
from io import StringIO, BytesIO
import logging
from datetime import datetime, date
import re
import argparse
import tweepy
from botocore.exceptions import ClientError
from zoneinfo import ZoneInfo

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Determine if running in a GitHub Actions environment
is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'

# Twitter API credentials from environment variables
DODGERS_TWITTER_API_KEY = os.environ.get("DODGERS_TWITTER_API_KEY")
DODGERS_TWITTER_API_SECRET = os.environ.get("DODGERS_TWITTER_API_SECRET")
DODGERS_TWITTER_API_BEARER = os.environ.get("DODGERS_TWITTER_API_BEARER")
DODGERS_TWITTER_API_ACCESS_TOKEN = os.environ.get("DODGERS_TWITTER_API_ACCESS_TOKEN")
DODGERS_TWITTER_API_ACCESS_SECRET = os.environ.get("DODGERS_TWITTER_API_ACCESS_SECRET")

# AWS credentials and session initialization
aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
aws_region = "us-west-1"
s3_bucket_name = "stilesdata.com" # Consistent with other scripts

# Conditional AWS session creation based on the environment
if is_github_actions:
    session = boto3.Session(
        aws_access_key_id=aws_key_id,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
    logging.info("Running in GitHub Actions environment. Using environment variables for AWS credentials.")
else:
    profile_name = os.environ.get("AWS_PERSONAL_PROFILE", "haekeo")
    session = boto3.Session(profile_name=profile_name, region_name=aws_region)
    logging.info(f"Running locally. Using AWS profile: {profile_name}")

s3_resource = session.resource("s3")

def get_last_tweet_date():
    """Reads the last tweet date from S3."""
    try:
        obj = s3_resource.Object(s3_bucket_name, "dodgers/data/lineups/last_tweet_date.txt")
        last_date_str = obj.get()['Body'].read().decode('utf-8').strip()
        logging.info(f"Last tweet date found in S3: {last_date_str}")
        return last_date_str
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logging.info("last_tweet_date.txt not found. This is expected for the first run of the day.")
            return None
        else:
            # For other S3-related errors, we should know about them.
            logging.error(f"An unexpected S3 error occurred in get_last_tweet_date: {e}")
            raise

def set_last_tweet_date(date_str):
    """Writes the last tweet date to S3."""
    try:
        obj = s3_resource.Object(s3_bucket_name, "dodgers/data/lineups/last_tweet_date.txt")
        obj.put(Body=date_str)
        logging.info(f"Successfully updated last tweet date in S3 to: {date_str}")
    except Exception as e:
        logging.error(f"Failed to write last tweet date to S3: {e}")

def get_player_details(player_element_text):
    """
    Parses player string like 'Shohei Ohtani (L) DH' or just 'Shohei Ohtani'
    into name, batting hand, and position.
    Handles cases where player link might be missing or text is just name.
    """
    match = re.search(r'([A-Za-z\s\.\'-]+)\s*\((S|L|R)\)\s*([A-Z0-9]+)', player_element_text)
    if match:
        name = match.group(1).strip()
        batting_hand = match.group(2)
        position = match.group(3)
        return name, batting_hand, position
    
    # Fallback for just name if regex doesn't match complex structure
    # This regex looks for name and then the batting hand / position part
    player_name_match = re.match(r"^(.*?)\s*(?:\([SLR]\)\s*\w+)?$", player_element_text)
    if player_name_match:
        name = player_name_match.group(1).strip()
        # Try to parse hand and position from the span if available
        pos_match = re.search(r'\((S|L|R)\)\s*([A-Z0-9]+)', player_element_text)
        if pos_match:
            return name, pos_match.group(1), pos_match.group(2)
        return name, None, None # Only name found
    return player_element_text.strip(), None, None


def fetch_lineup_data(current_date_str):
    """
    Fetches and parses lineup data for the given date.
    """
    url = f"https://www.mlb.com/dodgers/roster/starting-lineups/{current_date_str}"
    logging.info(f"Fetching lineup from: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the first matchup, which should be the current day's game
    matchup_div = soup.find("div", class_="starting-lineups__matchup")

    if not matchup_div:
        logging.warning(f"No lineup data found for {current_date_str} on the page. It might be an off-day or lineup not posted.")
        return pd.DataFrame() # Return empty DataFrame

    lineup_data = []

    # Team Names and Tricodes
    away_team_span = matchup_div.find("span", class_="starting-lineups__team-name--away")
    home_team_span = matchup_div.find("span", class_="starting-lineups__team-name--home")

    away_team_name = away_team_span.find("a").text.strip() if away_team_span and away_team_span.find("a") else "N/A"
    away_team_tricode = away_team_span.find("a")['data-tri-code'] if away_team_span and away_team_span.find("a") else "N/A"
    
    home_team_name = home_team_span.find("a").text.strip() if home_team_span and home_team_span.find("a") else "N/A"
    home_team_tricode = home_team_span.find("a")['data-tri-code'] if home_team_span and home_team_span.find("a") else "N/A"

    # Pitchers
    pitchers_container_div = matchup_div.find("div", class_="starting-lineups__pitchers")
    if pitchers_container_div:
        pitcher_overview_div = pitchers_container_div.find("div", class_="starting-lineups__pitcher-overview")
        if pitcher_overview_div:
            pitcher_summaries = pitcher_overview_div.find_all("div", class_="starting-lineups__pitcher-summary", recursive=False)
        
            # Away Pitcher (expected at index 0)
            if len(pitcher_summaries) >= 1:
                away_pitcher_name_div = pitcher_summaries[0].find("div", class_="starting-lineups__pitcher-name")
                if away_pitcher_name_div:
                    away_pitcher_name_tag = away_pitcher_name_div.find("a")
                    if away_pitcher_name_tag:
                        away_pitcher_name = away_pitcher_name_tag.text.strip()
                        away_pitcher_hand_tag = pitcher_summaries[0].find("span", class_="starting-lineups__pitcher-pitch-hand")
                        away_pitcher_hand = away_pitcher_hand_tag.text.strip() if away_pitcher_hand_tag else "N/A"
                    elif "TBD" in away_pitcher_name_div.text.strip().upper():
                        away_pitcher_name = "TBD"
                        away_pitcher_hand = "N/A" # Or "TBD" if preferred
                    else:
                        away_pitcher_name = "N/A"
                        away_pitcher_hand = "N/A"
                        logging.warning("Away pitcher name tag not found and not TBD in pitcher_summaries[0].")
                    
                    lineup_data.append({
                        "game_date": current_date_str, "team_name": away_team_name, "team_tricode": away_team_tricode, 
                        "player_name": away_pitcher_name, "role": "Pitcher", "throwing_hand": away_pitcher_hand,
                        "batting_hand": None, "position": "P", "lineup_order": None
                    })
                else:
                    logging.warning("Away pitcher name div not found in pitcher_summaries[0].")
            else:
                logging.warning("Away pitcher data not found or incomplete in pitcher_summaries (index 0).")

            # Home Pitcher (expected at index 2, as there's often an empty middle summary div)
            if len(pitcher_summaries) >= 3:
                home_pitcher_name_div = pitcher_summaries[2].find("div", class_="starting-lineups__pitcher-name")
                if home_pitcher_name_div:
                    home_pitcher_name_tag = home_pitcher_name_div.find("a")
                    if home_pitcher_name_tag:
                        home_pitcher_name = home_pitcher_name_tag.text.strip()
                        home_pitcher_hand_tag = pitcher_summaries[2].find("span", class_="starting-lineups__pitcher-pitch-hand")
                        home_pitcher_hand = home_pitcher_hand_tag.text.strip() if home_pitcher_hand_tag else "N/A"
                    elif "TBD" in home_pitcher_name_div.text.strip().upper():
                        home_pitcher_name = "TBD"
                        home_pitcher_hand = "N/A" # Or "TBD"
                    else:
                        home_pitcher_name = "N/A"
                        home_pitcher_hand = "N/A"
                        logging.warning("Home pitcher name tag not found and not TBD in pitcher_summaries[2].")

                    lineup_data.append({
                        "game_date": current_date_str, "team_name": home_team_name, "team_tricode": home_team_tricode,
                        "player_name": home_pitcher_name, "role": "Pitcher", "throwing_hand": home_pitcher_hand,
                        "batting_hand": None, "position": "P", "lineup_order": None
                    })
                else:
                    logging.warning("Home pitcher name div not found in pitcher_summaries[2].")

            else:
                logging.warning(f"Home pitcher data not found or incomplete in pitcher_summaries (index 2). Found {len(pitcher_summaries)} pitcher summary divs.")
        else:
            logging.warning("Pitcher overview div (starting-lineups__pitcher-overview) not found within pitchers container.")
    else:
        logging.warning("Pitchers container div (starting-lineups__pitchers) not found.")

    # Lineups - targeting the one with full names
    lineup_teams_container = matchup_div.find("div", class_="starting-lineups__teams--sm") # More specific: starting-lineups__teams--sm starting-lineups__teams--xl
    if not lineup_teams_container:
         lineup_teams_container = matchup_div.find("div", class_ = re.compile(r"starting-lineups__teams--\w+"))


    if lineup_teams_container:
        away_lineup_ol = lineup_teams_container.find("ol", class_="starting-lineups__team--away")
        home_lineup_ol = lineup_teams_container.find("ol", class_="starting-lineups__team--home")

        if away_lineup_ol:
            for order, player_li in enumerate(away_lineup_ol.find_all("li", class_="starting-lineups__player"), 1):
                player_name_tag = player_li.find("a", class_="starting-lineups__player--link")
                batting_hand, position = None, None
                
                if player_name_tag:
                    player_name_full = player_name_tag.text.strip()
                    position_span = player_li.find("span", class_="starting-lineups__player--position")
                    if position_span:
                        pos_text = position_span.text.strip()
                        match = re.search(r'\((S|L|R)\)\s*([A-Z0-9]+)', pos_text)
                        if match:
                            batting_hand = match.group(1)
                            position = match.group(2)
                elif "TBD" in player_li.text.strip().upper():
                    player_name_full = "TBD"
                    # batting_hand and position remain None
                else:
                    player_name_full = player_li.text.strip() # Fallback, might be empty or other text
                    logging.warning(f"Player link not found and not TBD for away team player: {player_name_full}")

                lineup_data.append({
                    "game_date": current_date_str, "team_name": away_team_name, "team_tricode": away_team_tricode,
                    "player_name": player_name_full, "role": "Batter", "throwing_hand": None,
                    "batting_hand": batting_hand, "position": position, "lineup_order": order
                })
        
        if home_lineup_ol:
            for order, player_li in enumerate(home_lineup_ol.find_all("li", class_="starting-lineups__player"), 1):
                player_name_tag = player_li.find("a", class_="starting-lineups__player--link")
                batting_hand, position = None, None

                if player_name_tag:
                    player_name_full = player_name_tag.text.strip()
                    position_span = player_li.find("span", class_="starting-lineups__player--position")
                    if position_span:
                        pos_text = position_span.text.strip()
                        match = re.search(r'\((S|L|R)\)\s*([A-Z0-9]+)', pos_text)
                        if match:
                            batting_hand = match.group(1)
                            position = match.group(2)
                elif "TBD" in player_li.text.strip().upper():
                    player_name_full = "TBD"
                    # batting_hand and position remain None
                else:
                    player_name_full = player_li.text.strip() # Fallback
                    logging.warning(f"Player link not found and not TBD for home team player: {player_name_full}")
                            
                lineup_data.append({
                    "game_date": current_date_str, "team_name": home_team_name, "team_tricode": home_team_tricode,
                    "player_name": player_name_full, "role": "Batter", "throwing_hand": None,
                    "batting_hand": batting_hand, "position": position, "lineup_order": order
                })
    else:
        logging.warning("Lineup teams container not found.")
        
    return pd.DataFrame(lineup_data)

# Function to save DataFrame to S3
def save_to_s3(df, base_s3_path, formats=["csv", "json"]):
    if df.empty:
        logging.info(f"DataFrame is empty. Skipping S3 upload for {base_s3_path}.")
        return

    for fmt in formats:
        try:
            buffer = BytesIO()
            if fmt == "csv":
                df.to_csv(buffer, index=False)
                content_type = "text/csv"
            elif fmt == "json":
                df.to_json(buffer, indent=4, orient="records", lines=False)
                content_type = "application/json"
            
            buffer.seek(0)
            s3_key = f"{base_s3_path}.{fmt}"
            s3_resource.Bucket(s3_bucket_name).put_object(Key=s3_key, Body=buffer, ContentType=content_type)
            logging.info(f"Successfully uploaded {fmt} to s3://{s3_bucket_name}/{s3_key}")
        except Exception as e:
            logging.error(f"Failed to upload {fmt} to S3 for {base_s3_path}: {e}")

def post_tweet(tweet_text, current_date_str):
    """
    Posts a tweet to the authenticated Twitter account.
    """
    if not all([DODGERS_TWITTER_API_KEY, DODGERS_TWITTER_API_SECRET, DODGERS_TWITTER_API_ACCESS_TOKEN, DODGERS_TWITTER_API_ACCESS_SECRET]):
        logging.error("Twitter API credentials are not fully set in environment variables. Cannot post tweet.")
        return

    try:
        client = tweepy.Client(
            consumer_key=DODGERS_TWITTER_API_KEY,
            consumer_secret=DODGERS_TWITTER_API_SECRET,
            access_token=DODGERS_TWITTER_API_ACCESS_TOKEN,
            access_token_secret=DODGERS_TWITTER_API_ACCESS_SECRET
        )
        response = client.create_tweet(text=tweet_text)
        logging.info(f"Tweet posted successfully: {response.data['id']}")
        set_last_tweet_date(current_date_str)
    except Exception as e:
        logging.error(f"Failed to post tweet: {e}")

def fetch_schedule_data():
    """
    Fetches the Dodgers schedule from the JSON endpoint and finds the next game.
    Returns the next game info or None if no upcoming game found.
    """
    schedule_url = "https://stilesdata.com/dodgers/data/standings/dodgers_schedule.json"
    logging.info(f"Fetching schedule from: {schedule_url}")
    
    try:
        response = requests.get(schedule_url, timeout=10)
        response.raise_for_status()
        schedule_data = response.json()
        
        # Find the next game where game_start is not "--"
        for game in schedule_data:
            if game.get('game_start') and game['game_start'] != "--":
                logging.info(f"Found next game: {game['date']} vs {game['opp_name']} at {game['game_start']}")
                return game
        
        logging.warning("No upcoming games found with valid start times")
        return None
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching schedule from {schedule_url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error parsing schedule data: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Fetch Dodgers lineup and optionally post pitching matchup to Twitter.")
    parser.add_argument("--post-tweet", action="store_true", help="Post the pitching matchup to Twitter if available.")
    args = parser.parse_args()

    # Get current date in Los Angeles timezone to handle UTC on server
    la_tz = ZoneInfo("America/Los_Angeles")
    today_date = datetime.now(la_tz).date()
    current_date_str = today_date.strftime("%Y-%m-%d")
    # current_date_str = "2025-05-15" # Test date
    
    # Define paths - relative to the script's location to reach project root, then into data/lineups
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, '..', '..') # Assumes script is in scripts/something/
    
    # If script is directly in scripts/, then project_root is os.path.join(script_dir, '..')
    # Let's adjust based on `17_fetch_lineup.py` being in `scripts/`
    if os.path.basename(script_dir) == "data" and os.path.basename(os.path.dirname(script_dir)) == "scripts":
         # Path like scripts/data/17_fetch_lineup.py
         project_root = os.path.join(script_dir, '..', '..', '..')
         local_output_dir = os.path.join(project_root, 'data', 'lineups')
    elif os.path.basename(script_dir) == "scripts":
         # Path like scripts/17_fetch_lineup.py
         project_root = os.path.join(script_dir, '..')
         local_output_dir = os.path.join(project_root, 'data', 'lineups')
    else: # Defaulting if structure is unexpected, assuming script_dir is project root for safety
         logging.warning(f"Script directory structure unexpected: {script_dir}. Defaulting output to data/lineups from current dir.")
         project_root = os.getcwd() # Fallback
         local_output_dir = os.path.join(project_root, 'data', 'lineups')


    os.makedirs(local_output_dir, exist_ok=True)
    
    lineup_df = fetch_lineup_data(current_date_str)
    
    if not lineup_df.empty:
        # Check if the fetched lineup is for today
        fetched_game_date_str = lineup_df['game_date'].iloc[0]
        fetched_game_date = datetime.strptime(fetched_game_date_str, '%Y-%m-%d').date()
        if fetched_game_date != today_date:
            logging.info(f"Lineup data found is for {fetched_game_date}, which is not today. Halting operations.")
            return

        logging.info(f"Successfully fetched and parsed lineup data for {current_date_str}. Shape: {lineup_df.shape}")
        
        # Define base file name and S3 path
        base_filename = f"dodgers_lineup_{current_date_str}"
        local_base_path = os.path.join(local_output_dir, base_filename)
        s3_base_path = f"dodgers/data/lineups/{base_filename}"

        # Save locally
        try:
            csv_path = f"{local_base_path}.csv"
            json_path = f"{local_base_path}.json"
            lineup_df.to_csv(csv_path, index=False)
            logging.info(f"Saved lineup data to {csv_path}")
            lineup_df.to_json(json_path, indent=4, orient="records", lines=False)
            logging.info(f"Saved lineup data to {json_path}")
        except Exception as e:
            logging.error(f"Failed to save files locally: {e}")

        # Upload to S3
        save_to_s3(lineup_df, s3_base_path, formats=["csv", "json"])

        # Twitter logic
        pitchers_df = lineup_df[lineup_df['role'] == 'Pitcher'].copy()
        if len(pitchers_df) == 2:
            dodgers_pitcher = pitchers_df[pitchers_df['team_tricode'] == 'LAD']
            opponent_pitcher = pitchers_df[pitchers_df['team_tricode'] != 'LAD']

            if not dodgers_pitcher.empty and not opponent_pitcher.empty:
                dodgers_pitcher = dodgers_pitcher.iloc[0]
                opponent_pitcher = opponent_pitcher.iloc[0]

                # Fetch schedule data to get game start time
                next_game = fetch_schedule_data()

                # Format date for the tweet
                game_date = datetime.strptime(dodgers_pitcher['game_date'], '%Y-%m-%d').strftime('%B %-d')

                line1 = f"The pitching matchup for {game_date} is set! 🌟"
                line2 = f"{dodgers_pitcher['throwing_hand']} {dodgers_pitcher['player_name']} ({dodgers_pitcher['team_tricode']}) takes the mound against {opponent_pitcher['throwing_hand']} {opponent_pitcher['player_name']} ({opponent_pitcher['team_tricode']}). ⚾️🔥"
                
                # Add game start time if available
                if next_game and next_game.get('game_start'):
                    line3 = f"First pitch: {next_game['game_start']} (PT)."
                    line4 = f"More: https://DodgersData.bot"
                    tweet_text = f"{line1}\n\n{line2}\n\n{line3}"
                else:
                    line3 = f"More: https://DodgersData.bot"
                    tweet_text = f"{line1}\n\n{line2}"

                logging.info("Generated tweet text:")
                print(tweet_text)

                if args.post_tweet:
                    last_tweet_date = get_last_tweet_date()
                    if last_tweet_date == current_date_str:
                        logging.info(f"Already tweeted for {current_date_str}. Skipping.")
                    else:
                        logging.info("Attempting to post tweet...")
                        post_tweet(tweet_text, current_date_str)
                else:
                    logging.info("Dry run: --post-tweet flag not provided. Not posting to Twitter.")
            else:
                logging.warning("Could not identify both Dodgers and opponent pitcher.")
        else:
            logging.info("Not enough pitcher data to generate a tweet.")
    else:
        logging.info(f"No lineup data processed for {current_date_str}. No files will be saved or uploaded.")

if __name__ == "__main__":
    main()
