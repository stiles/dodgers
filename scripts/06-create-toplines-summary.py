#!/usr/bin/env python
# coding: utf-8


"""
LA Dodgers toplines
This notebook extracts key statistics from the project's processed tables for display in a dashboard.
"""

import os
import pandas as pd
import boto3
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Base directory calculation for file paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read_parquet_s3(url, sort_by=None):
    """Read a Parquet file from the S3 URL.
    Only sort the dataframe if a sort column is provided.
    Batting doesn't have game dates because it's annual totals."""
    df = pd.read_parquet(url)
    if sort_by and sort_by in df.columns:
        df.sort_values(sort_by, ascending=False, inplace=True)
    return df

# URLs for data
standings_url = "https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.parquet"
batting_url = "https://stilesdata.com/dodgers/data/batting/dodgers_team_batting_1958_present.parquet"

# Load the data
standings = read_parquet_s3(standings_url, sort_by='game_date').query("year == '2024'")
standings['result'] = standings['result'].str.split('-wo', expand=True)[0]
standings.loc[standings.result == "L", "result_clean"] = "loss"
standings.loc[standings.result == "W", "result_clean"] = "win"
standings_past = read_parquet_s3(standings_url, sort_by='game_date').query("year != '2024'")
standings_now = standings.query("game_date == game_date.max()").copy()

batting = read_parquet_s3(batting_url)
batting_past = batting.query("season != '2024'").copy()
batting_now = batting.query("season == '2024'").copy()

def current_season_stats(standings_now, standings_past):
    games = standings_now["gm"].iloc[0]
    wins = standings_now["wins"].iloc[0]
    losses = standings_now["losses"].iloc[0]
    record = standings_now["record"].iloc[0]
    win_pct = int(standings_now["win_pct"].iloc[0] * 100)
    win_pct_decade_thispoint = int(
        standings_past.query(f"gm == {games}").head(10)["win_pct"].mean().round(2) * 100
    )
    return games, wins, losses, record, win_pct, win_pct_decade_thispoint

def run_differential(standings):
    runs = standings["r"].sum()
    runs_against = standings["ra"].sum()
    run_diff = runs - runs_against
    return runs, runs_against, run_diff

def home_run_stats(batting_now, batting_past):
    games = int(batting_now["g"].iloc[0])
    home_runs = int(batting_now["hr"].sum())
    home_runs_game = round(home_runs / games, 2)
    batting_past["hr_game"] = batting_past["hr"].astype(int) / batting_past["g"].astype(int).round(2)
    home_runs_game_last = batting_past.query('season == "2023"')["hr_game"].iloc[0]
    games_decade = batting_past.head(10)["g"].astype(int).sum()
    home_runs_decade = batting_past.head(10)["hr"].astype(int).sum()
    home_runs_game_decade = round(home_runs_decade / games_decade, 2)
    return home_runs, home_runs_game, home_runs_game_last, home_runs_game_decade

def batting_and_stolen_base_stats(batting_now, batting_past, games):
    batting_average = batting_now["ba"].iloc[0]
    batting_average_decade = round(
        batting_past.head(10)["ba"].astype(float).mean(), 3
    ).astype(str).replace("0.", ".")
    stolen_bases = int(batting_now["sb"].iloc[0])
    stolen_bases_game = round(stolen_bases / games, 2)
    stolen_decade = batting_past.head(10)["sb"].astype(int).sum()
    stolen_bases_decade_game = round(stolen_decade / games, 2)
    return batting_average, batting_average_decade, stolen_bases, stolen_bases_game, stolen_bases_decade_game

def generate_summary(standings_now, wins, losses, win_pct):
    last_game = standings_now.iloc[0]
    summary = (
        f"The Dodgers have played {games} games this season compiling a {record} record — "
        f"a winning percentage of {win_pct}%. The team's last game was a "
        f"{last_game['r']}-{last_game['ra']} {last_game['home_away']} {last_game['result_clean']} "
        f"to the {last_game['opp']} in front of {'{:,}'.format(last_game['attendance'])} fans. "
        f"The team has won {win_count_trend} of its last 10 games."
    )
    return summary

def recent_trend(standings):
    last_10 = standings.iloc[:10]['result']  # Ensuring the last 10 games are considered
    win_count_trend = last_10[last_10 == "W"].count()
    loss_count_trend = last_10[last_10 == "L"].count()
    return win_count_trend, loss_count_trend, f"Recent trend: {win_count_trend} wins, {loss_count_trend} losses"

games, wins, losses, record, win_pct, win_pct_decade_thispoint = current_season_stats(standings_now, standings_past)
runs, runs_against, run_diff = run_differential(standings)
home_runs, home_runs_game, home_runs_game_last, home_runs_game_decade = home_run_stats(batting_now, batting_past)
batting_average, batting_average_decade, stolen_bases, stolen_bases_game, stolen_bases_decade_game = batting_and_stolen_base_stats(batting_now, batting_past, games)
win_count_trend, loss_count_trend, win_loss_trend = recent_trend(standings.iloc[:10])

summary = generate_summary(standings, wins, losses, win_pct)

summary_data = [
    {"stat_label": "Wins", "stat": "wins", "value": wins, "category": "standings"},
    {"stat_label": "Losses", "stat": "losses", "value": losses, "category": "standings"},
    {"stat_label": "Record", "stat": "record", "value": record, "category": "standings"},
    {"stat_label": "Win percentage", "stat": "win_pct", "value": f"{win_pct}%", "category": "standings"},
    {"stat_label": "Win % this decade", "stat": "win_pct_decade_thispoint", "value": f"{win_pct_decade_thispoint}%", "category": "standings"},
    {"stat_label": "Runs", "stat": "runs", "value": runs, "category": "standings"},
    {"stat_label": "Runs against", "stat": "runs_against", "value": runs_against, "category": "standings"},
    {"stat_label": "Run differential", "stat": "run_differential", "value": run_diff, "category": "standings"},
    {"stat_label": "Home runs", "stat": "home_runs", "value": home_runs, "category": "batting"},
    {"stat_label": "Home runs/game", "stat": "home_runs_game", "value": home_runs_game, "category": "batting"},
    {"stat_label": "HR/game last season", "stat": "home_runs_game_last", "value": home_runs_game_last, "category": "batting"},
    {"stat_label": "HR/game last decade", "stat": "home_runs_game_decade", "value": home_runs_game_decade, "category": "batting"},
    {"stat_label": "Stolen bases", "stat": "stolen_bases", "value": stolen_bases, "category": "batting"},
    {"stat_label": "Stolen bases per game", "stat": "stolen_bases_game", "value": stolen_bases_game, "category": "batting"},
    {"stat_label": "Stolen per game last decade", "stat": "stolen_bases_decade_game", "value": stolen_bases_decade_game, "category": "batting"},
    {"stat_label": "Batting average", "stat": "batting_average", "value": batting_average, "category": "batting"},
    {"stat_label": "Batting average last decade", "stat": "batting_average_decade", "value": batting_average_decade, "category": "batting"},
    {"stat_label": "Recent trned", "stat": "recent_trend", "value": win_loss_trend, "category": "standings"},
    {"stat_label": "Team summary", "stat": "summary", "value": summary, "category": "standings"}
]

summary_df = pd.DataFrame(summary_data)
summary_df.to_csv(os.path.join(base_dir, 'data', 'standings', 'season_summary_latest.csv'), index=False)
summary_df.to_json(os.path.join(base_dir, 'data', 'standings', 'season_summary_latest.json'), orient='records', indent=4, lines=False)

def save_to_s3(df, base_path, s3_bucket, formats=["csv", "json"]):
    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name="us-west-1"
    )
    s3_resource = session.resource("s3")
    for fmt in formats:
        file_path = f"{base_path}.{fmt}"
        buffer = BytesIO()
        if fmt == "csv":
            df.to_csv(buffer, index=False)
            content_type = "text/csv"
        elif fmt == "json":
            df.to_json(buffer, orient="records", indent=4, lines=False)
            content_type = "application/json"
        buffer.seek(0)
        s3_resource.Bucket(s3_bucket).put_object(Key=file_path, Body=buffer, ContentType=content_type)
        logging.info(f"Uploaded {fmt} to {s3_bucket}/{file_path}")

save_to_s3(summary_df, "dodgers/data/standings/season_summary_latest", "stilesdata.com")