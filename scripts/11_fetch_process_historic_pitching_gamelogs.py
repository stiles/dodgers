#!/usr/bin/env python
# coding: utf-8

# # LA Dodgers pitching logs by season, 1958-2024
# > This script processes current and past game-by-game and cumulative totals for strikeouts, walks, ERA, etc., using data from [Baseball Reference](https://www.baseball-reference.com/teams/tgl.cgi?team=LAD&t=p&year=2024).

# ---

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
    # session = boto3.Session(region_name=aws_region)


s3_resource = session.resource("s3")

# Base directory settings
base_dir = os.getcwd()
data_dir = os.path.join(base_dir, 'data', 'pitching')
# os.makedirs(data_dir, exist_ok=True)

profile_name = os.environ.get("AWS_PERSONAL_PROFILE")
today = datetime.date.today()
year = pd.to_datetime("now").strftime("%Y")


# Headers to mimic a browser request
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
}


# Fetch archive game logs
archive_url = "https://stilesdata.com/dodgers/data/pitching/archive/dodgers_historic_pitching_gamelogs_1958_2023.parquet"
archive_df = pd.read_parquet(archive_url)


# Fetch Current game logs
current_url = f"https://www.baseball-reference.com/teams/tgl.cgi?team=LAD&t=p&year={year}"
# Use index [0] for the main table and assign year
current_src = pd.read_html(current_url)[0].assign(year=year)
# Drop the top level of the MultiIndex columns
current_src.columns = current_src.columns.droplevel(0)
# Lowercase column names
current_src.columns = current_src.columns.str.lower()
# Rename the column that was ('year', '') and became '' to 'year'
current_src = current_src.rename(columns={'': 'year'})
# Filter out header/summary rows by ensuring 'gtm' is a numeric value
current_src = current_src[pd.to_numeric(current_src['gtm'], errors='coerce').notna()]


# Process current game logs
current_src["game_date"] = pd.to_datetime(
    current_src["date"] + " " + current_src["year"].astype(str),
    format="%b %d %Y",
    errors="coerce"
).dt.strftime("%Y-%m-%d")


# Just the columns we need
keep_cols = ['gtm', 'year', 'game_date', 'h', 'hr', 'er', 'so', 'era']
current_df = current_src[keep_cols].copy()


# Define value columns
int_cols = ["gtm", 'h', 'hr', 'er', 'so']

# Convert value columns to numbers
current_df[int_cols] = current_df[int_cols].astype(int)
current_df['era'] = current_df['era'].astype(float)
current_df['era_cum'] = current_df['era']


# Calculate cumulative columns
for col in ['h', 'hr', 'er', 'so']:
    current_df[f"{col}_cum"] = current_df.groupby("year")[col].cumsum()


"""
MERGE
"""

# Combine current and archive data
df = (
    pd.concat([current_df, archive_df])
    .sort_values(["year", "gtm"], ascending=[False, True])
    .reset_index(drop=True)
    .drop_duplicates()
)

"""
OUTPUT
"""

# Optimize DataFrame for output
optimized_df = df[['gtm', 'year', 'game_date', 'era_cum','h_cum', 'hr_cum', 'er_cum', 'so_cum']].copy()


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
            s3_resource.Bucket(s3_bucket).put_object(Key=f"{base_path}.{fmt}", Body=buffer, ContentType=content_type)
            logging.info(f"Uploaded {fmt} to {s3_bucket}/{base_path}.{fmt}")
        except Exception as e:
            logging.error(f"Failed to upload {fmt} to S3: {e}")

# Saving files locally and to S3
file_path = os.path.join(data_dir, 'dodgers_historic_pitching_gamelogs_1958-present')
formats = ["csv", "json", "parquet"]
# save_dataframe(optimized_df, file_path, formats)
save_to_s3(optimized_df, "dodgers/data/pitching/dodgers_historic_pitching_gamelogs_1958-present", "stilesdata.com", formats)

