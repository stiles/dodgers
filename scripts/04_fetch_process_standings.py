#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers Standings: Build from MLB API boxscores archive
Replaces Baseball Reference scraping with archive-based processing
"""

import os
import pandas as pd
import boto3
import json
import logging
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
BUCKET = "stilesdata.com"
BOXES_KEY_JSON = "dodgers/data/standings/dodgers_boxscores.json"
LOCAL_BOXES_JSON = os.path.join("data", "standings", "dodgers_boxscores.json")
HISTORIC_ARCHIVE = "https://stilesdata.com/dodgers/data/standings/archive/dodgers_standings_1958_2025.parquet"

output_dir = "data/standings"
year = datetime.now().year  # Keep as int to match historical data


def get_s3_client(profile_name: Optional[str] = None):
    """Get S3 client with local/CI fallback"""
    if profile_name:
        session = boto3.session.Session(profile_name=profile_name)
        return session.client("s3")
    
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return boto3.client("s3")
    
    env_profile = os.environ.get("AWS_PROFILE")
    resolved = env_profile or "haekeo"
    session = boto3.session.Session(profile_name=resolved)
    return session.client("s3")


def load_boxscores(profile_name: Optional[str] = None) -> pd.DataFrame:
    """Load boxscores archive from S3 or local"""
    # Try S3 first
    try:
        s3 = get_s3_client(profile_name)
        obj = s3.get_object(Bucket=BUCKET, Key=BOXES_KEY_JSON)
        text = obj["Body"].read().decode("utf-8")
        logging.info(f"Loaded boxscores from S3: {BOXES_KEY_JSON}")
        return pd.DataFrame(json.loads(text))
    except Exception as e:
        logging.warning(f"Could not load from S3: {e}")
    
    # Try local
    if os.path.exists(LOCAL_BOXES_JSON):
        with open(LOCAL_BOXES_JSON, "r", encoding="utf-8") as f:
            logging.info(f"Loaded boxscores from local: {LOCAL_BOXES_JSON}")
            return pd.DataFrame(json.load(f))
    
    raise FileNotFoundError("Boxscores archive not found in S3 or local")


def build_standings_from_boxscores(df: pd.DataFrame, season: int) -> pd.DataFrame:
    """Build game-by-game standings from boxscores archive"""
    df = df.copy()
    
    # Filter for final games only and current season
    if "is_final" in df.columns:
        df = df[df["is_final"] == True]
    
    # Normalize date
    df["game_date"] = pd.to_datetime(df.get("date", df.get("game_date")))
    df = df[df["game_date"].dt.year == season]
    
    # Exclude spring training exhibitions (Angels games in March)
    march_angels = (
        (df["game_date"].dt.month == 3) & 
        (df["opponent_name"].str.contains("Angels", na=False))
    )
    df = df[~march_angels]
    
    # Sort by date
    df = df.sort_values("game_date").reset_index(drop=True)
    
    if df.empty:
        logging.warning(f"No games found for season {season}")
        return pd.DataFrame()
    
    # Build core stats
    standings = pd.DataFrame()
    standings["gm"] = range(1, len(df) + 1)
    standings["game_date"] = df["game_date"].dt.strftime("%Y-%m-%d")
    standings["year"] = season
    
    # Home/away (convert dodgers_is_home boolean to home/away string)
    standings["home_away"] = df["dodgers_is_home"].apply(lambda x: "home" if x else "away")
    
    # Opponent
    standings["opp"] = df["opponent_name"]
    
    # Scores
    standings["r"] = df["dodgers_runs"].astype(int)
    standings["ra"] = df["opponent_runs"].astype(int)
    
    # Result
    standings["run_diff"] = standings["r"] - standings["ra"]
    standings["result"] = standings["run_diff"].apply(
        lambda x: "W" if x > 0 else ("L" if x < 0 else "T")
    )
    
    # Cumulative wins/losses
    standings["wins"] = (standings["result"] == "W").cumsum()
    standings["losses"] = (standings["result"] == "L").cumsum()
    standings["record"] = standings["wins"].astype(str) + "-" + standings["losses"].astype(str)
    
    # Win percentage
    standings["win_pct"] = (standings["wins"] / standings["gm"]).round(3)
    
    # Games back (relative to division leader at that point)
    # For now, set to 0 (would need historical standings data to compute accurately)
    standings["gb"] = 0
    standings["rank"] = 1  # Simplified - would need division standings history
    
    # Attendance (from boxscores if available)
    if "attendance" in df.columns:
        standings["attendance"] = df["attendance"].fillna(0).astype(int)
    else:
        standings["attendance"] = 0
    
    # Game metadata
    if "game_time_minutes" in df.columns:
        standings["time_minutes"] = df["game_time_minutes"].fillna(0).astype(int)
    else:
        standings["time_minutes"] = 0
    
    # Convert time_minutes to HH:MM:SS format
    hours = standings["time_minutes"] // 60
    minutes = standings["time_minutes"] % 60
    standings["time"] = hours.astype(str).str.zfill(2) + ":" + minutes.astype(str).str.zfill(2) + ":00"
    
    # Day/night - not in boxscores, default to N
    standings["day_night"] = "N"
    standings["game_day"] = df["game_date"].dt.day_name()
    
    logging.info(f"Built standings for {season}: {len(standings)} games")
    return standings


def save_dataframe_formats(df: pd.DataFrame, base_path: str, formats: list):
    """Save DataFrame in multiple formats"""
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    
    for fmt in formats:
        file_path = f"{base_path}.{fmt}"
        if fmt == "csv":
            df.to_csv(file_path, index=False)
        elif fmt == "json":
            df.to_json(file_path, orient="records", indent=2)
        elif fmt == "parquet":
            df.to_parquet(file_path, index=False)
        logging.info(f"Saved {fmt}: {file_path}")


def upload_to_s3(df: pd.DataFrame, s3_key: str, profile_name: Optional[str] = None):
    """Upload DataFrame to S3 in multiple formats"""
    try:
        s3 = get_s3_client(profile_name)
        
        # CSV
        csv_buffer = df.to_csv(index=False).encode("utf-8")
        s3.put_object(Bucket=BUCKET, Key=f"{s3_key}.csv", Body=csv_buffer, ContentType="text/csv")
        logging.info(f"Uploaded to S3: {s3_key}.csv")
        
        # JSON
        json_buffer = df.to_json(orient="records", indent=2).encode("utf-8")
        s3.put_object(Bucket=BUCKET, Key=f"{s3_key}.json", Body=json_buffer, ContentType="application/json")
        logging.info(f"Uploaded to S3: {s3_key}.json")
        
        # Parquet
        parquet_buffer = df.to_parquet(index=False)
        s3.put_object(Bucket=BUCKET, Key=f"{s3_key}.parquet", Body=parquet_buffer, ContentType="application/octet-stream")
        logging.info(f"Uploaded to S3: {s3_key}.parquet")
        
    except Exception as e:
        logging.error(f"S3 upload failed: {e}")
        raise


def main():
    """Main execution"""
    try:
        profile_name = os.environ.get("AWS_PROFILE", "haekeo" if os.environ.get("GITHUB_ACTIONS") != "true" else None)
        
        logging.info(f"Building standings for season {year} from boxscores archive")
        
        # Load boxscores archive
        boxscores_df = load_boxscores(profile_name)
        logging.info(f"Loaded {len(boxscores_df)} total boxscore records")
        
        # Build current season standings
        standings_current = build_standings_from_boxscores(boxscores_df, year)
        
        if standings_current.empty:
            logging.error(f"No standings data generated for {year}")
            return
        
        # Load historical archive (1958-2025)
        logging.info("Loading historical standings archive")
        try:
            historic_df = pd.read_parquet(HISTORIC_ARCHIVE)
            logging.info(f"Loaded {len(historic_df)} historical records")
        except Exception as e:
            logging.error(f"Failed to load historical archive: {e}", exc_info=True)
            raise
        
        # Ensure consistent data types before combining
        # Convert game_date to string in both dataframes to avoid Parquet mixed-type errors
        logging.info("Converting data types for compatibility")
        standings_current["game_date"] = standings_current["game_date"].astype(str)
        historic_df["game_date"] = pd.to_datetime(historic_df["game_date"]).dt.strftime("%Y-%m-%d")
        
        # Ensure year is int in both dataframes
        standings_current["year"] = standings_current["year"].astype(int)
        historic_df["year"] = historic_df["year"].astype(int)
        
        # Combine current season with historical
        logging.info("Combining current season with historical data")
        combined_df = pd.concat([standings_current, historic_df]).sort_values(
            ["year", "gm"], ascending=[False, True]
        ).reset_index(drop=True)
        
        logging.info(f"Combined total: {len(combined_df)} records")
        
        # Save locally
        logging.info("Saving files locally")
        formats = ["csv", "json", "parquet"]
        save_dataframe_formats(standings_current, f"{output_dir}/dodgers_standings_current", formats)
        save_dataframe_formats(combined_df, f"{output_dir}/dodgers_standings_1958_present", formats)
        
        # Upload to S3
        logging.info("Uploading to S3")
        upload_to_s3(standings_current, "dodgers/data/standings/dodgers_standings_current", profile_name)
        upload_to_s3(combined_df, "dodgers/data/standings/dodgers_standings_1958_present", profile_name)
        
        logging.info("Standings processing complete!")
    
    except Exception as e:
        logging.error(f"Fatal error in main(): {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
