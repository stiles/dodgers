#!/usr/bin/env python
# coding: utf-8

"""
Add a completed season to the historical standings archive.
Reads from dodgers_standings_current (MLB API output from script 04)
instead of scraping Baseball Reference.

Usage:
    python scripts/add_season_to_archive.py              # adds previous year
    python scripts/add_season_to_archive.py --year 2026  # adds specific year
"""

import argparse
import os
import sys
import pandas as pd
import boto3
import json
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BUCKET = "stilesdata.com"
ARCHIVE_BASE = "dodgers/data/standings/archive"
STANDINGS_KEY = "dodgers/data/standings/dodgers_standings_current"
LOCAL_STANDINGS = os.path.join("data", "standings", "dodgers_standings_current.json")
OUTPUT_DIR = os.path.join("data", "standings", "archive")


def get_s3_client(profile_name: Optional[str] = None):
    """Get S3 client with local/CI fallback"""
    if profile_name:
        return boto3.session.Session(profile_name=profile_name).client("s3")

    if os.environ.get("GITHUB_ACTIONS") == "true":
        return boto3.client("s3")

    resolved = os.environ.get("AWS_PROFILE") or "haekeo"
    return boto3.session.Session(profile_name=resolved).client("s3")


def load_season_data(year: int, profile_name: Optional[str] = None) -> pd.DataFrame:
    """Load a completed season from dodgers_standings_current (S3 or local)"""
    # Try S3 first
    try:
        s3 = get_s3_client(profile_name)
        obj = s3.get_object(Bucket=BUCKET, Key=f"{STANDINGS_KEY}.json")
        text = obj["Body"].read().decode("utf-8")
        df = pd.DataFrame(json.loads(text))
        logging.info(f"Loaded standings from S3: {STANDINGS_KEY}.json")
    except Exception as e:
        logging.warning(f"Could not load from S3: {e}")
        if os.path.exists(LOCAL_STANDINGS):
            with open(LOCAL_STANDINGS, "r", encoding="utf-8") as f:
                df = pd.DataFrame(json.load(f))
            logging.info(f"Loaded standings from local: {LOCAL_STANDINGS}")
        else:
            raise FileNotFoundError("Standings file not found in S3 or local")

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    season_df = df[df["year"] == year].copy()

    if season_df.empty:
        raise ValueError(f"No games found for {year} in standings file")

    logging.info(f"Found {len(season_df)} games for {year}")
    return season_df


def resolve_archive_url(year_end: int) -> str:
    """Build the S3 URL for the current archive parquet"""
    return f"https://{BUCKET}/{ARCHIVE_BASE}/dodgers_standings_1958_{year_end}.parquet"


def main():
    from datetime import datetime

    parser = argparse.ArgumentParser(description="Add a completed season to the standings archive")
    parser.add_argument("--year", type=int, default=datetime.now().year - 1,
                        help="Season year to archive (default: previous year)")
    args = parser.parse_args()
    year_to_add = args.year

    profile_name = os.environ.get(
        "AWS_PROFILE",
        "haekeo" if os.environ.get("GITHUB_ACTIONS") != "true" else None,
    )

    # Load the completed season from MLB API output
    logging.info(f"Loading {year_to_add} season data from standings file")
    season_df = load_season_data(year_to_add, profile_name)

    # Flip GB sign: script 04 uses negative = leading,
    # but the archive convention is positive = leading (from Baseball Reference era)
    season_df["gb"] = -season_df["gb"]
    logging.info(f"Flipped GB sign for {year_to_add} to match archive convention (positive = leading)")

    # Ensure year is stored as string to match historical archive
    season_df["year"] = season_df["year"].astype(str)

    # Load existing archive
    archive_end = year_to_add - 1
    archive_url = resolve_archive_url(archive_end)
    logging.info(f"Loading archive from {archive_url}")
    historic_df = pd.read_parquet(archive_url)
    logging.info(f"Archive loaded: {len(historic_df)} rows, years {historic_df['year'].min()}-{historic_df['year'].max()}")

    # Combine
    combined_df = pd.concat([historic_df, season_df], ignore_index=True)
    combined_df = combined_df.sort_values(["year", "gm"]).reset_index(drop=True)
    combined_df["rank"] = pd.to_numeric(combined_df["rank"], errors="coerce").astype("Int64")
    combined_df["year"] = combined_df["year"].astype(str)

    logging.info(f"Combined: {len(combined_df)} rows, years {combined_df['year'].min()}-{combined_df['year'].max()}")

    # Save locally
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    new_archive = os.path.join(OUTPUT_DIR, f"dodgers_standings_1958_{year_to_add}.parquet")
    combined_df.to_parquet(new_archive, index=False)
    logging.info(f"Saved to {new_archive}")

    # Upload to S3
    try:
        s3 = get_s3_client(profile_name)
        s3_key = f"{ARCHIVE_BASE}/dodgers_standings_1958_{year_to_add}.parquet"
        with open(new_archive, "rb") as f:
            s3.put_object(Bucket=BUCKET, Key=s3_key, Body=f.read(), ContentType="application/octet-stream")
        logging.info(f"Uploaded to s3://{BUCKET}/{s3_key}")
    except Exception as e:
        logging.error(f"Failed to upload to S3: {e}")
        return 1

    logging.info(f"Successfully added {year_to_add} to archive!")

    # Remind to update the HISTORIC_ARCHIVE constant in 04_fetch_process_standings.py
    new_url = f"https://{BUCKET}/{ARCHIVE_BASE}/dodgers_standings_1958_{year_to_add}.parquet"
    logging.info(f"Next step: update HISTORIC_ARCHIVE in scripts/04_fetch_process_standings.py to:\n  {new_url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
