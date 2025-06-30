#!/usr/bin/env python
# coding: utf-8

"""
Fetches and parses current league standings metrics for all MLB teams.
Saves the data locally as a JSON list of dictionaries and uploads to S3.
"""

import os
import requests
import boto3
import logging
from datetime import datetime
import json
from typing import List, Dict, Any, Optional

HEADERS = {
    'sec-ch-ua-platform': '"macOS"',
    'Referer': 'https://www.mlb.com/',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
}

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Determine if running in a GitHub Actions environment
is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'

# AWS credentials and session initialization
aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
aws_region = "us-west-1"
s3_bucket_name = "stilesdata.com"

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

CURRENT_YEAR = datetime.now().year

def format_games_back(gb_value):
    """Formats games back to be an int if a whole number, otherwise a float."""
    try:
        # Try to convert to a float first
        gb_float = float(gb_value)
        # Check if it's an integer
        if gb_float.is_integer():
            return int(gb_float)
        return gb_float
    except (ValueError, TypeError):
        # Return original value if conversion fails (e.g., '-')
        return gb_value

def get_all_teams_standings_metrics() -> Optional[List[Dict[str, Any]]]:
    """
    Fetches MLB standings data for all teams.
    Returns: A list of dictionaries, each containing standings metrics for a team, or None on failure.
    """
    url = (
        f'https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season={CURRENT_YEAR}'
        f'&standingsTypes=regularSeason&hydrate=team(division,league)'
    )
    all_teams_data = []
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        if "records" not in data:
            logging.warning("No 'records' key in standings API response.")
            return None

        for record_group in data["records"]:
            if "teamRecords" in record_group:
                for team_record in record_group["teamRecords"]:
                    metrics = {
                        "team_id": team_record.get("team", {}).get("id"),
                        "team_name": team_record.get("team", {}).get("name"),
                        "wins": team_record.get("wins"),
                        "losses": team_record.get("losses"),
                        "winning_percentage": team_record.get("winningPercentage"),
                        "division_rank": team_record.get("divisionRank"),
                        "league_rank": team_record.get("leagueRank"),
                        "sport_rank": team_record.get("sportRank"),
                        "games_back": format_games_back(team_record.get("gamesBack", "-")),
                        "division_games_back": format_games_back(team_record.get("divisionGamesBack", "-")),
                        "league_games_back": format_games_back(team_record.get("leagueGamesBack", "-")),
                        "streak_type": team_record.get("streak", {}).get("streakType"),
                        "streak_number": team_record.get("streak", {}).get("streakNumber"),
                        "magic_number": team_record.get("magicNumber"),
                        "elimination_number": team_record.get("eliminationNumber"),
                        "division_name": team_record.get("team",{}).get("division",{}).get("name"),
                        "league_name": team_record.get("team",{}).get("league",{}).get("name"),
                        "games_played": team_record.get("gamesPlayed"),
                        "runs_scored": team_record.get("runsScored"),
                        "runs_against": team_record.get("runsAllowed"),
                        "run_differential": team_record.get("runDifferential"),
                    }
                    all_teams_data.append(metrics)
        
        if not all_teams_data:
            logging.warning("No team data extracted from standings.")
            return None
        return all_teams_data

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for standings data: {e}")
        return None
    except ValueError as e: # Includes JSONDecodeError
        logging.error(f"Failed to decode JSON for standings data: {e}")
        return None

def main():
    """
    Main function to fetch all teams standings metrics, save locally, and upload to S3.
    """
    logging.info(f"Fetching all teams standings metrics for {CURRENT_YEAR}...")
    all_standings_data = get_all_teams_standings_metrics()

    if not all_standings_data:
        logging.error(f"Could not retrieve standings metrics for any teams. Exiting.")
        return

    logging.info(f"Successfully fetched standings for {len(all_standings_data)} teams for {CURRENT_YEAR}.")

    local_dir = os.path.join("data", "standings")
    data_dir_for_jekyll = os.path.join("_data", "standings") # New directory for Jekyll
    local_filename = f"all_teams_standings_metrics_{CURRENT_YEAR}.json"
    local_file_path = os.path.join(local_dir, local_filename)
    jekyll_file_path = os.path.join(data_dir_for_jekyll, local_filename) # Path for Jekyll data file
    s3_key = f"dodgers/data/standings/{local_filename}" # Path on S3

    try:
        os.makedirs(local_dir, exist_ok=True)
        os.makedirs(data_dir_for_jekyll, exist_ok=True) # Ensure Jekyll data directory exists
        logging.info(f"Ensured directory exists: {local_dir}")
        logging.info(f"Ensured directory exists: {data_dir_for_jekyll}")
    except OSError as e:
        logging.error(f"Could not create directory {local_dir} or {data_dir_for_jekyll}: {e}")
        return

    try:
        with open(local_file_path, 'w') as f:
            json.dump(all_standings_data, f, indent=4)
        logging.info(f"Successfully saved all teams standings metrics to {local_file_path}")
        # Save a copy for Jekyll
        with open(jekyll_file_path, 'w') as f:
            json.dump(all_standings_data, f, indent=4)
        logging.info(f"Successfully saved all teams standings metrics to {jekyll_file_path} for Jekyll")
    except IOError as e:
        logging.error(f"Failed to save all teams standings metrics locally: {e}")
        return

    if os.path.exists(local_file_path):
        try:
            s3_resource.Bucket(s3_bucket_name).upload_file(local_file_path, s3_key)
            logging.info(f"Successfully uploaded {local_filename} to S3 at '{s3_key}'")
        except boto3.exceptions.S3UploadFailedError as e:
            logging.error(f"Failed to upload {local_filename} to S3: {e}")
        except Exception as e: 
            logging.error(f"An unexpected error during S3 upload of {local_filename}: {e}")
    else:
        logging.warning(f"Local file {local_file_path} not found. Skipping S3 upload.")

if __name__ == "__main__":
    main()