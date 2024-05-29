#!/usr/bin/env python
# coding: utf-8

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
data_dir = os.path.join(base_dir, "data", "batting")
# os.makedirs(data_dir, exist_ok=True)

profile_name = os.environ.get("AWS_PERSONAL_PROFILE")
today = datetime.date.today()
year = today.year


# Headers for requests
headers = {
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "sec-ch-ua-platform": '"macOS"',
}


batter_list = requests.get(
    "https://bdfed.stitch.mlbinfra.com/bdfed/stats/player?&env=prod&season=2024&sportId=1&stats=season&group=hitting&gameType=R&offset=0&sortStat=plateAppearances&order=desc&teamId=119",
    headers=headers,
)


cols = [
    "playerName",
    "positionAbbrev",
    "plateAppearances",
    "totalBases",
    "leftOnBase",
    "extraBaseHits",
    "pitchesPerPlateAppearance",
    "walksPerPlateAppearance",
    "strikeoutsPerPlateAppearance",
    "homeRunsPerPlateAppearance",
    "flyOuts",
    "totalSwings",
    "swingAndMisses",
    "ballsInPlay",
    "popOuts",
    "lineOuts",
    "groundOuts",
    "flyHits",
    "popHits",
    "lineHits",
    "groundHits",
    "gamesPlayed",
    "airOuts",
    "runs",
    "doubles",
    "triples",
    "homeRuns",
    "strikeOuts",
    "baseOnBalls",
    "intentionalWalks",
    "hits",
    "avg",
    "atBats",
    "obp",
    "slg",
    "ops",
    "stolenBases",
    "groundIntoDoublePlay",
    "rbi",
]


df = pd.DataFrame(batter_list.json()["stats"])[cols].rename(
    columns={
        "playerName": "player",
        "positionAbbrev": "postion",
        "walksPerPlateAppearance": "bbper",
        "strikeoutsPerPlateAppearance": "soper",
        "homeRunsPerPlateAppearance": "hrper",
    }
)


df["fetched"] = today.strftime("%Y-%m-%d")


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
file_path = os.path.join(data_dir, "dodgers_player_batting_current_table")
formats = ["csv", "json", "parquet"]
# save_dataframe(optimized_df, file_path, formats)
save_to_s3(
    df,
    "dodgers/data/batting/dodgers_player_batting_current_table",
    "stilesdata.com",
    formats,
)


# Save a copy of notebook as a python script
get_ipython().system('jupyter nbconvert --to script --no-prompt --output ../scripts/14_fetch_process_batting_mlb 14_fetch_process_batting_mlb.ipynb')

