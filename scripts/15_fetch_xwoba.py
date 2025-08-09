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
import re
import unicodedata

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

# Allowlist of batter names to include (expected input: "First Last")
ALLOWED_BATTERS = [
    "Shohei Ohtani",
    "Mookie Betts",
    "Will Smith",
    "Freddie Freeman",
    "Andy Pages",
    "Teo Hernandex",  # will be normalized/matched to Teoscar Hernández
    "Max Muncy",
    "Miguel Rojas",
    "Tommy Edman",
    "Hyeseong Kim",
    "Michael Conforto",
    "Alex Call",
]

# Known corrections to help match allowlist typos or alternate spellings
NAME_CORRECTIONS = {
    # normalized "first last" -> corrected normalized "first last"
    "teo hernandex": "teoscar hernandez",
    "teo hernandez": "teoscar hernandez",
    "hyeseong kim": "hyeseong kim",  # keep as-is; normalization handles hyphens/accents
}

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

def strip_accents(text: str) -> str:
    """Remove diacritics from text."""
    text_norm = unicodedata.normalize('NFD', text)
    return ''.join(ch for ch in text_norm if not unicodedata.combining(ch))

def normalize_name(name: str) -> str:
    """
    Normalize a player name for comparison:
    - lower case
    - remove accents
    - remove punctuation, commas, periods
    - collapse whitespace
    - remove hyphens
    Output as "first last" order regardless of input.
    """
    if not name:
        return ""
    name = name.strip()
    # If "Last, First" flip to "First Last"
    if ',' in name:
        parts = [p.strip() for p in name.split(',')]
        if len(parts) >= 2:
            name = f"{parts[1]} {parts[0]}"
    # Remove accents
    name = strip_accents(name)
    # Remove punctuation and hyphens
    name = re.sub(r"[\-\.]+", " ", name)
    name = re.sub(r"[^a-zA-Z\s]", " ", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name.lower()

def to_last_first(name: str) -> str:
    """Convert "First Last" to "Last, First" for display."""
    if not name:
        return name
    tokens = name.strip().split()
    if len(tokens) >= 2:
        first = " ".join(tokens[:-1])
        last = tokens[-1]
        return f"{last}, {first}"
    return name

def build_allowed_set(raw_names: list[str]) -> set[str]:
    normalized = set()
    for nm in raw_names:
        key = normalize_name(nm)
        key = NAME_CORRECTIONS.get(key, key)
        normalized.add(key)
    return normalized

ALLOWED_NORMALIZED = build_allowed_set(ALLOWED_BATTERS)

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
                player_name_raw = row.find('a').text.strip()
                # Format to "First Last" then filter by allowlist
                formatted_name = format_player_name(player_name_raw)
                normalized = normalize_name(formatted_name)
                # Apply corrections map before comparison
                normalized = NAME_CORRECTIONS.get(normalized, normalized)
                # Check allowlist: require last name exact match and loose first-name prefix match
                if normalized not in ALLOWED_NORMALIZED:
                    # try prefix match on first name with exact last name
                    # split to first/last for both candidate and allowed
                    cand_tokens = normalized.split()
                    if len(cand_tokens) >= 2:
                        cand_first = " ".join(cand_tokens[:-1])
                        cand_last = cand_tokens[-1]
                        matched = False
                        for allowed in ALLOWED_NORMALIZED:
                            a_tokens = allowed.split()
                            if len(a_tokens) >= 2:
                                a_first = " ".join(a_tokens[:-1])
                                a_last = a_tokens[-1]
                                if cand_last == a_last and (cand_first.startswith(a_first) or a_first.startswith(cand_first)):
                                    matched = True
                                    break
                        if not matched:
                            continue
                    else:
                        continue
                player_lookup[formatted_name] = player_id
                logging.debug(f"Added allowed player: {formatted_name} (ID: {player_id})")
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
        if 'plate100' not in player_data:
            logging.warning(f"No plate100 data found for {player_name} - likely a pitcher")
            return None
            
        player_data_list = player_data['plate100']
        if not player_data_list:
            logging.warning(f"No data in plate100 for {player_name}")
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
        # Display name as "First Last"
        player_df['player_name'] = player_name
        player_df['player_id'] = player_id
        
        logging.info(f"Successfully processed data for {player_name}")
        return player_df
        
    except Exception as e:
        logging.error(f"Error fetching data for {player_name}: {str(e)}")
        logging.error(f"Response object: {response if 'response' in locals() else 'No response object'}")
        return None

def fetch_league_average_xwoba(year=None):
    """
    Fetches the league average xwOBA from the rolling leaderboard on Baseball Savant.
    It finds the inline script data, parses it, and averages the xwOBA for all batters.
    """
    logging.info("Fetching league average xwOBA from rolling leaderboard.")
    url = 'https://baseballsavant.mlb.com/leaderboard/rolling'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    script_tags = soup.find_all('script')
    
    data = None
    for script in script_tags:
        if script.string and 'var rolling =' in script.string:
            script_content = script.string
            match = re.search(r'var rolling = (\{.*?\});', script_content, re.DOTALL)
            if match:
                json_data_str = match.group(1)
                try:
                    data = json.loads(json_data_str)
                    break 
                except json.JSONDecodeError:
                    continue 

    if data is None:
        logging.error("Could not find and parse rolling data from any script tag.")
        return None

    if 'Batter100' not in data:
        logging.error("Could not find 'Batter100' key in the data.")
        return None

    player_data = data['Batter100']

    if not player_data:
        logging.warning("No player data found under 'Batter100'.")
        return None

    df = pd.DataFrame(player_data)
    xwoba_column = 'last_x_xwoba'

    if xwoba_column not in df.columns:
        logging.error(f"Could not find '{xwoba_column}' column in the player data.")
        return None

    df[xwoba_column] = pd.to_numeric(df[xwoba_column], errors='coerce')
    df.dropna(subset=[xwoba_column], inplace=True)

    average_xwoba = df[xwoba_column].mean()
    logging.info(f"Calculated league average xwOBA: {average_xwoba:.3f}")
    
    return average_xwoba

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
            df.to_json(json_file, orient="records", indent=2)
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