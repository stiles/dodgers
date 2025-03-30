#!/usr/bin/env python
# coding: utf-8

# # LA Dodgers batting: Combine current season with historical archive
# > This notebook downloads the team's current batting tables from [Baseball Reference](https://www.baseball-reference.com/teams/LAD/2024-batting.shtml), combines it with a historical archive to 1958 and outputs the data to CSV, JSON and Parquet formats for later analysis and visualization.

# Import Python tools and Jupyter config

import os
import boto3
import pandas as pd
from io import BytesIO
from io import StringIO

aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

# Fetch

year = pd.to_datetime("now").strftime("%Y")

url = f"https://www.baseball-reference.com/teams/LAD/{year}-batting.shtml"


# Fetch batters table, excluding team totals
player_totals_df = (
    pd.read_html(url)[0]
    .query(f"~Rk.isna() and Rk != 'Rk'")
    .dropna(thresh=7)
    .assign(season=year)
    .rename(columns={'GIDP':'gdp'})
)
player_totals_df.columns = player_totals_df.columns.str.lower().str.replace(
    "+", "_plus"
)

# Team stats
summary_df = (
    pd.read_html(url)[0]
    .query(f"Rk.isna() and Rk != 'Rk'")
    .dropna(thresh=7)
    .assign(season=year)
    .rename(columns={'GIDP':'gdp', 'Player': 'name'})  # Rename 'name' column to avoid conflicts
)
summary_df.columns = summary_df.columns.str.lower().str.replace("+", "_plus")



# Player stats
# Remove injury details listed parenthetically next to some players' names
player_totals_df["player"] = (
    player_totals_df["player"].str.split("(", expand=True)[0].str.strip()
)

# Determine batter type, clean special characters from names
def determine_and_clean_bats(name):
    # Determine batting stance
    if name.endswith("*"):
        bat = "Left"
    elif name.endswith("#"):
        bat = "Both"
    elif name.endswith("?"):
        bat = "Unknown"
    else:
        bat = "Right"

    if name[-1] in "*#?":
        name = name[:-1]

    return bat, name


# Apply the function and separate the results into two columns
player_totals_df["bats"], player_totals_df["name_clean"] = zip(
    *player_totals_df["player"].apply(determine_and_clean_bats)
)


# Replace the original 'player' column with the cleaned names
player_totals_df["player"] = player_totals_df["name_clean"]
del player_totals_df["name_clean"]

player_totals_df[
    [
        "g",
        "pa",
        "ab",
        "r",
        "h",
        "2b",
        "3b",
        "hr",
        "rbi",
        "sb",
        "cs",
        "bb",
        "so",
        "tb",
        "gdp",
        "hbp",
        "sh",
        "sf",
        "ibb",
    ]
] = player_totals_df[
    [
        "g",
        "pa",
        "ab",
        "r",
        "h",
        "2b",
        "3b",
        "hr",
        "rbi",
        "sb",
        "cs",
        "bb",
        "so",
        "tb",
        "gdp",
        "hbp",
        "sh",
        "sf",
        "ibb",
    ]
].astype(
    int
)


player_totals_df[["ba", "obp", "slg", "ops", "ops_plus"]] = player_totals_df[
    ["ba", "obp", "slg", "ops", "ops_plus"]
].astype(float)

player_totals_df = player_totals_df.rename(columns={'player': 'name'})

# Team stats
# The main batting table has totals for the team, with totals and ranks by season

# Team totals
team_totals_df = summary_df[summary_df['name'] == "Team Totals"].dropna(axis=1)

# Team ranks
team_ranks_df = summary_df.query('name.str.contains("Rank")').dropna(axis=1)

# Combine
# Concatenate current season player totals with historical player archive

player_totals_archive_df = pd.read_parquet(
    "https://stilesdata.com/dodgers/data/batting/archive/dodgers_player_batting_statistics_1958_2023.parquet"
)

players_full_df = (
    pd.concat([player_totals_df, player_totals_archive_df])
    .sort_values("season", ascending=False)
    .reset_index(drop=True)
)

team_totals_archive_df = pd.read_parquet(
    "https://stilesdata.com/dodgers/data/batting/archive/dodgers_team_batting_statistics_1958_2023.parquet"
)


team_full_df = (
    pd.concat([team_totals_df, team_totals_archive_df])
    .sort_values("season", ascending=False)
    .reset_index(drop=True)
)


team_ranks_archive_df = pd.read_parquet(
    "https://stilesdata.com/dodgers/data/batting/archive/dodgers_team_batting_rankings_1958_2023.parquet"
)


team_ranks_full_df = (
    pd.concat([team_ranks_df, team_ranks_archive_df])
    .sort_values("season", ascending=False)
    .reset_index(drop=True)
)

# Export
# Function to save dataframes with different formats and file extensions

def save_dataframe(df, path_without_extension, formats):
    os.makedirs(os.path.dirname(path_without_extension), exist_ok=True)  # Ensure directory exists
    for file_format in formats:
        file_path = f"{path_without_extension}.{file_format}"
        if file_format == "csv":
            df.to_csv(file_path, index=False)
        elif file_format == "json":
            df.to_json(file_path, orient="records", lines=True)
        elif file_format == "parquet":
            df.to_parquet(file_path, index=False)

# Save local files

try:
    formats = ["csv", "json", "parquet"]
    save_dataframe(
        players_full_df,
        f"../data/batting/dodgers_player_batting_1958_present",
        formats,
    )
    save_dataframe(
        team_full_df, f"../data/batting/dodgers_team_batting_1958_present", formats
    )
    save_dataframe(
        team_ranks_full_df,
        f"../data/batting/dodgers_team_batting_ranks_1958_present",
        formats,
    )
except Exception as e:
    print(f"An error occurred: {e}")

def save_to_s3(df, base_path, s3_bucket, formats=["csv", "json", "parquet"]):
    """
    Save Pandas DataFrame in specified formats and upload to S3 bucket using environment credentials.

    :param df: DataFrame to save.
    :param base_path: Base file path without format extension.
    :param s3_bucket: S3 bucket name.
    :param formats: List of formats to save -- 'csv', 'json', 'parquet'.
    """
    # Create session using environment variables directly
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name='us-west-1'  
    )
    s3_resource = session.resource("s3")

    for fmt in formats:
        file_path = f"{base_path}.{fmt}"
        buffer = BytesIO()
        if fmt == "csv":
            df.to_csv(buffer, index=False)
            content_type = "text/csv"
        elif fmt == "json":
            df.to_json(buffer, orient="records", lines=True)
            content_type = "application/json"
        elif fmt == "parquet":
            df.to_parquet(buffer, index=False)
            content_type = "application/octet-stream"

        buffer.seek(0)
        s3_resource.Bucket(s3_bucket).put_object(
            Key=file_path, Body=buffer, ContentType=content_type
        )
        print(f"Uploaded {fmt} to {s3_bucket}/{file_path}")


# Save to S3
save_to_s3(
    players_full_df,
    "dodgers/data/batting/dodgers_player_batting_1958_present",
    "stilesdata.com",
)
save_to_s3(
    team_full_df,
    "dodgers/data/batting/dodgers_team_batting_1958_present",
    "stilesdata.com",
)
save_to_s3(
    team_ranks_full_df,
    "dodgers/data/batting/dodgers_team_batting_ranks_1958_present",
    "stilesdata.com",
)
