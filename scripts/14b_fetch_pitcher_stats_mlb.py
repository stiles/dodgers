#!/usr/bin/env python
# coding: utf-8

import os
import requests
import datetime
import pandas as pd
from io import BytesIO
import boto3
import logging


# Set up basic configuration for logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Determine if running in a GitHub Actions environment
is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"

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
        region_name=aws_region,
    )
else:
    # Locally, use a specific profile
    session = boto3.Session(profile_name="haekeo", region_name=aws_region)

s3_resource = session.resource("s3")

# Base directory settings
base_dir = os.getcwd()
data_dir = os.path.join(base_dir, "data", "pitching")
os.makedirs(data_dir, exist_ok=True)

profile_name = os.environ.get("AWS_PERSONAL_PROFILE")
today = datetime.date.today()
year = today.year
year = pd.to_datetime("now").strftime("%Y")

# Headers for requests
headers = {
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "sec-ch-ua-platform": '"macOS"',
}

# Fetch pitcher stats from BDFed API
pitcher_list = requests.get(
    f"https://bdfed.stitch.mlbinfra.com/bdfed/stats/player?&env=prod&season={year}&sportId=1&stats=season&group=pitching&gameType=R&offset=0&sortStat=inningsPitched&order=desc&teamId=119",
    headers=headers,
)

# Select columns we need
cols = [
    "playerName",
    "positionAbbrev",
    "gamesStarted",
    "gamesPlayed",
    "inningsPitched",
    "era",
    "whip",
    "strikeoutsPer9",
    "baseOnBallsPer9",
    "strikesoutsToWalks",
]

df = pd.DataFrame(pitcher_list.json()["stats"])[cols].rename(
    columns={
        "playerName": "player",
        "positionAbbrev": "position",
        "gamesStarted": "gs",
        "gamesPlayed": "gp",
        "inningsPitched": "ip",
        "strikeoutsPer9": "k9",
        "baseOnBallsPer9": "bb9",
        "strikesoutsToWalks": "kbb",
    }
)

# Derive role from games started
df["role"] = df["gs"].apply(lambda x: "SP" if x > 0 else "RP")

# Convert IP to float for filtering
df["ip_float"] = df["ip"].astype(float)

# Filter to pitchers with at least 10 IP
df_filtered = df[df["ip_float"] >= 10.0].copy()

# Take top 10 by innings pitched (already sorted from API)
df_top10 = df_filtered.head(10).copy()

# Round IP for display
df_top10.loc[:, "ip_rounded"] = df_top10["ip_float"].round(0).astype(int)

# Select final columns for output
output_cols = ["player", "role", "position", "era", "whip", "k9", "bb9", "kbb", "ip", "ip_rounded", "gs", "gp"]
df_final = df_top10[output_cols]

df_final["fetched"] = today.strftime("%Y-%m-%d")

logging.info(f"Found {len(df_final)} pitchers with 10+ IP")

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
            elif fmt == "parquet":
                df.to_parquet(buffer, index=False)
                content_type = "application/octet-stream"
            buffer.seek(0)
            s3_resource.Bucket(s3_bucket).put_object(
                Key=f"{base_path}.{fmt}", Body=buffer, ContentType=content_type
            )
            logging.info(f"Uploaded {fmt} to {s3_bucket}/{base_path}.{fmt}")
        except Exception as e:
            logging.error(f"Failed to upload {fmt} to S3: {e}")


# Saving files locally and to S3
file_path = os.path.join(data_dir, "dodgers_pitcher_stats_current_table")
formats = ["csv", "json", "parquet"]

# Save locally
for fmt in formats:
    try:
        if fmt == "csv":
            df_final.to_csv(f"{file_path}.{fmt}", index=False)
        elif fmt == "json":
            df_final.to_json(f"{file_path}.{fmt}", indent=4, orient="records")
        elif fmt == "parquet":
            df_final.to_parquet(f"{file_path}.{fmt}", index=False)
        logging.info(f"Saved local file: {file_path}.{fmt}")
    except Exception as e:
        logging.error(f"Failed to save local {fmt}: {e}")

# Upload to S3
save_to_s3(
    df_final,
    "dodgers/data/pitching/dodgers_pitcher_stats_current_table",
    "stilesdata.com",
    formats,
)

logging.info("Pitcher stats fetch complete!")
