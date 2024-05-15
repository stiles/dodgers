#!/usr/bin/env python
# coding: utf-8

# # LA Dodgers pitching
# > This notebook downloads the team's current pitching table from [Baseball Reference](https://www.baseball-reference.com/teams/LAD/2024-pitching.shtml#all_team_pitching) and outputs the data to CSV, JSON and Parquet formats for later analysis and visualization.

# ---

# #### Import Python tools and Jupyter config

import os
import boto3
import pandas as pd
import jupyter_black
from io import BytesIO
from io import StringIO
from tqdm.notebook import tqdm


jupyter_black.load()
pd.options.display.max_columns = 100
pd.options.display.max_rows = 1000
pd.options.display.max_colwidth = None
aws_key_id = os.environ.get("HAEKEO_AWS_KEY")
aws_secret_key = os.environ.get("HAEKEO_AWS_SECRET")


boto3.Session(
    aws_access_key_id=aws_key_id,
    aws_secret_access_key=aws_secret_key,
    region_name="us-west-1",
)


# ---

# ## Fetch

# #### Pitching for the current season

year = pd.to_datetime("now").strftime("%Y")


url = f"https://www.baseball-reference.com/teams/LAD/{year}-pitching.shtml#all_team_pitching"


# ---

# ## Team stats

summary_df = (
    pd.read_html(url)[0]
    .query(f"Rk.isna() and Rk != 'Rk'")
    .dropna(thresh=7)
    .assign(season=year)
)
summary_df.columns = summary_df.columns.str.lower()


# #### Ranks

ranks = (
    summary_df.query('name == "Rank in 15 NL teams"')
    .dropna(axis=1)
    .reset_index(drop=True)
).copy()


# #### Totals

totals = (
    summary_df.query('name == "Team Totals"')
    .dropna(axis=1)
    .reset_index(drop=True)
    .copy()
)


ranks["era"].iloc[0]


totals["era"].iloc[0]


# ---

# ## Export

# #### Function to save dataframes with different formats and file extensions

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


# #### Save local files

formats = ["csv", "json", "parquet"]
save_dataframe(totals, f"../data/pitching/dodgers_pitching_totals_current", formats)
save_dataframe(
    ranks,
    f"../data/pitching/dodgers_pitching_ranks_current",
    formats,
)


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
            df.to_json(buffer, orient="records", lines=True)
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
    totals,
    "dodgers/data/pitching/dodgers_pitching_totals_current",
    "stilesdata.com",
    profile_name="haekeo",
)
save_to_s3(
    ranks,
    "dodgers/data/pitching/dodgers_pitching_ranks_current",
    "stilesdata.com",
    profile_name="haekeo",
)


# Save a copy of notebook as python script
get_ipython().system('jupyter nbconvert --to script --no-prompt --output ../scripts/05_fetch_process_pitching 08_fetch_process_pitching.ipynb')




