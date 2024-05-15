#!/usr/bin/env python
# coding: utf-8

# # LA Dodgers current season performance
# > This notebook downloads the team's current season and outputs the data to CSV, JSON and Parquet formats for later analysis and visualization.

# ---

import os
import boto3
import pandas as pd
from io import BytesIO
from io import StringIO


pd.options.display.max_columns = 100
pd.options.display.max_rows = 1000
pd.options.display.max_colwidth = None
aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")


boto3.Session(
    aws_access_key_id=aws_key_id,
    aws_secret_access_key=aws_secret_key,
    region_name="us-west-1",
)


year = pd.to_datetime("now").strftime("%Y")


"""
Fetch
"""


df = pd.read_parquet('https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.parquet')


wl_df = df.query("year == '2024'")[["gm", "game_date", "result", "r", "ra"]].copy()
wl_df["result"] = wl_df["result"].str.split("-", expand=True)[0]
wl_df["run_diff"] = wl_df["r"] - wl_df["ra"]


""" 
EXPORT
"""


# Function to save dataframes with different formats and file extensions
def save_dataframe(df, path_without_extension, formats):
    """
    Save DataFrames in multiple formats.
    """
    for file_format in formats:
        if file_format == "csv":
            df.to_csv(f"{path_without_extension}.{file_format}", index=False)
        elif file_format == "json":
            df.to_json(
                f"{path_without_extension}.{file_format}", indent=4, orient="records"
            )
        elif file_format == "parquet":
            df.to_parquet(f"{path_without_extension}.{file_format}", index=False)
        else:
            print(f"Unsupported format: {file_format}")


# Save local files
formats = ["csv", "json", "parquet"]
save_dataframe(wl_df, f"../data/standings/dodgers_wins_losses_current", formats)


# Function to export to s3 in various formats
def save_to_s3(
    df, base_path, s3_bucket, formats=["csv", "json", "parquet"], profile_name="default"
):
    """
    Save Pandas DataFrame in specified formats and upload to S3 bucket using a specified AWS profile.

    :param df: DataFrame to save.
    :param base_path: Base file path without format extension.
    :param s3_bucket: S3 bucket name.
    :param formats: List of formats to save -- 'csv', 'json', 'parquet'.
    :param profile_name: AWS CLI profile name to use for credentials.
    """
    session = boto3.Session(profile_name=profile_name)
    s3_resource = session.resource("s3")

    for fmt in formats:
        file_path = f"{base_path}.{fmt}"
        if fmt == "csv":
            buffer = BytesIO()
            df.to_csv(buffer, index=False)
            content_type = "text/csv"
        elif fmt == "json":
            buffer = BytesIO()
            df.to_json(buffer, indent=4, orient="records")
            content_type = "application/json"
        elif fmt == "parquet":
            buffer = BytesIO()
            df.to_parquet(buffer, index=False)
            content_type = "application/octet-stream"

        buffer.seek(0)
        s3_resource.Bucket(s3_bucket).put_object(
            Key=file_path, Body=buffer, ContentType=content_type
        )
        print(f"Uploaded {fmt} to {s3_bucket}/{file_path}")


# Save to S3
save_to_s3(
    wl_df,
    "dodgers/data/standings/dodgers_wins_losses_current",
    "stilesdata.com",
    profile_name="haekeo",
)


# Save a copy of notebook as a python script
get_ipython().system('jupyter nbconvert --to script --no-prompt --output ../scripts/08_fetch_process_wins_losses_current 10_fetch_process_wins_losses_current.ipynb')

