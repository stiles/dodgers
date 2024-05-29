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
# os.makedirs(data_dir, exist_ok=True)

profile_name = os.environ.get("AWS_PERSONAL_PROFILE")
year = pd.Timestamp.today().year


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
    "OAK": "Oakland Athletics",
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
year = 2024
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
    df['opp_name'] = df['opp'].map(mlb_teams)
    df['date'] = df['date'].dropna().str.split(', ', expand=True)[1]
    df['date'] = df['date'].str.split(' \(', expand=True)[0]
    df['date'] = pd.to_datetime(df['date'].dropna() + " " + df['season'].astype(str))
    df['date'] = df['date'].dt.strftime('%b %-d')
    df['home_away'] = df['home_away'].apply(lambda i: 'away' if i == '@' else 'home')
    # df['result'] = df['result'].apply(lambda i: 'win' if i == 'W' else 'loss')
    # df['result'] = df['result'].apply(lambda i: 'win' if i == 'W' else 'loss')
    df["result"] = df["result"].str.split('-', expand=True)[0]
    df.loc[df["result"] == "W", "result"] = 'win'
    df.loc[df["result"] == "L", "result"] = 'loss'
    df.loc[~df["result"].str.contains("win|loss"), "result"] = '--'
    df = df.drop(["unnamed: 2", "streak", "orig. scheduled", 'inn', 'tm', 'ra', 'rank', 'gb', 'win', 'opp', 'loss', 'save', 'time', 'd/n', 'w-l', 'attendance'], axis=1)
    return df


src = fetch_clean_current_schedule(url, year)
next_five = src.query('cli.isnull()').head(10).drop(['cli', 'season'], axis=1).copy()
last_five = src.query('~cli.isnull()').tail(10).drop(['cli', 'season'], axis=1).copy()
next_five['placement'] = 'next'
last_five['placement'] = 'last'


schedule_df = pd.concat([last_five, next_five])[['date', 'opp_name', 'home_away', 'result', 'placement', 'r']].rename(columns={'r': 'game_start'})
schedule_df.loc[schedule_df.result != '--', 'game_start'] = '--'

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
# save_dataframe(optimized_df, file_path, formats)
save_to_s3(schedule_df, "dodgers/data/standings/dodgers_schedule", "stilesdata.com", formats)