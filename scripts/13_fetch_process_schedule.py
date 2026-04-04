#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers schedule from MLB Stats API
Creates tables showing last 10 games and next 10 games
"""

import os
import pandas as pd
import requests
import boto3
import logging
from datetime import datetime, timedelta
from io import BytesIO
import pytz

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DODGERS_TEAM_ID = 119
BUCKET = "stilesdata.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}


def get_s3_resource():
    """Get S3 resource with environment-based credentials"""
    if os.getenv('GITHUB_ACTIONS') == 'true':
        session = boto3.Session(
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name="us-west-1"
        )
    else:
        profile = os.environ.get("AWS_PROFILE", "haekeo")
        session = boto3.Session(profile_name=profile, region_name="us-west-1")
    
    return session.resource("s3")


def fetch_schedule_from_mlb_api(season: int) -> pd.DataFrame:
    """Fetch full season schedule from MLB Stats API"""
    # Get schedule for entire season
    start_date = f"{season}-02-01"  # Spring training starts
    end_date = f"{season}-11-30"    # World Series ends
    
    url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        'sportId': 1,
        'teamId': DODGERS_TEAM_ID,
        'startDate': start_date,
        'endDate': end_date,
        'hydrate': 'team,linescore'
    }
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for date_entry in data.get('dates', []):
            for game in date_entry.get('games', []):
                game_data = parse_game(game)
                if game_data:
                    games.append(game_data)
        
        if not games:
            logging.error("No games found in schedule")
            return pd.DataFrame()
        
        df = pd.DataFrame(games)
        logging.info(f"Fetched {len(df)} games from schedule")
        return df
        
    except Exception as e:
        logging.error(f"Failed to fetch schedule: {e}")
        raise


def parse_game(game: dict) -> dict:
    """Parse a single game from MLB API response"""
    try:
        # Skip spring training and exhibition games
        game_type = game.get('gameType')
        if game_type in ['S', 'E']:
            return None
        
        teams = game.get('teams', {})
        status = game.get('status', {})
        game_date_str = game.get('gameDate')
        
        # Parse game date/time
        game_date_utc = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
        
        # Convert to Pacific Time
        pacific = pytz.timezone('US/Pacific')
        game_date_pacific = game_date_utc.astimezone(pacific)
        
        # Determine if Dodgers are home or away
        is_home = teams.get('home', {}).get('team', {}).get('id') == DODGERS_TEAM_ID
        
        if is_home:
            opponent_name = teams.get('away', {}).get('team', {}).get('name', 'Unknown')
            dodgers_score = teams.get('home', {}).get('score')
            opponent_score = teams.get('away', {}).get('score')
        else:
            opponent_name = teams.get('home', {}).get('team', {}).get('name', 'Unknown')
            dodgers_score = teams.get('away', {}).get('score')
            opponent_score = teams.get('home', {}).get('score')
        
        # Determine result
        game_state = status.get('detailedState', '')
        result = None
        game_start = None
        
        if game_state in ['Final', 'Completed']:
            # Completed game
            if dodgers_score is not None and opponent_score is not None:
                result = 'win' if dodgers_score > opponent_score else 'loss'
                game_start = f"{dodgers_score}-{opponent_score}"  # Show score for completed games
        elif game_state in ['Scheduled', 'Pre-Game']:
            # Upcoming game
            result = '--'
            game_start = game_date_pacific.strftime('%-I:%M %p')  # Show time for upcoming games
        elif game_state in ['In Progress', 'Delayed']:
            # Game in progress
            result = 'in progress'
            game_start = 'Live'
        else:
            # Postponed, cancelled, etc.
            result = '--'
            game_start = game_state
        
        return {
            'game_pk': game.get('gamePk'),
            'date': game_date_pacific.strftime('%b %-d'),
            'date_full': game_date_pacific.strftime('%Y-%m-%d'),
            'opp_name': opponent_name,
            'home_away': 'home' if is_home else 'away',
            'result': result,
            'game_start': game_start,
            'status': game_state,
            'is_final': game_state in ['Final', 'Completed']
        }
        
    except Exception as e:
        logging.warning(f"Failed to parse game: {e}")
        return None


def build_schedule_tables(df: pd.DataFrame) -> pd.DataFrame:
    """Build last 10 and next 10 game tables"""
    # Split into completed and upcoming
    completed = df[df['is_final'] == True].copy()
    upcoming = df[df['is_final'] == False].copy()
    
    # Last 10 games
    last_ten = completed.tail(10).copy()
    last_ten['placement'] = 'last'
    
    # Next 10 games
    next_ten = upcoming.head(10).copy()
    next_ten['placement'] = 'next'
    
    # Combine
    schedule = pd.concat([last_ten, next_ten], ignore_index=True)
    
    # Keep only needed columns
    schedule = schedule[['date', 'opp_name', 'home_away', 'result', 'placement', 'game_start']]
    
    logging.info(f"Built schedule table: {len(last_ten)} past games, {len(next_ten)} upcoming games")
    return schedule


def save_to_s3(df: pd.DataFrame, base_path: str, bucket: str, formats: list):
    """Save DataFrame to S3 in multiple formats"""
    s3 = get_s3_resource()
    
    for fmt in formats:
        try:
            buffer = BytesIO()
            if fmt == "csv":
                df.to_csv(buffer, index=False)
                content_type = "text/csv"
            elif fmt == "json":
                df.to_json(buffer, indent=4, orient="records", lines=False)
                content_type = "application/json"
            
            buffer.seek(0)
            s3.Bucket(bucket).put_object(
                Key=f"{base_path}.{fmt}",
                Body=buffer,
                ContentType=content_type
            )
            logging.info(f"Uploaded {fmt} to {bucket}/{base_path}.{fmt}")
        except Exception as e:
            logging.error(f"Failed to upload {fmt} to S3: {e}")


def save_locally(df: pd.DataFrame, base_path: str, formats: list):
    """Save DataFrame locally"""
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    
    for fmt in formats:
        file_path = f"{base_path}.{fmt}"
        if fmt == "csv":
            df.to_csv(file_path, index=False)
        elif fmt == "json":
            df.to_json(file_path, indent=4, orient="records", lines=False)
        logging.info(f"Saved locally: {file_path}")


def main():
    """Main execution"""
    season = datetime.now().year
    
    logging.info(f"Fetching Dodgers schedule for {season} from MLB Stats API")
    
    # Fetch schedule
    df = fetch_schedule_from_mlb_api(season)
    
    if df.empty:
        logging.error("No schedule data retrieved")
        return
    
    # Build last 10 / next 10 tables
    schedule = build_schedule_tables(df)
    
    # Save locally
    save_locally(schedule, "data/standings/dodgers_schedule", ["csv", "json"])
    
    # Upload to S3
    save_to_s3(schedule, "dodgers/data/standings/dodgers_schedule", BUCKET, ["csv", "json"])
    
    logging.info("Schedule processing complete!")
    
    # Print summary
    last_count = len(schedule[schedule['placement'] == 'last'])
    next_count = len(schedule[schedule['placement'] == 'next'])
    print(f"\nSchedule summary:")
    print(f"  Last {last_count} games included")
    print(f"  Next {next_count} games included")


if __name__ == "__main__":
    main()
