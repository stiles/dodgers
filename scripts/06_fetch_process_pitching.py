#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers pitching stats from MLB Stats API
This replaces Baseball Reference with the faster MLB Stats API for current season pitching data.
"""

import os
import boto3
import pandas as pd
import requests
import logging
from io import BytesIO
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DODGERS_TEAM_ID = 119
year = datetime.now().year

# Headers for MLB Stats API
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
}


def fetch_team_pitching_stats():
    """Fetch team pitching totals from MLB Stats API"""
    url = f"https://statsapi.mlb.com/api/v1/teams/{DODGERS_TEAM_ID}/stats"
    params = {
        'stats': 'season',
        'group': 'pitching',
        'season': year
    }
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Extract pitching stats from the response
        stats = data['stats'][0]['splits'][0]['stat']
        
        # Map MLB API fields to our schema
        team_stats = {
            'season': str(year),
            'name': 'Team Totals',
            'w': stats.get('wins', 0),
            'l': stats.get('losses', 0),
            'era': stats.get('era', '0.00'),
            'g': stats.get('gamesPlayed', 0),
            'gs': stats.get('gamesStarted', 0),
            'cg': stats.get('completeGames', 0),
            'sho': stats.get('shutouts', 0),
            'sv': stats.get('saves', 0),
            'ip': stats.get('inningsPitched', '0.0'),
            'h': stats.get('hits', 0),
            'r': stats.get('runs', 0),
            'er': stats.get('earnedRuns', 0),
            'hr': stats.get('homeRuns', 0),
            'bb': stats.get('baseOnBalls', 0),
            'ibb': stats.get('intentionalWalks', 0),
            'so': stats.get('strikeOuts', 0),
            'hbp': stats.get('hitByPitch', 0),
            'bk': stats.get('balks', 0),
            'wp': stats.get('wildPitches', 0),
            'bf': stats.get('battersFaced', 0),
            'whip': stats.get('whip', '0.00'),
            'avg': stats.get('avg', '.000'),
            'so/bb': None,  # Calculate below
        }
        
        # Calculate SO/BB ratio
        if team_stats['bb'] > 0:
            team_stats['so/bb'] = round(team_stats['so'] / team_stats['bb'], 2)
        
        logging.info(f"Successfully fetched team pitching stats for {year}")
        return pd.DataFrame([team_stats])
        
    except Exception as e:
        logging.error(f"Failed to fetch team pitching stats from MLB API: {e}")
        raise


def save_dataframe(df, path_without_extension, formats):
    """Save DataFrames in multiple formats"""
    os.makedirs(os.path.dirname(path_without_extension), exist_ok=True)
    
    for file_format in formats:
        file_path = f"{path_without_extension}.{file_format}"
        if file_format == "csv":
            df.to_csv(file_path, index=False)
        elif file_format == "json":
            df.to_json(file_path, indent=4, orient="records")
        elif file_format == "parquet":
            df.to_parquet(file_path, index=False)
        else:
            logging.warning(f"Unsupported format: {file_format}")


def save_to_s3(df, base_path, s3_bucket, formats=["csv", "json", "parquet"]):
    """Save Pandas DataFrame in specified formats and upload to S3 bucket"""
    # Use environment variables if available (GitHub Actions), otherwise use local profile
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        session = boto3.Session(
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name='us-west-1'
        )
        logging.info("Using AWS credentials from environment variables")
    else:
        profile_name = os.environ.get("AWS_PERSONAL_PROFILE", "haekeo")
        session = boto3.Session(profile_name=profile_name, region_name='us-west-1')
        logging.info(f"Using AWS profile: {profile_name}")
    
    s3_resource = session.resource("s3")

    for fmt in formats:
        file_path = f"{base_path}.{fmt}"
        buffer = BytesIO()
        if fmt == "csv":
            df.to_csv(buffer, index=False)
            content_type = "text/csv"
        elif fmt == "json":
            df.to_json(buffer, indent=4, orient="records")
            content_type = "application/json"
        elif fmt == "parquet":
            df.to_parquet(buffer, index=False)
            content_type = "application/vnd.apache.parquet"
        
        buffer.seek(0)
        try:
            s3_resource.Bucket(s3_bucket).put_object(
                Key=file_path, Body=buffer, ContentType=content_type
            )
            logging.info(f"Uploaded {fmt} to {s3_bucket}/{file_path}")
        except Exception as e:
            logging.error(f"Failed to upload {fmt} to {s3_bucket}/{file_path}: {e}")
            raise


def main():
    """Main execution function"""
    logging.info(f"Fetching Dodgers pitching stats for {year} from MLB Stats API")
    
    # Fetch current season data from MLB API
    totals = fetch_team_pitching_stats()
    
    # Note: Ranks are now fetched by script 03_scrape_league_ranks.py
    # Create empty ranks dataframe for backward compatibility
    ranks = pd.DataFrame()
    
    # Save local files
    logging.info("Saving files locally")
    formats = ["csv", "json", "parquet"]
    try:
        save_dataframe(totals, "data/pitching/dodgers_pitching_totals_current", formats)
        # Don't save empty ranks file
        # save_dataframe(ranks, "data/pitching/dodgers_pitching_ranks_current", formats)
    except Exception as e:
        logging.error(f"An error occurred saving local files: {e}")
        raise
    
    # Upload to S3
    logging.info("Uploading to S3")
    save_to_s3(
        totals,
        "dodgers/data/pitching/dodgers_pitching_totals_current",
        "stilesdata.com",
    )
    # Don't upload empty ranks file
    # save_to_s3(
    #     ranks,
    #     "dodgers/data/pitching/dodgers_pitching_ranks_current",
    #     "stilesdata.com",
    # )
    
    logging.info("Pitching data fetch and processing complete!")


if __name__ == "__main__":
    main()
