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
import requests
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


def fetch_nl_west_standings(season: int) -> pd.DataFrame:
    """Fetch game-by-game standings for all NL West teams"""
    import requests
    
    # NL West team IDs
    NL_WEST_TEAMS = {
        119: 'Los Angeles Dodgers',
        109: 'Arizona Diamondbacks',
        137: 'San Francisco Giants',
        135: 'San Diego Padres',
        115: 'Colorado Rockies'
    }
    
    all_games = []
    
    for team_id, team_name in NL_WEST_TEAMS.items():
        logging.info(f"Fetching schedule for {team_name}")
        
        url = "https://statsapi.mlb.com/api/v1/schedule"
        params = {
            'sportId': 1,
            'teamId': team_id,
            'season': season,
            'gameType': 'R',  # Regular season only
            'hydrate': 'team,linescore'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for date_entry in data.get('dates', []):
                for game in date_entry.get('games', []):
                    if game.get('status', {}).get('abstractGameState') != 'Final':
                        continue
                    
                    game_date = pd.to_datetime(game.get('gameDate')).strftime('%Y-%m-%d')
                    teams = game.get('teams', {})
                    home_team_id = teams.get('home', {}).get('team', {}).get('id')
                    away_team_id = teams.get('away', {}).get('team', {}).get('id')
                    
                    # Determine if this team won
                    if home_team_id == team_id:
                        team_score = teams.get('home', {}).get('score', 0)
                        opp_score = teams.get('away', {}).get('score', 0)
                    else:
                        team_score = teams.get('away', {}).get('score', 0)
                        opp_score = teams.get('home', {}).get('score', 0)
                    
                    won = team_score > opp_score
                    
                    all_games.append({
                        'team_id': team_id,
                        'team_name': team_name,
                        'game_date': game_date,
                        'won': won
                    })
        
        except Exception as e:
            logging.error(f"Failed to fetch schedule for {team_name}: {e}")
            continue
    
    if not all_games:
        logging.warning("No NL West games fetched")
        return pd.DataFrame()
    
    df = pd.DataFrame(all_games)
    df['game_date'] = pd.to_datetime(df['game_date'])
    df = df.sort_values(['team_id', 'game_date']).reset_index(drop=True)
    
    # Calculate cumulative wins and losses by team
    df['wins'] = df.groupby('team_id')['won'].cumsum().astype(int)
    df['games'] = df.groupby('team_id').cumcount() + 1
    df['losses'] = df['games'] - df['wins']
    
    logging.info(f"Fetched {len(df)} total NL West games")
    return df


def calculate_games_back(dodgers_standings: pd.DataFrame, nl_west_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate game-by-game games back/up for Dodgers"""
    dodgers_standings = dodgers_standings.copy()
    dodgers_standings['game_date'] = pd.to_datetime(dodgers_standings['game_date'])
    
    gb_values = []
    
    for idx, row in dodgers_standings.iterrows():
        game_date = row['game_date']
        dodgers_wins = row['wins']
        dodgers_losses = row['losses']
        
        # Get all NL West teams' records as of this date
        teams_as_of_date = nl_west_df[nl_west_df['game_date'] <= game_date].copy()
        
        if teams_as_of_date.empty:
            gb_values.append(0.0)
            continue
        
        # Get latest record for each team as of this date
        latest_records = teams_as_of_date.groupby('team_id').tail(1).copy()
        
        # Find division leader (most wins, best win %)
        latest_records = latest_records.copy()
        latest_records['win_pct'] = latest_records['wins'] / (latest_records['wins'] + latest_records['losses'])
        leader = latest_records.sort_values(['wins', 'win_pct'], ascending=False).iloc[0]
        
        leader_wins = leader['wins']
        leader_losses = leader['losses']
        
        # Calculate games back/up
        # GB = ((Leader Wins - Team Wins) + (Team Losses - Leader Losses)) / 2
        gb = ((leader_wins - dodgers_wins) + (dodgers_losses - leader_losses)) / 2.0
        
        # If Dodgers are the leader, negate to show games UP
        if leader['team_id'] == 119:  # Dodgers team ID
            # Find second place team
            other_teams = latest_records[latest_records['team_id'] != 119]
            if not other_teams.empty:
                second_place = other_teams.sort_values(['wins', 'win_pct'], ascending=False).iloc[0]
                gb = -((dodgers_wins - second_place['wins']) + (second_place['losses'] - dodgers_losses)) / 2.0
        
        gb_values.append(gb)
    
    dodgers_standings['gb'] = gb_values
    dodgers_standings['game_date'] = dodgers_standings['game_date'].dt.strftime('%Y-%m-%d')
    
    return dodgers_standings


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
    standings["gtm"] = standings["gm"]  # Alias for charts
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
        
        # Fetch NL West standings and calculate games back
        logging.info("Fetching NL West standings for games back calculation")
        nl_west_df = fetch_nl_west_standings(year)
        
        if not nl_west_df.empty:
            logging.info("Calculating games back")
            standings_current = calculate_games_back(standings_current, nl_west_df)
        else:
            logging.warning("Could not fetch NL West standings, gb will be 0")
        
        # Load historical archive (1958-2025)
        logging.info("Loading historical standings archive")
        try:
            historic_df = pd.read_parquet(HISTORIC_ARCHIVE)
            logging.info(f"Loaded {len(historic_df)} historical records")
        except Exception as e:
            logging.error(f"Failed to load historical archive: {e}", exc_info=True)
            raise
        
        # Calculate cumulative wins/losses for historical data if missing
        if historic_df['wins'].isna().any():
            logging.info("Calculating cumulative wins/losses for historical data")
            # Group by year and calculate cumulative stats
            historic_df = historic_df.sort_values(['year', 'gm'])
            historic_df['wins'] = historic_df.groupby('year')['result'].apply(
                lambda x: (x == 'W').cumsum()
            ).values
            historic_df['losses'] = historic_df.groupby('year')['result'].apply(
                lambda x: (x == 'L').cumsum()
            ).values
            # Recalculate win_pct
            historic_df['win_pct'] = (historic_df['wins'] / historic_df['gm']).round(3)
            logging.info("Cumulative stats calculated for historical data")
        
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
