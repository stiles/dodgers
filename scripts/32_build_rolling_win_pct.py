#!/usr/bin/env python
"""
Build a compact rolling win-percentage dataset for streak barcode charts.

Uses the combined Dodgers standings history and calculates a rolling 20-game
winning percentage for every season, saving a lightweight JSON payload for the
homepage comparison module.
"""

import argparse
import json
import logging
import os
from datetime import datetime
from io import BytesIO

import boto3
import pandas as pd
import pytz

WINDOW_SIZE = 20
INPUT_FILE = "data/standings/dodgers_standings_1958_present.parquet"
OUTPUT_FILE = "data/standings/dodgers_rolling_win_pct_20.json"
S3_BUCKET = "stilesdata.com"
S3_KEY = "dodgers/data/standings/dodgers_rolling_win_pct_20.json"
RECOMMENDED_COMPARISONS = [2025, 2024, 2022, 2020, 2017, 1988]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_s3_resource():
    """Get S3 resource with environment-based credentials."""
    if os.getenv("GITHUB_ACTIONS") == "true":
        session = boto3.Session(
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name="us-west-1",
        )
    else:
        profile = os.environ.get("AWS_PROFILE", "haekeo")
        session = boto3.Session(profile_name=profile, region_name="us-west-1")

    return session.resource("s3")


def get_pacific_time() -> str:
    """Return current Pacific time as an ISO string."""
    pacific = pytz.timezone("US/Pacific")
    return datetime.now(pacific).isoformat()


def load_standings_history() -> pd.DataFrame:
    """Load the combined Dodgers standings history."""
    logging.info("Loading standings history from %s", INPUT_FILE)
    return pd.read_parquet(INPUT_FILE, columns=["year", "gm", "game_date", "result"])


def build_rolling_dataset(df: pd.DataFrame) -> dict:
    """Calculate rolling winning percentage and shape the export payload."""
    games = df.copy()
    games["result"] = (
        games["result"].astype("string").str.strip().str.extract(r"^([WL])(?:\b|$)", expand=False)
    )
    games = games.dropna(subset=["result"]).copy()

    games["year"] = pd.to_numeric(games["year"], errors="raise").astype(int)
    games["gm"] = pd.to_numeric(games["gm"], errors="raise").astype(int)
    games["game_date"] = pd.to_datetime(games["game_date"], errors="raise")

    games = games.sort_values(["year", "gm"]).reset_index(drop=True)
    games["is_win"] = games["result"].eq("W").astype(int)
    games["rolling_win_pct_20"] = games.groupby("year")["is_win"].transform(
        lambda s: s.rolling(WINDOW_SIZE, min_periods=WINDOW_SIZE).mean()
    )
    games["rolling_wins_20"] = (games["rolling_win_pct_20"] * WINDOW_SIZE).round().astype("Int64")

    rolling_games = games.dropna(subset=["rolling_win_pct_20"]).copy()
    rolling_games["rolling_win_pct_20"] = rolling_games["rolling_win_pct_20"].round(3)
    rolling_games["game_date"] = rolling_games["game_date"].dt.strftime("%Y-%m-%d")

    latest_year = int(rolling_games["year"].max())
    records = rolling_games[
        ["year", "gm", "game_date", "result", "rolling_win_pct_20", "rolling_wins_20"]
    ].to_dict(orient="records")

    logging.info("Built rolling dataset with %s records across %s seasons", len(records), rolling_games["year"].nunique())

    return {
        "window_size": WINDOW_SIZE,
        "current_year": latest_year,
        "recommended_comparisons": RECOMMENDED_COMPARISONS,
        "last_updated": get_pacific_time(),
        "records": records,
    }


def save_locally(payload: dict):
    """Save payload to the repo data directory."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    logging.info("Saved rolling win-percentage dataset locally to %s", OUTPUT_FILE)


def save_to_s3(payload: dict):
    """Upload payload to S3."""
    buffer = BytesIO()
    buffer.write(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    buffer.seek(0)

    s3 = get_s3_resource()
    s3.Bucket(S3_BUCKET).put_object(
        Key=S3_KEY,
        Body=buffer,
        ContentType="application/json",
    )
    logging.info("Uploaded rolling win-percentage dataset to s3://%s/%s", S3_BUCKET, S3_KEY)


def main(local_only: bool = False):
    df = load_standings_history()
    payload = build_rolling_dataset(df)
    save_locally(payload)

    if not local_only:
        save_to_s3(payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build rolling 20-game win percentage dataset")
    parser.add_argument("--local-only", action="store_true", help="Skip the S3 upload step")
    args = parser.parse_args()
    main(local_only=args.local_only)
