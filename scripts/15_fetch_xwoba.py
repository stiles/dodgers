#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers xwOBA Data
This script downloads xwOBA data from Baseball Savant for all current Dodgers players.
"""

import os
import sys
import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import time
import boto3
import logging
from io import StringIO
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get current year dynamically
CURRENT_YEAR = datetime.now().year

# Configuration
output_dir = "data/batting"
csv_file = f"{output_dir}/dodgers_xwoba_current.csv"
json_file = f"{output_dir}/dodgers_xwoba_current.json"
parquet_file = f"{output_dir}/dodgers_xwoba_current.parquet"
s3_bucket = "stilesdata.com"
s3_key_csv = "dodgers/data/batting/dodgers_xwoba_current.csv"
s3_key_json = "dodgers/data/batting/dodgers_xwoba_current.json"
s3_key_parquet = "dodgers/data/batting/dodgers_xwoba_current.parquet"

# List of known pitchers to skip
PITCHERS_TO_SKIP = [
    'Sasaki, Roki',
    'Snell, Blake',
    'Treinen, Blake',
    'Casparius, Ben',
    'May, Dustin',
    'Sauer, Matt',
    'García, Luis',
    'Glasnow, Tyler',
    'Wrobleski, Justin',
    'Banda, Anthony',
    'Yates, Kirby',
    'Knack, Landon',
    'Vesia, Alex',
    'Yamamoto, Yoshinobu',
    'Scott, Tanner',
    'Dreyer, Jack',
    'Phillips, Evan',
    'Kershaw, Clayton',
    'Stratton, Chris'
]

# AWS session and S3 resource
# Determine if running in a GitHub Actions environment
is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'

# AWS credentials and session initialization
aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
aws_region = "us-west-1"

# Conditional AWS session creation based on the environment
if is_github_actions:
    # In GitHub Actions, use environment variables directly
    session = boto3.Session(
        aws_access_key_id=aws_key_id,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
else:
    # Locally, use a specific profile
    session = boto3.Session(profile_name="haekeo", region_name=aws_region)

s3 = session.resource('s3')

headers = {
    'sec-ch-ua-platform': '"macOS"',
    'Referer': 'https://baseballsavant.mlb.com/savant-player/shohei-ohtani-660271?stats=career-r-hitting-mlb',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    'sec-ch-ua-mobile': '?0',
}

def format_player_name(name):
    """Convert 'Lastname, Firstname' to 'Firstname Lastname'."""
    if ',' in name:
        last, first = name.split(',')
        return f"{first.strip()} {last.strip()}"
    return name

def fetch_player_ids():
    """
    Scrape the Dodgers roster page to get all player IDs.
    Uses the current year dynamically to ensure we're getting the current roster.
    """
    logging.info(f"Fetching player IDs from roster page for {CURRENT_YEAR} season.")
    team_url = f'https://baseballsavant.mlb.com/team/119?view=statcast&nav=hitting&season={CURRENT_YEAR}'
    logging.info(f"Making request to: {team_url}")
    
    try:
        response = requests.get(team_url, headers=headers)
        logging.info(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            logging.error(f"Failed to fetch roster page. Status code: {response.status_code}")
            logging.error(f"Response content: {response.text[:500]}")  # First 500 chars of response
            return {}
            
        logging.info("Successfully fetched roster page")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all player rows in the roster table
        player_rows = soup.find_all('tr', id=lambda x: x and x.startswith('scg_'))
        logging.info(f"Found {len(player_rows)} player rows")
        
        # Create dictionary mapping player names to IDs
        player_lookup = {}
        for row in player_rows:
            try:
                player_id = row['id'].replace('scg_', '')
                # Skip team totals and MLB totals rows
                if player_id in ['119', '999999']:
                    continue
                player_name = row.find('a').text.strip()
                # Skip known pitchers before name formatting
                if player_name in PITCHERS_TO_SKIP:
                    logging.debug(f"Skipping known pitcher: {player_name}")
                    continue
                # Format name after pitcher check
                formatted_name = format_player_name(player_name)
                player_lookup[formatted_name] = player_id
                logging.debug(f"Added player: {formatted_name} (ID: {player_id})")
            except Exception as e:
                logging.warning(f"Skipping row with ID {row.get('id', 'unknown')}: {str(e)}")
                continue
        
        logging.info(f"Successfully created lookup for {len(player_lookup)} players")
        return player_lookup
        
    except Exception as e:
        logging.error(f"Error in fetch_player_ids: {str(e)}")
        logging.error(f"Response object: {response if 'response' in locals() else 'No response object'}")
        return {}

def fetch_player_xwoba(player_name, player_id):
    """Fetch xwOBA data for a specific player."""
    logging.info(f"Fetching xwOBA data for {player_name} (ID: {player_id})...")
    
    params = {
        'playerId': player_id,
        'playerType': 'Y',
    }
    
    try:
        response = requests.get('https://baseballsavant.mlb.com/player-services/rolling-thumb', 
                              params=params, 
                              headers=headers)
        logging.info(f"Response status code for {player_name}: {response.status_code}")
        
        if response.status_code != 200:
            logging.error(f"Failed to fetch data for {player_name}. Status code: {response.status_code}")
            logging.error(f"Response content: {response.text[:500]}")
            return None
            
        player_data = response.json()
        if 'plate50' not in player_data:
            logging.warning(f"No plate50 data found for {player_name} - likely a pitcher")
            return None
            
        player_data_list = player_data['plate50']
        if not player_data_list:
            logging.warning(f"No data in plate50 for {player_name}")
            return None
            
        player_df = pd.DataFrame(player_data_list)
        
        # Check if xwoba column exists
        if 'xwoba' not in player_df.columns:
            logging.warning(f"No xwoba data for {player_name}")
            return None
            
        # Convert max_game_date from UTC to Pacific Time
        if 'max_game_date' in player_df.columns:
            player_df['max_game_date'] = pd.to_datetime(player_df['max_game_date'])
            player_df['max_game_date'] = player_df['max_game_date'].dt.tz_convert('America/Los_Angeles')
            # Format the date for better readability
            player_df['max_game_date'] = player_df['max_game_date'].dt.strftime('%Y-%m-%d %H:%M:%S %Z')
            
        player_df['xwoba'] = player_df['xwoba'].astype(float)
        player_df['player_name'] = player_name
        player_df['player_id'] = player_id
        
        logging.info(f"Successfully processed data for {player_name}")
        return player_df
        
    except Exception as e:
        logging.error(f"Error fetching data for {player_name}: {str(e)}")
        logging.error(f"Response object: {response if 'response' in locals() else 'No response object'}")
        return None

def fetch_league_average_xwoba(year=CURRENT_YEAR):
    """
    Fetch league average xwOBA from Baseball Savant.
    
    Args:
        year (int): The season year to fetch data for. Defaults to current year.
        
    Returns:
        float or None: The league average xwOBA for qualified hitters (50+ PA), or None if fetch fails
    """
    logging.info(f"Fetching league average xwOBA for {year} season")
    url = (
        "https://baseballsavant.mlb.com/leaderboard/expected_statistics?"
        f"type=batter&year={year}&position=&team=&filterType=bip&min=q&csv=true"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/132.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        
        # Calculate weighted average xwOBA based on plate appearances
        # Only include players with at least some minimum PAs to avoid noise
        # Using a weighted average ensures that players with more PAs have more influence on
        # the league average calculation, which better represents the true league performance.
        # A simple mean would give equal weight to a player with 10 PAs and a player with 500 PAs.
        min_pa = 10  # Minimum plate appearances to include
        filtered_df = df[df["pa"] >= min_pa]
        
        if 'pa' in filtered_df.columns and 'est_woba' in filtered_df.columns:
            # Calculate weighted average based on number of plate appearances
            total_pa = filtered_df['pa'].sum()
            weighted_xwoba = (filtered_df['est_woba'] * filtered_df['pa']).sum() / total_pa
            lg_avg_xwoba = weighted_xwoba
            logging.info(f"Calculated weighted league average xwOBA: {lg_avg_xwoba:.3f} (based on {total_pa} plate appearances)")
        else:
            # Fallback to simple mean if columns are missing
            lg_avg_xwoba = filtered_df["est_woba"].mean()
            logging.info(f"Calculated simple league average xwOBA: {lg_avg_xwoba:.3f}")
        
        logging.info(f"League average xwOBA: {lg_avg_xwoba:.3f}")
        return lg_avg_xwoba
        
    except Exception as e:
        logging.error(f"Error fetching league average xwOBA: {str(e)}")
        return None

def main():
    try:
        logging.info(f"Starting xwOBA data collection for {CURRENT_YEAR} season")
        os.makedirs(output_dir, exist_ok=True)
        logging.info("Output directory checked/created.")

        # Get league average xwOBA
        lg_avg_xwoba = fetch_league_average_xwoba()
        if lg_avg_xwoba is None:
            logging.error("Failed to fetch league average xwOBA. Exiting.")
            sys.exit(1)

        # Get all player IDs
        player_lookup = fetch_player_ids()
        if not player_lookup:
            logging.error("No players found in lookup. Exiting.")
            sys.exit(1)
            
        logging.info(f"Player lookup contains {len(player_lookup)} players")
        
        # Save the player lookup
        with open(f'{output_dir}/player_lookup.json', 'w') as f:
            json.dump(player_lookup, f, indent=2)
        logging.info("Saved player lookup to JSON file")
        
        # Fetch xwOBA data for each player
        all_player_data = []
        for player_name, player_id in player_lookup.items():
            player_df = fetch_player_xwoba(player_name, player_id)
            if player_df is not None:
                # Add league average column to each player's data
                player_df['league_avg_xwoba'] = lg_avg_xwoba
                all_player_data.append(player_df)
                logging.info(f"Added data for {player_name} to collection")
            time.sleep(1)  # Be nice to the server
        
        # Combine all player data
        if all_player_data:
            df = pd.concat(all_player_data, ignore_index=True)
            logging.info(f"Combined data for {len(all_player_data)} players")
            
            # Calculate forward rank, preserving original ordering
            # In Baseball Savant data, rn=1 is already the most recent plate appearance, 
            # and rn=50 is the oldest, so we'll keep this ordering
            df["rn_fwd"] = df["rn"]
            
            # Add a debugging log to show the range of rn values
            min_rn = df["rn"].min()
            max_rn = df["rn"].max()
            logging.info(f"Source data rn values range from {min_rn} (most recent) to {max_rn} (oldest)")
            
            # Validate ordering assumption if date information is available
            if 'max_game_date' in df.columns:
                # Get a sample player with multiple records
                sample_player = df['player_name'].value_counts().idxmax()
                sample_df = df[df['player_name'] == sample_player].sort_values('rn')
                
                logging.info(f"Validating chronological order using {sample_player}'s data:")
                for idx, row in sample_df.head(3).iterrows():
                    logging.info(f"  rn={row['rn']}, date={row.get('max_game_date', 'N/A')}")
                    
                logging.info("If dates for lower rn values are more recent, the ordering is correct")
            
            # Save league average separately
            league_avg_data = {
                'year': CURRENT_YEAR,
                'league_avg_xwoba': lg_avg_xwoba,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            with open(f'{output_dir}/league_avg_xwoba.json', 'w') as f:
                json.dump(league_avg_data, f, indent=2)
            
            df.drop(columns=['savant_batter_id'], inplace=True)
            # Save to various formats
            df.to_csv(csv_file, index=False)
            df.to_json(json_file, orient="records")
            df.to_parquet(parquet_file, index=False)
            logging.info("Data written to JSON, CSV, and Parquet files.")
            
            # Upload to S3
            s3.Bucket(s3_bucket).upload_file(csv_file, s3_key_csv)
            s3.Bucket(s3_bucket).upload_file(json_file, s3_key_json)
            s3.Bucket(s3_bucket).upload_file(parquet_file, s3_key_parquet)
            s3.Bucket(s3_bucket).upload_file(
                f'{output_dir}/league_avg_xwoba.json',
                'dodgers/data/batting/league_avg_xwoba.json'
            )
            logging.info("Files successfully uploaded to S3.")
        else:
            logging.error("No data was collected from any players.")
            sys.exit(1)

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        logging.error(f"Error type: {type(e).__name__}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()