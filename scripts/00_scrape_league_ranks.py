#!/usr/bin/env python
# coding: utf-8

"""
Fetches and parses the Dodgers league ranks from MLB.com.
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
from typing import Optional
import json # Added for JSON operations

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

CURRENT_YEAR = datetime.now().year

# runs, stolen bases, homeruns, strikeouts, walks, ERA
HITTING_STATS = ['runs', 'stolenBases', 'homeRuns', 'battingAverage', 'onBasePlusSlugging', 'sluggingPercentage', 'onBasePercentage']
PITCHING_STATS = ['strikeouts', 'walks', 'earnedRunAverage', 'walksAndHitsPerInningPitched']
STAT_TYPES = ['hitting', 'pitching']

def get_team_rank_for_stat(stat_name: str, stat_group: str, team_name_query: str = "Los Angeles Dodgers") -> Optional[int]:
    """
    Fetches MLB team stats for a given statistic and returns the rank of the specified team.

    Args:
        stat_name: The specific statistic to fetch (e.g., 'runs', 'homeRuns').
        stat_group: The group of the statistic ('hitting' or 'pitching').
        team_name_query: The name of the team to find the rank for.

    Returns:
        The rank of the team for the specified statistic, or None if not found.
    """
    # Determine sort order based on stat - some stats are better lower (e.g., ERA)
    sort_order = "asc" if stat_name in ["earnedRunAverage"] else "desc"
    
    url = (
        f'https://bdfed.stitch.mlbinfra.com/bdfed/stats/team?&env=prod&sportId=1&gameType=R'
        f'&group={stat_group}&order={sort_order}&sortStat={stat_name}&stats=season&season={CURRENT_YEAR}'
        f'&limit=30&offset=0'
    )
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()  # Raises an exception for 4XX/5XX errors
        data = response.json()
        if "stats" in data:
            for team_stats in data["stats"]:
                if team_stats.get("teamName") == team_name_query:
                    # The API provides rank directly
                    return team_stats.get("rank")
            logging.warning(f"Team '{team_name_query}' not found in stats for {stat_name} ({stat_group}).")
        else:
            logging.warning(f"No 'stats' key in response for {stat_name} ({stat_group}): {data}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {stat_name} ({stat_group}): {e}")
        return None
    except ValueError as e: # Includes JSONDecodeError
        logging.error(f"Failed to decode JSON for {stat_name} ({stat_group}): {e}")
        return None

def main():
    """
    Main function to fetch Dodgers league ranks for specified stats.
    """
    dodgers_ranks = {}
    team_to_find = "Los Angeles Dodgers"

    logging.info(f"Fetching hitting stats for {team_to_find} for {CURRENT_YEAR}...")
    for stat in HITTING_STATS:
        rank = get_team_rank_for_stat(stat_name=stat, stat_group="hitting", team_name_query=team_to_find)
        if rank is not None:
            dodgers_ranks[f'hitting_{stat}'] = rank
        else:
            dodgers_ranks[f'hitting_{stat}'] = 'Not found'

    logging.info(f"Fetching pitching stats for {team_to_find} for {CURRENT_YEAR}...")
    for stat in PITCHING_STATS:
        rank = get_team_rank_for_stat(stat_name=stat, stat_group="pitching", team_name_query=team_to_find)
        if rank is not None:
            dodgers_ranks[f'pitching_{stat}'] = rank
        else:
            dodgers_ranks[f'pitching_{stat}'] = 'Not found'
    
    logging.info("Dodgers League Ranks:")
    for stat, rank in dodgers_ranks.items():
        logging.info(f"  {stat.replace('_', ' ').title()}: {rank}")

    # Define file paths
    local_dir = os.path.join("data", "standings")
    local_filename = f"dodgers_league_ranks_{CURRENT_YEAR}.json"
    local_file_path = os.path.join(local_dir, local_filename)
    s3_key = f"dodgers/standings/{local_filename}" # S3 key structure

    # Ensure local directory exists
    try:
        os.makedirs(local_dir, exist_ok=True)
        logging.info(f"Ensured directory exists: {local_dir}")
    except OSError as e:
        logging.error(f"Could not create directory {local_dir}: {e}")
        return 

    # Save locally
    try:
        with open(local_file_path, 'w') as f:
            json.dump(dodgers_ranks, f, indent=4)
        logging.info(f"Successfully saved ranks to {local_file_path}")
    except IOError as e:
        logging.error(f"Failed to save ranks locally to {local_file_path}: {e}")

    # Upload to S3
    if os.path.exists(local_file_path): # Only upload if file was created successfully
        try:
            s3_resource.Bucket(s3_bucket_name).upload_file(local_file_path, s3_key)
            logging.info(f"Successfully uploaded {local_filename} to S3 bucket '{s3_bucket_name}' at '{s3_key}'")
        except boto3.exceptions.S3UploadFailedError as e:
            logging.error(f"Failed to upload {local_filename} to S3: {e}")
        except Exception as e: # Catch other potential boto3/AWS errors (e.g., NoCredentialsError)
            logging.error(f"An unexpected error occurred during S3 upload of {local_filename}: {e}")
    else:
        logging.warning(f"Local file {local_file_path} not found. Skipping S3 upload.")

if __name__ == "__main__":
    main()