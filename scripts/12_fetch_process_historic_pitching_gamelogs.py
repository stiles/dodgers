#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers game-by-game pitching stats from MLB API
Builds cumulative pitching gamelogs for charts (ERA, K's, hits allowed, etc.)
"""

import os
import boto3
import pandas as pd
import requests
import json
import logging
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DODGERS_TEAM_ID = 119
BUCKET = "stilesdata.com"
LOCAL_BOXES = "data/standings/dodgers_boxscores.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}


def get_s3_client(profile_name: Optional[str] = None):
    """Get S3 client"""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return boto3.client("s3")
    
    profile = profile_name or os.environ.get("AWS_PROFILE", "haekeo")
    session = boto3.session.Session(profile_name=profile)
    return session.client("s3")


def load_boxscores(profile_name: Optional[str] = None) -> pd.DataFrame:
    """Load boxscores archive from S3 or local"""
    # Try S3 first
    try:
        s3 = get_s3_client(profile_name)
        obj = s3.get_object(Bucket=BUCKET, Key="dodgers/data/standings/dodgers_boxscores.json")
        text = obj["Body"].read().decode("utf-8")
        logging.info(f"Loaded boxscores from S3")
        return pd.DataFrame(json.loads(text))
    except Exception as e:
        logging.warning(f"Could not load from S3: {e}")
    
    # Try local
    if os.path.exists(LOCAL_BOXES):
        with open(LOCAL_BOXES, 'r') as f:
            logging.info(f"Loaded boxscores from local: {LOCAL_BOXES}")
            data = json.load(f)
        return pd.DataFrame(data)
    
    raise FileNotFoundError(f"Could not load boxscores from S3 or local ({LOCAL_BOXES})")


def fetch_game_pitching_stats(game_pk: int, season: int) -> dict:
    """Fetch pitching stats for a single game"""
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Find Dodgers team stats
        dodgers_stats = None
        if data.get('liveData', {}).get('boxscore', {}).get('teams'):
            teams = data['liveData']['boxscore']['teams']
            
            # Check if home or away
            if teams['home']['team']['id'] == DODGERS_TEAM_ID:
                dodgers_stats = teams['home']['teamStats']['pitching']
            elif teams['away']['team']['id'] == DODGERS_TEAM_ID:
                dodgers_stats = teams['away']['teamStats']['pitching']
        
        if not dodgers_stats:
            logging.warning(f"Could not find Dodgers stats for game {game_pk}")
            return None
        
        # Extract key stats
        return {
            'game_pk': game_pk,
            'innings_pitched': dodgers_stats.get('inningsPitched', '0.0'),
            'hits': dodgers_stats.get('hits', 0),
            'runs': dodgers_stats.get('runs', 0),
            'earned_runs': dodgers_stats.get('earnedRuns', 0),
            'walks': dodgers_stats.get('baseOnBalls', 0),
            'strikeouts': dodgers_stats.get('strikeOuts', 0),
            'home_runs': dodgers_stats.get('homeRuns', 0),
            'hit_by_pitch': dodgers_stats.get('hitByPitch', 0),
            'wild_pitches': dodgers_stats.get('wildPitches', 0),
            'balks': dodgers_stats.get('balks', 0),
        }
        
    except Exception as e:
        logging.error(f"Failed to fetch game {game_pk}: {e}")
        return None


def innings_to_outs(ip_str: str) -> int:
    """Convert innings pitched string (e.g., '9.0', '8.1') to outs"""
    try:
        parts = str(ip_str).split('.')
        full_innings = int(parts[0])
        partial = int(parts[1]) if len(parts) > 1 else 0
        return (full_innings * 3) + partial
    except:
        return 0


def outs_to_innings(outs: int) -> str:
    """Convert outs to innings pitched string"""
    full_innings = outs // 3
    partial = outs % 3
    return f"{full_innings}.{partial}"


def build_pitching_gamelogs(season: int) -> pd.DataFrame:
    """Build game-by-game pitching stats for the season"""
    logging.info(f"Loading boxscores for {season}")
    boxes_df = load_boxscores()
    
    # Filter for current season and final games
    boxes_df['date'] = pd.to_datetime(boxes_df['date'])
    boxes_df = boxes_df[
        (boxes_df['date'].dt.year == season) & 
        (boxes_df['is_final'] == True)
    ].sort_values('date').reset_index(drop=True)
    
    # Exclude spring training
    march_angels = (
        (boxes_df['date'].dt.month == 3) & 
        (boxes_df['opponent_name'].str.contains("Angels", na=False))
    )
    boxes_df = boxes_df[~march_angels]
    
    logging.info(f"Fetching pitching stats for {len(boxes_df)} games")
    
    game_stats = []
    for idx, row in boxes_df.iterrows():
        game_pk = row['game_pk']
        game_date = row['date'].strftime('%Y-%m-%d')
        
        logging.info(f"Fetching game {idx + 1}/{len(boxes_df)}: {game_date} (PK: {game_pk})")
        stats = fetch_game_pitching_stats(game_pk, season)
        if stats:
            stats['game_date'] = game_date
            stats['game_number'] = idx + 1
            game_stats.append(stats)
        else:
            logging.warning(f"Skipped game {game_pk} - no stats returned")
    
    logging.info(f"Successfully fetched {len(game_stats)}/{len(boxes_df)} games")
    
    if not game_stats:
        logging.error("No pitching stats collected")
        return pd.DataFrame()
    
    df = pd.DataFrame(game_stats)
    
    # Add year column
    df['year'] = season
    
    # Convert IP to outs for cumulative calculation
    df['outs'] = df['innings_pitched'].apply(innings_to_outs)
    
    # Add cumulative columns (long names for clarity)
    df['cumulative_outs'] = df['outs'].cumsum()
    df['cumulative_innings_pitched'] = df['cumulative_outs'].apply(outs_to_innings)
    df['cumulative_hits'] = df['hits'].cumsum()
    df['cumulative_runs'] = df['runs'].cumsum()
    df['cumulative_earned_runs'] = df['earned_runs'].cumsum()
    df['cumulative_walks'] = df['walks'].cumsum()
    df['cumulative_strikeouts'] = df['strikeouts'].cumsum()
    df['cumulative_home_runs'] = df['home_runs'].cumsum()
    
    # Calculate cumulative ERA (earned runs per 9 innings)
    df['cumulative_era'] = (df['cumulative_earned_runs'] * 27 / df['cumulative_outs']).round(2)
    df['cumulative_era'] = df['cumulative_era'].replace([float('inf'), float('-inf')], 0)
    
    # Add short field name aliases to match historical data schema
    df['era_cum'] = df['cumulative_era']
    df['h_cum'] = df['cumulative_hits']
    df['hr_cum'] = df['cumulative_home_runs']
    df['er_cum'] = df['cumulative_earned_runs']
    df['so_cum'] = df['cumulative_strikeouts']
    
    logging.info(f"Built pitching gamelogs: {len(df)} games")
    return df


def save_outputs(df: pd.DataFrame, season: int, profile_name: Optional[str] = None):
    """Save locally and to S3"""
    base_path = f"data/pitching/dodgers_pitching_gamelogs_{season}"
    os.makedirs("data/pitching", exist_ok=True)
    
    # Save locally
    df.to_csv(f"{base_path}.csv", index=False)
    df.to_json(f"{base_path}.json", orient='records', indent=2)
    df.to_parquet(f"{base_path}.parquet", index=False)
    logging.info(f"Saved locally: {base_path}")
    
    # Upload to S3
    try:
        s3 = get_s3_client(profile_name)
        s3_base = f"dodgers/data/pitching/dodgers_pitching_gamelogs_{season}"
        
        # CSV
        csv_buf = df.to_csv(index=False).encode('utf-8')
        s3.put_object(Bucket=BUCKET, Key=f"{s3_base}.csv", Body=csv_buf, ContentType="text/csv")
        
        # JSON
        json_buf = df.to_json(orient='records', indent=2).encode('utf-8')
        s3.put_object(Bucket=BUCKET, Key=f"{s3_base}.json", Body=json_buf, ContentType="application/json")
        
        # Parquet
        parquet_buf = df.to_parquet(index=False)
        s3.put_object(Bucket=BUCKET, Key=f"{s3_base}.parquet", Body=parquet_buf)
        
        logging.info(f"Uploaded to S3: {s3_base}")
    except Exception as e:
        logging.error(f"S3 upload failed: {e}")


def main():
    """Main execution"""
    current_season = datetime.now().year
    profile = os.environ.get("AWS_PROFILE", "haekeo" if os.environ.get("GITHUB_ACTIONS") != "true" else None)
    
    # Build 2025 and 2026 seasons
    seasons_to_build = [2025, current_season]
    all_new_data = []
    
    logging.info(f"Will build gamelogs for seasons: {seasons_to_build}")
    for season in seasons_to_build:
        logging.info(f"===== Building pitching gamelogs for {season} =====")
        df_season = build_pitching_gamelogs(season)
        
        if not df_season.empty:
            all_new_data.append(df_season)
            logging.info(f"✅ Built {len(df_season)} games for {season}")
        else:
            logging.warning(f"⚠️  No data generated for {season}")
    
    if not all_new_data:
        logging.error("No data generated for any season")
        return
    
    # Combine 2025 + 2026
    df_recent = pd.concat(all_new_data, ignore_index=True)
    
    # Save current season files
    save_outputs(df_recent[df_recent['year'] == current_season], current_season, profile)
    
    # Load historical archive (1958-2024)
    HISTORIC_URL = "https://stilesdata.com/dodgers/data/pitching/archive/dodgers_historic_pitching_gamelogs_1958_2024.parquet"
    try:
        logging.info("Loading historical pitching gamelogs archive (1958-2024)")
        df_historic = pd.read_parquet(HISTORIC_URL)
        logging.info(f"Loaded {len(df_historic)} historical records")
        
        # Combine: historic (1958-2024) + recent (2025-2026)
        df_combined = pd.concat([df_recent, df_historic]).sort_values(
            ['year', 'gtm'], ascending=[False, True]
        ).reset_index(drop=True)
        
        logging.info(f"Combined total: {len(df_combined)} records (years: 1958-{current_season})")
        
        # Upload combined file to archive path (what the charts use)
        s3 = get_s3_client(profile)
        archive_key = "dodgers/data/pitching/dodgers_historic_pitching_gamelogs_1958-present"
        
        # JSON (what the chart uses)
        json_buf = df_combined.to_json(orient='records', indent=2).encode('utf-8')
        s3.put_object(Bucket=BUCKET, Key=f"{archive_key}.json", Body=json_buf, ContentType="application/json")
        logging.info(f"Uploaded combined archive to S3: {archive_key}.json")
        
    except Exception as e:
        logging.error(f"Could not load/combine historical archive: {e}", exc_info=True)
        raise
    
    # Print summary
    df_current_only = df_recent[df_recent['year'] == current_season]
    if not df_current_only.empty:
        print(f"\n{current_season} season totals through game {len(df_current_only)}:")
        print(f"  Innings pitched: {df_current_only['cumulative_innings_pitched'].iloc[-1]}")
        print(f"  ERA: {df_current_only['cumulative_era'].iloc[-1]}")
        print(f"  Strikeouts: {df_current_only['cumulative_strikeouts'].iloc[-1]}")
        print(f"  Hits allowed: {df_current_only['cumulative_hits'].iloc[-1]}")
        print(f"  Walks: {df_current_only['cumulative_walks'].iloc[-1]}")



if __name__ == "__main__":
    main()
