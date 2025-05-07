#!/usr/bin/env python
# coding: utf-8

import os
import requests
import boto3
import pandas as pd
import sys

# Always resolve output_dir relative to the project root (dodgers/)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
default_output_dir = os.path.join(project_root, 'data/batting')
output_dir = os.environ.get("SHOHEI_OUTPUT_DIR", default_output_dir)
os.makedirs(output_dir, exist_ok=True)

current_year = pd.Timestamp("now").year

# Headers for requests
headers = {
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "sec-ch-ua-platform": '"macOS"',
}

stars = [
    "Shohei Ohtani",
]

def fetch_shohei_timeseries(season):
    # Get Shohei's playerId for the given season
    batter_list = requests.get(
        f"https://bdfed.stitch.mlbinfra.com/bdfed/stats/player?&env=prod&season={season}&sportId=1&stats=season&group=hitting&gameType=R&offset=0&sortStat=homeRuns&order=desc&teamId=119",
        headers=headers,
    )
    batters = pd.DataFrame(batter_list.json()["stats"])
    shohei = batters.query('playerName == "Shohei Ohtani"').iloc[0]
    params = {
        "playerId": shohei["playerId"],
        "type": "",
        "season": season,
    }
    pitch_data = requests.get(
        "https://baseballsavant.mlb.com/player-viz/lookup",
        params=params,
        headers=headers,
    ).json()["data"]
    pitch_df = pd.DataFrame(pitch_data).query("is_lastpitch == 1").fillna("")
    pitch_df["game_date"] = pd.to_datetime(pitch_df["game_date"])
    pitch_df = pitch_df.sort_values("game_date").copy()
    pitch_df["pa_number"] = pitch_df.groupby(["batter_name"])["play_id"].cumcount() + 1
    # Add game_number (increment for each unique game_date)
    pitch_df = pitch_df.sort_values(["game_date", "pa_number"]).copy()
    pitch_df["game_number"] = pitch_df["game_date"].rank(method="dense").astype(int)
    # Filter for home run at bats
    shohei_homer_at_bats = pitch_df.query(
        "is_hit_into_play_basehit == 1 and events == 'home_run'"
    ).copy()
    # Group by game_date and count home runs per game
    home_runs_per_game = shohei_homer_at_bats.groupby("game_date").size().reset_index(name="home_runs")
    home_runs_per_game = home_runs_per_game.sort_values("game_date")
    home_runs_per_game["home_runs_cum"] = home_runs_per_game["home_runs"].cumsum()
    # Merge game_number and pa_number for each home run
    merged = pd.merge(
        home_runs_per_game,
        pitch_df.drop_duplicates("game_date")[["game_date", "game_number"]],
        on="game_date",
        how="left",
    )
    # For each home run, get the pa_number of the last HR in that game
    pa_merge = shohei_homer_at_bats.groupby("game_date")["pa_number"].max().reset_index()
    merged = pd.merge(merged, pa_merge, on="game_date", how="left")
    merged["season"] = season
    return merged[["season", "game_date", "game_number", "pa_number", "home_runs_cum"]]

def fetch_shohei_sb_timeseries(season):
    player_id = 660271  # Shohei Ohtani
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group=hitting&season={season}"
    resp = requests.get(url)
    data = resp.json()
    games = data.get('stats', [{}])[0].get('splits', [])
    if not games:
        return pd.DataFrame(columns=["season", "game_date", "game_number", "sb_cum"])
    rows = []
    for i, g in enumerate(games, 1):
        game_date = g['date']
        sb = int(g['stat'].get('stolenBases', 0))
        rows.append({
            "season": season,
            "game_date": game_date,
            "game_number": i,
            "sb": sb
        })
    df = pd.DataFrame(rows)
    df["game_date"] = pd.to_datetime(df["game_date"])
    df = df.sort_values("game_date").reset_index(drop=True)
    df["sb_cum"] = df["sb"].cumsum()
    return df[["season", "game_date", "game_number", "sb_cum"]]

# URLs for 2024 data
hr_2024_url = "https://stilesdata.com/dodgers/data/batting/shohei_home_runs_cumulative_timeseries_2024.json"
sb_2024_url = "https://stilesdata.com/dodgers/data/batting/shohei_stolen_bases_cumulative_timeseries_2024.json"

# Load 2024 data from S3-hosted URLs
hr_2024 = pd.read_json(hr_2024_url)
sb_2024 = pd.read_json(sb_2024_url)

# Generate 2025 data as before
hr_2025 = fetch_shohei_timeseries(2025)
sb_2025 = fetch_shohei_sb_timeseries(2025)

# Save separate files
hr_2025.to_json(
    os.path.join(output_dir, "shohei_home_runs_cumulative_timeseries_2025.json"),
    orient="records", date_format="iso", indent=4
)
sb_2025.to_json(
    os.path.join(output_dir, "shohei_stolen_bases_cumulative_timeseries_2025.json"),
    orient="records", date_format="iso", indent=4
)

# Save combined files
combined = pd.concat([hr_2024, hr_2025], ignore_index=True)
combined.to_json(
    os.path.join(output_dir, "shohei_home_runs_cumulative_timeseries_combined.json"),
    orient="records", date_format="iso", indent=4
)

sb_combined = pd.concat([sb_2024, sb_2025], ignore_index=True)
sb_combined.to_json(
    os.path.join(output_dir, "shohei_stolen_bases_cumulative_timeseries_combined.json"),
    orient="records", date_format="iso", indent=4
)

# S3 upload if AWS credentials are present
aws_key = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
s3_bucket = os.getenv('SHOHEI_S3_BUCKET', 'stilesdata.com')

files_to_upload = [
    (os.path.join(output_dir, "shohei_home_runs_cumulative_timeseries_2024.json"),
     "dodgers/data/batting/shohei_home_runs_cumulative_timeseries_2024.json"),
    (os.path.join(output_dir, "shohei_home_runs_cumulative_timeseries_2025.json"),
     "dodgers/data/batting/shohei_home_runs_cumulative_timeseries_2025.json"),
    (os.path.join(output_dir, "shohei_home_runs_cumulative_timeseries_combined.json"),
     "dodgers/data/batting/shohei_home_runs_cumulative_timeseries_combined.json"),
    (os.path.join(output_dir, "shohei_stolen_bases_cumulative_timeseries_2024.json"),
     "dodgers/data/batting/shohei_stolen_bases_cumulative_timeseries_2024.json"),
    (os.path.join(output_dir, "shohei_stolen_bases_cumulative_timeseries_2025.json"),
     "dodgers/data/batting/shohei_stolen_bases_cumulative_timeseries_2025.json"),
    (os.path.join(output_dir, "shohei_stolen_bases_cumulative_timeseries_combined.json"),
     "dodgers/data/batting/shohei_stolen_bases_cumulative_timeseries_combined.json"),
]

if aws_key and aws_secret or os.getenv('AWS_PROFILE') or os.path.exists(os.path.expanduser('~/.aws/credentials')):
    try:
        # Prefer profile if available
        session = None
        if os.getenv('AWS_PROFILE') or os.path.exists(os.path.expanduser('~/.aws/credentials')):
            session = boto3.Session(profile_name='haekeo')
        else:
            session = boto3.Session(
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
            )
        s3 = session.resource('s3')
        uploaded = False
        for local_path, s3_key in files_to_upload:
            if os.path.exists(local_path):
                s3.Bucket(s3_bucket).upload_file(local_path, s3_key)
                print(f"Uploaded {local_path} to s3://{s3_bucket}/{s3_key}")
                uploaded = True
        if not uploaded:
            print("No files were uploaded to S3. Check your output directory and credentials.")
    except Exception as e:
        print(f"S3 upload failed: {e}")
        sys.exit(1)
