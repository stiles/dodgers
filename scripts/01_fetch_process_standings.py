#!/usr/bin/env python
# coding: utf-8

# # LA Dodgers Standings, 1958-present
# > This notebook downloads the team's current standings table from [Baseball Reference](https://www.baseball-reference.com/teams/LAD/2024-schedule-scores.shtml) and combines it with historic records for later analysis and visualization.

# ---

# #### Import Python tools and Jupyter config

#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers Standings, 1958-present
This script downloads the team's current standings table from Baseball Reference and combines it with historic records.
"""

import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import boto3
from io import StringIO
import logging


# Configuration
year = 2024
url = f"https://www.baseball-reference.com/teams/LAD/{year}-schedule-scores.shtml"
output_dir = "data/standings"
csv_file = f"{output_dir}/dodgers_standings_1958_present.csv"
json_file = f"{output_dir}/dodgers_standings_1958_present.json"
historic_file = f"https://stilesdata.com/dodgers/data/standings/archive/dodgers_standings_1958_2023.parquet"
parquet_file = f"{output_dir}/dodgers_standings_1958_present.parquet"
s3_bucket = "stilesdata.com"


# Assume AWS credentials are set as environment variables
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
)
s3 = session.resource('s3')


# Fetch and process the current year's data
def fetch_current_year_data(url, year):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    src = (pd.read_html(StringIO(str(soup)))[0].query("Tm !='Tm' and Inn != 'Game Preview, and Matchups'")
              .drop(["Unnamed: 2", "Streak", "Orig. Scheduled"], axis=1)
              .rename(columns={"Unnamed: 4": "home_away"})
              .assign(season=year))
    
    src.columns = src.columns.str.lower().str.replace("/", "_").str.replace("-", "-")
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
        "year",
    ]

    # Convert date types where needed
    src["gm"] = src["gm"].astype(int)
    src["year"] = src["year"].astype(str)

    # Split, format date
    src[["weekday", "date"]] = src["date"].str.split(", ", expand=True)
    src["date"] = src["date"].str.replace(" (1)", "").str.replace(" (2)", "")
    src["game_date"] = pd.to_datetime(src["date"] + ", " + src["year"], format="%b %d, %Y").astype(str)

    # Clean home-away column
    src.loc[src.home_away == "@", "home_away"] = "away"
    src.loc[src.home_away.isna(), "home_away"] = "home"

    # Games back figures as a number
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

    src["time"] = src["time"] + ":00"
    src["time_minutes"] = pd.to_timedelta(src["time"]).dt.total_seconds() / 60
    src["time_minutes"] = src["time_minutes"].astype(int)

    src[['wins', 'losses']] = src['record'].str.split('-', expand=True).astype(int)
    src['win_pct'] = (src['wins'] / src['gm']).round(2)
    src['game_day'] = pd.to_datetime(src['game_date']).dt.day_name()

    # Just the columns we need
    src_df = src[
        [
            "gm",
            "game_date",
            "home_away",
            "opp",
            "result",
            "r",
            "ra",
            "record",
            "rank",
            "gb",
            "time",
            "time_minutes",
            "day_night",
            "attendance",
            "year",
            "wins",
            "losses",
            "win_pct",
            "game_day",
            
        ]
    ].copy()
    
    return src_df


# Load historic data
def load_historic_data(filepath):
    return pd.read_parquet(filepath)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        os.makedirs(output_dir, exist_ok=True)
        logging.info("Output directory checked/created.")

        src_df = fetch_current_year_data(url, year)
        historic_df = load_historic_data(historic_file)
        historic_df['game_date'] = historic_df['game_date'].astype(str)
        historic_df['rank'] = historic_df['rank'].astype(int)

        df = pd.concat([src_df, historic_df]).sort_values("game_date", ascending=False).drop_duplicates(subset=['gm', 'year']).reset_index(drop=True)

        df.to_json(json_file, orient="records")
        df.to_csv(csv_file, index=False)
        df.to_parquet(parquet_file, index=False)

        s3.Bucket(s3_bucket).upload_file(csv_file, s3_key_csv)
        s3.Bucket(s3_bucket).upload_file(json_file, s3_key_json)
        s3.Bucket(s3_bucket).upload_file(parquet_file, s3_key_parquet)

        logging.info("Files successfully uploaded to S3.")
    except Exception as e:
        logging.error(f"Error occurred: {e}")

if __name__ == "__main__":
    main()