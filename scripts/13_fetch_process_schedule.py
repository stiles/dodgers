#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers schedule snapshot
This notebook downloads the team's current standings table from [Baseball Reference](https://www.baseball-reference.com/teams/LAD/2024-schedule-scores.shtml) and creates a results/schedule table listing five games in the past and future.
"""

# Import Python tools
import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import boto3
from io import StringIO
from io import BytesIO
import logging
from datetime import datetime, timedelta

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

s3_resource = session.resource("s3")

# Base directory settings
base_dir = os.getcwd()
data_dir = os.path.join(base_dir, 'data', 'standings')

profile_name = os.environ.get("AWS_PERSONAL_PROFILE")
year = pd.Timestamp.today().year
year = pd.to_datetime("now").strftime("%Y")

mlb_teams = {
    "ARI": "Arizona Diamondbacks",
    "ATL": "Atlanta Braves",
    "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox",
    "CHC": "Chicago Cubs",
    "CHW": "Chicago White Sox",
    "CIN": "Cincinnati Reds",
    "CLE": "Cleveland Guardians",
    "COL": "Colorado Rockies",
    "DET": "Detroit Tigers",
    "HOU": "Houston Astros",
    "KCR": "Kansas City Royals",
    "LAA": "Los Angeles Angels",
    "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers",
    "MIN": "Minnesota Twins",
    "NYM": "New York Mets",
    "NYY": "New York Yankees",
    "ATH": "Athletics",
    "PHI": "Philadelphia Phillies",
    "PIT": "Pittsburgh Pirates",
    "SDP": "San Diego Padres",
    "SFG": "San Francisco Giants",
    "SEA": "Seattle Mariners",
    "STL": "St. Louis Cardinals",
    "TBR": "Tampa Bay Rays",
    "TEX": "Texas Rangers",
    "TOR": "Toronto Blue Jays",
    "WSN": "Washington Nationals"
}

# Configuration
year = pd.to_datetime("now").strftime("%Y")
url = f"https://www.baseball-reference.com/teams/LAD/{year}-schedule-scores.shtml"
output_dir = "data/standings"
csv_file = f"{output_dir}/dodgers_schedule.csv"
json_file = f"{output_dir}/dodgers_schedule.json"
parquet_file = f"{output_dir}/dodgers_schedule.parquet"
s3_bucket = "stilesdata.com"

def fetch_clean_current_schedule(url, year):
    response = requests.get(url)
    html_content = BeautifulSoup(response.content, 'html.parser')
    raw_df = pd.read_html(StringIO(str(html_content)))[0].rename(columns={"Gm#": "game_no", "Unnamed: 4": "home_away", 'W/L': 'result'}).assign(season=year)
    df = raw_df.query("Tm !='Tm'").copy()
    df.columns = df.columns.str.lower()
    print(df.columns)
    df['opp_name'] = df['opp'].map(mlb_teams)
    df['date'] = df['date'].dropna().str.split(', ', expand=True)[1]
    df['date'] = df['date'].str.split(' \(', expand=True)[0]
    df['date'] = pd.to_datetime(df['date'].dropna() + " " + df['season'].astype(str))
    df['date'] = df['date'].dt.strftime('%b %-d')
    df['home_away'] = df['home_away'].apply(lambda i: 'away' if i == '@' else 'home')
    # Parse result with score to preserve last game's score string
    # Example values: 'W-5-3', 'L-2-4', 'W', 'L', None
    df['result_raw'] = df['result'].astype(str)
    df['result_letter'] = df['result_raw'].str[0]
    df['result_letter'] = df['result_letter'].where(df['result_letter'].isin(['W','L']), None)
    df['result'] = df['result_letter'].map({'W':'win','L':'loss'})
    # Extract score part after first dash
    score_part = df['result_raw'].str.extract(r'^[WL]-(.+)$')[0]
    df['score'] = score_part.where(df['result'].notna(), None)
    # Where result is neither win nor loss, set placeholder
    df.loc[df['result'].isna(), 'result'] = '--'
    df = df.drop(["unnamed: 2", "streak", "orig. scheduled", 'inn', 'tm', 'ra', 'rank', 'gb', 'win', 'opp', 'loss', 'save', 'time', 'd/n', 'w-l', 'attendance'], axis=1)
    return df

# Convert time from Eastern to Pacific manually
def convert_time_to_pacific_manual(time_str):
    try:
        time = datetime.strptime(time_str, '%I:%M %p')
        time -= timedelta(hours=3)
        return time.strftime('%-I:%M %p')
    except Exception as e:
        logging.error(f"Failed to convert time: {e}")
        return time_str

src = fetch_clean_current_schedule(url, year)

# Create a more robust indicator for completed games
# A game is completed if either cli is not null OR result is 'win' or 'loss'
src['game_completed'] = (~src['cli'].isnull()) | (src['result'].isin(['win', 'loss']))

next_five = src.query('~game_completed').head(10).drop(['cli', 'season', 'game_completed'], axis=1).copy()
last_five = src.query('game_completed').tail(10).drop(['cli', 'season', 'game_completed'], axis=1).copy()
next_five['placement'] = 'next'
last_five['placement'] = 'last'

schedule_df = pd.concat([last_five, next_five], ignore_index=True)
# For completed games, show score instead of time; for upcoming, show time
schedule_df['game_start'] = schedule_df.apply(
    lambda row: row['score'] if row['result'] in ['win', 'loss'] and isinstance(row.get('score'), str) and row['score'] else row.get('r', '--'),
    axis=1
)
schedule_df = schedule_df[['date', 'opp_name', 'home_away', 'result', 'placement', 'game_start']]

# Convert time-like strings to Pacific Time; ignore scores like '5-3'
def is_time_string(s: str) -> bool:
    if not isinstance(s, str):
        return False
    return bool(pd.Series([s]).str.match(r'^\d{1,2}:\d{2}\s?(AM|PM)$', case=False, na=False).iloc[0])

schedule_df['game_start'] = schedule_df['game_start'].apply(
    lambda x: convert_time_to_pacific_manual(x) if isinstance(x, str) and is_time_string(x) else x
)

# Function to save DataFrame to S3
def save_to_s3(df, base_path, s3_bucket, formats):
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
            s3_resource.Bucket(s3_bucket).put_object(Key=f"{base_path}.{fmt}", Body=buffer, ContentType=content_type)
            logging.info(f"Uploaded {fmt} to {s3_bucket}/{base_path}.{fmt}")
        except Exception as e:
            logging.error(f"Failed to upload {fmt} to S3: {e}")

# Saving files locally and to S3
file_path = os.path.join(data_dir, 'dodgers_schedule')
formats = ["csv", "json"]
save_to_s3(schedule_df, "dodgers/data/standings/dodgers_schedule", "stilesdata.com", formats)
