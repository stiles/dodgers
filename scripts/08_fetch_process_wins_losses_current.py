#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers current season performance
This notebook downloads the team's current season and outputs the data to CSV, JSON and Parquet formats for later analysis and visualization.
"""

import os
import pandas as pd
import boto3
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
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(base_dir, 'data', 'standings')
os.makedirs(data_dir, exist_ok=True)

year = pd.to_datetime("now").strftime("%Y")

"""
Fetch
"""

df = pd.read_parquet('https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.parquet')

wl_df = df.query("year == '2024'")[["gm", "game_date", "result", "r", "ra"]].copy()
wl_df["result"] = wl_df["result"].str.split("-", expand=True)[0]
wl_df["run_diff"] = wl_df["r"] - wl_df["ra"]
wl_df["game_date"] = wl_df["game_date"].astype(str)

""" 
EXPORT
"""

def save_dataframe(df, path_without_extension, formats):
    for file_format in formats:
        try:
            full_path = f"{path_without_extension}.{file_format}"
            if file_format == "csv":
                df.to_csv(full_path, index=False)
            elif file_format == "json":
                df.to_json(full_path, indent=4, orient="records", lines=False)
            elif file_format == "parquet":
                df.to_parquet(full_path, index=False)
            logging.info(f"Saved {file_format} format to {full_path}")
        except Exception as e:
            logging.error(f"Failed to save {file_format}: {e}")

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
            s3_resource.Bucket(s3_bucket).put_object(Key=f"{base_path}.{fmt}", Body=buffer, ContentType=content_type)
            logging.info(f"Uploaded {fmt} to {s3_bucket}/{base_path}.{fmt}")
        except Exception as e:
            logging.error(f"Failed to upload {fmt} to S3: {e}")

# Saving files locally and to S3
file_path = os.path.join(data_dir, 'dodgers_wins_losses_current')
formats = ["csv", "json", "parquet"]
save_dataframe(wl_df, file_path, formats)
save_to_s3(wl_df, "dodgers/data/standings/dodgers_wins_losses_current", "stilesdata.com", formats)
