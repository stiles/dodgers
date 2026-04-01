#!/usr/bin/env python
# coding: utf-8

"""
Add 2025 season data to historical standings archive
This is a one-time script to backfill 2025 data that was treated as "current" last year
"""

import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import boto3
from io import StringIO
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
YEAR_TO_ADD = 2025
url = f"https://www.baseball-reference.com/teams/LAD/{YEAR_TO_ADD}-schedule-scores.shtml"
output_dir = "data/standings/archive"
historic_file_url = "https://stilesdata.com/dodgers/data/standings/archive/dodgers_standings_1958_2024.parquet"
new_archive_file = f"{output_dir}/dodgers_standings_1958_2025.parquet"

# AWS configuration
s3_bucket = "stilesdata.com"
s3_key = "dodgers/data/standings/archive/dodgers_standings_1958_2025.parquet"

# AWS session
session = boto3.Session(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
)
s3 = session.resource('s3')

def fetch_year_data(url, year):
    """Fetch and process a single year's data from Baseball Reference"""
    logging.info(f"Fetching {year} data from Baseball Reference...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", {"id": "team_schedule"})
        
        if not table:
            logging.error(f"Could not find team schedule table for {year}")
            return None
        
        # Parse table
        src = pd.read_html(StringIO(str(table)))[0]
        
        # Handle different column counts
        num_cols = len(src.columns)
        logging.info(f"Table has {num_cols} columns (before adding year)")
        
        # Set column names - adjust based on actual column count
        if num_cols == 22:  # 2025 format with Streak and Orig. Scheduled
            src.columns = [
                "gm",
                "date",
                "boxscore",  # Unnamed: 2 (boxscore link)
                "tm",
                "home_away",  # Unnamed: 4
                "opp",
                "result",
                "r",
                "ra",
                "inn",
                "record",
                "rank",
                "gb",
                "win",
                "loss",
                "save",
                "time",
                "day_night",
                "attendance",
                "cli",
                "streak",  # New column
                "orig_scheduled",  # New column
            ]
            # Drop the extra columns we don't need
            src = src.drop(columns=["streak", "orig_scheduled", "boxscore"])
        elif num_cols == 20:  # Standard format
            src.columns = [
                "gm",
                "date",
                "tm",
                "home_away",
                "opp",
                "result",
                "r",
                "ra",
                "inn",
                "record",
                "rank",
                "gb",
                "win",
                "loss",
                "save",
                "time",
                "day_night",
                "attendance",
                "cli",
            ]
        else:
            logging.error(f"Unexpected number of columns: {num_cols}")
            return None
        
        # Add year column AFTER setting column names
        src["year"] = str(year)

        # Remove header rows that appear in the data (where gm == 'Gm#')
        src = src[src['gm'] != 'Gm#'].reset_index(drop=True)
        
        # Convert types
        src["gm"] = src["gm"].astype(int)
        src["year"] = src["year"].astype(str)

        # Split and format date
        src[["weekday", "date"]] = src["date"].str.split(", ", expand=True)
        src["date"] = src["date"].str.replace(" (1)", "").str.replace(" (2)", "")
        src["game_date"] = pd.to_datetime(src["date"] + ", " + src["year"], format="%b %d, %Y").astype(str)

        # Clean home-away column
        src.loc[src.home_away == "@", "home_away"] = "away"
        src.loc[src.home_away.isna(), "home_away"] = "home"

        # Games back as number
        src["gb"] = (
            src["gb"].str.replace("up ", "up").str.replace("up", "+").str.replace("Tied", "0")
        )
        src["gb"] = src["gb"].apply(
            lambda x: float(x) if x.startswith("+") else -float(x) if float(x) != 0 else 0
        )

        src["attendance"] = src["attendance"].fillna(0)
        src["gm"] = src["gm"].astype(int)
        src[["r", "ra", "attendance", "gm", "rank"]] = src[
            ["r", "ra", "attendance", "gm", "rank"]
        ].astype(int)

        # Calculate win/loss and win percentage
        src[['wins', 'losses']] = src['record'].str.split('-', expand=True).astype(int)
        src['win_pct'] = (src['wins'] / src['gm']).round(2)
        src['game_day'] = pd.to_datetime(src['game_date']).dt.day_name()
        src["result"] = src["result"].str.split("-", expand=True)[0]

        # Convert game_date to datetime if needed
        if 'game_date' in src.columns and src['game_date'].dtype == 'object':
            src['game_date'] = pd.to_datetime(src['game_date'])

        logging.info(f"Successfully fetched {len(src)} games for {year}")
        return src
        
    except Exception as e:
        logging.error(f"Error fetching {year} data: {e}")
        return None

def main():
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load historic data (1958-2024)
    logging.info(f"Loading historic data from {historic_file_url}...")
    historic_df = pd.read_parquet(historic_file_url)
    logging.info(f"Historic data loaded: {len(historic_df)} rows, years {historic_df['year'].min()}-{historic_df['year'].max()}")
    
    # 2. Fetch 2025 data
    year_2025_df = fetch_year_data(url, YEAR_TO_ADD)
    
    if year_2025_df is None:
        logging.error("Failed to fetch 2025 data. Exiting.")
        return 1
    
    # 3. Combine
    logging.info("Combining historic data with 2025...")
    
    # Ensure consistent types before combining
    # Convert year_2025_df columns to match historic_df types
    for col in historic_df.columns:
        if col in year_2025_df.columns:
            try:
                year_2025_df[col] = year_2025_df[col].astype(historic_df[col].dtype)
            except Exception as e:
                logging.warning(f"Could not convert {col} to {historic_df[col].dtype}: {e}")
    
    combined_df = pd.concat([historic_df, year_2025_df], ignore_index=True)
    
    # Sort by year and game number
    combined_df = combined_df.sort_values(['year', 'gm']).reset_index(drop=True)
    
    logging.info(f"Combined data: {len(combined_df)} rows, years {combined_df['year'].min()}-{combined_df['year'].max()}")
    
    # Force consistent types for problematic columns
    combined_df['rank'] = pd.to_numeric(combined_df['rank'], errors='coerce').astype('Int64')  # Nullable integer, coerce non-numeric to NaN
    combined_df['year'] = combined_df['year'].astype(str)
    
    # 4. Save locally
    combined_df.to_parquet(new_archive_file, index=False)
    logging.info(f"✅ Saved to {new_archive_file}")
    
    # 5. Upload to S3
    try:
        s3.Bucket(s3_bucket).upload_file(new_archive_file, s3_key)
        logging.info(f"✅ Uploaded to s3://{s3_bucket}/{s3_key}")
        logging.info(f"   Public URL: https://{s3_bucket}/{s3_key}")
    except Exception as e:
        logging.error(f"Failed to upload to S3: {e}")
        return 1
    
    logging.info("✅ Successfully added 2025 to archive!")
    return 0

if __name__ == "__main__":
    exit(main())
