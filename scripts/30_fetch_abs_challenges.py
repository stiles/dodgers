#!/usr/bin/env python
"""
Fetch ABS (Automated Ball-Strike) challenge data from MLB StatsAPI.

This script fetches challenge information from the StatsAPI v1.1 live feed,
which contains reviewDetails for ABS challenges. It tracks challenges by
batters, pitchers, and catchers for both the Dodgers and their opponents.
"""

import json
import os
import requests
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError
from datetime import datetime, timedelta

# === Configuration ===
OUTPUT_DIR = "data/summary"
LOCAL_JSON_PATH = os.path.join(OUTPUT_DIR, "abs_challenges.json")
S3_BUCKET = "stilesdata.com"
S3_KEY = "dodgers/data/summary/abs_challenges.json"
DODGERS_TEAM_ID = 119

# === AWS Session Setup ===
is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
if is_github_actions:
    aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    aws_region = "us-west-1"
    session = boto3.Session(
        aws_access_key_id=aws_key_id,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
else:
    session = boto3.Session(profile_name="haekeo", region_name="us-west-1")
s3 = session.resource('s3')


def upload_to_s3(file_path):
    """Uploads a file to the configured S3 bucket."""
    if not S3_BUCKET:
        print("S3 upload skipped: Bucket name is not configured.")
        return
    
    try:
        s3.Bucket(S3_BUCKET).upload_file(file_path, S3_KEY)
        print(f"Successfully uploaded {os.path.basename(file_path)} to {S3_BUCKET}/{S3_KEY}")
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found for S3 upload.")
    except NoCredentialsError:
        print("Error: AWS credentials not found. S3 upload failed.")
    except Exception as e:
        print(f"An error occurred during S3 upload: {e}")


def get_dodgers_games(start_date, end_date):
    """
    Fetch Dodgers game IDs for the date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        List of game_pk integers
    """
    url = f"https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "teamId": DODGERS_TEAM_ID,
        "startDate": start_date,
        "endDate": end_date
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        game_pks = []
        for date_obj in data.get("dates", []):
            for game in date_obj.get("games", []):
                # Only include completed games
                if game["status"]["abstractGameState"] == "Final":
                    game_pks.append(game["gamePk"])
        
        return game_pks
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return []


def fetch_game_challenges(game_pk):
    """
    Fetch ABS challenge data from a single game's live feed.
    
    Args:
        game_pk: MLB game ID
        
    Returns:
        List of challenge dicts or empty list if error/no challenges
    """
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        # Check if game has ABS challenges enabled
        abs_info = data.get("gameData", {}).get("absChallenges", {})
        if not abs_info.get("hasChallenges"):
            return []
        
        # Get game date and teams
        game_date = data.get("gameData", {}).get("datetime", {}).get("officialDate")
        teams = data.get("gameData", {}).get("teams", {})
        home_team_id = teams.get("home", {}).get("id")
        away_team_id = teams.get("away", {}).get("id")
        
        is_dodgers_home = home_team_id == DODGERS_TEAM_ID
        is_dodgers_away = away_team_id == DODGERS_TEAM_ID
        
        # Parse challenges from play events
        challenges = []
        all_plays = data.get("liveData", {}).get("plays", {}).get("allPlays", [])
        
        for play in all_plays:
            inning = play.get("about", {}).get("inning")
            half_inning = play.get("about", {}).get("halfInning")
            
            for event in play.get("playEvents", []):
                review = event.get("reviewDetails")
                if not review:
                    continue
                
                # Only process ABS challenges (reviewType "MJ")
                if review.get("reviewType") != "MJ":
                    continue
                
                # Get challenge info
                challenger = review.get("player", {})
                challenger_name = challenger.get("fullName", "Unknown")
                challenger_id = challenger.get("id")
                
                challenge_team_id = review.get("challengeTeamId")
                is_overturned = review.get("isOverturned", False)
                
                # Get pitch details
                pitch_data = event.get("pitchData", {})
                call = event.get("details", {}).get("call", {}).get("description", "Unknown")
                
                # Get matchup info from the play level
                matchup = play.get("matchup", {})
                batter_name = matchup.get("batter", {}).get("fullName", "Unknown")
                batter_id = matchup.get("batter", {}).get("id")
                pitcher_name = matchup.get("pitcher", {}).get("fullName", "Unknown")
                pitcher_id = matchup.get("pitcher", {}).get("id")
                
                # Determine role: batter, pitcher, or catcher
                if challenger_id == batter_id:
                    role = "batting"
                elif challenger_id == pitcher_id:
                    role = "pitching"
                else:
                    role = "catching"
                
                # Determine team (dodgers or opponents)
                if challenge_team_id == DODGERS_TEAM_ID:
                    team = "dodgers"
                else:
                    team = "opponents"
                
                # Get result description from play result
                result_desc = play.get("result", {}).get("description", "")
                
                challenges.append({
                    "game_pk": game_pk,
                    "date": game_date,
                    "inning": inning,
                    "half_inning": half_inning,
                    "challenger": challenger_name,
                    "challenger_id": challenger_id,
                    "role": role,
                    "team": team,
                    "outcome": "overturned" if is_overturned else "confirmed",
                    "call": call,
                    "batter": batter_name,
                    "pitcher": pitcher_name,
                    "result_desc": result_desc,
                })
        
        return challenges
        
    except Exception as e:
        print(f"Error fetching game {game_pk}: {e}")
        return []


def process_challenges(challenges):
    """
    Process raw challenges into aggregated stats and a challenge log.
    
    Args:
        challenges: List of challenge dicts
        
    Returns:
        Dict with dodgers/opponents stats and challenge_log
    """
    if not challenges:
        return {
            "dodgers": {
                "batting": {"total": 0, "successful": 0, "failed": 0},
                "pitching": {"total": 0, "successful": 0, "failed": 0},
                "catching": {"total": 0, "successful": 0, "failed": 0},
            },
            "opponents": {
                "batting": {"total": 0, "successful": 0, "failed": 0},
                "pitching": {"total": 0, "successful": 0, "failed": 0},
                "catching": {"total": 0, "successful": 0, "failed": 0},
            },
            "challenge_log": []
        }
    
    # Convert to DataFrame for easier processing
    df = pd.DataFrame(challenges)
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by date descending
    df = df.sort_values('date', ascending=False)
    
    # Create challenge log (limit to 20 most recent)
    challenge_log = []
    for _, row in df.head(20).iterrows():
        challenge_log.append({
            "date": row['date'].strftime('%Y-%m-%d'),
            "date_formatted": row['date'].strftime('%B %-d, %Y'),
            "challenger": row['challenger'],
            "role": row['role'],
            "team": row['team'],
            "outcome": row['outcome'],
            "result_desc": row['result_desc'],
            "batter": row['batter'],
            "pitcher": row['pitcher'],
            "game_pk": int(row['game_pk']),
        })
    
    # Aggregate stats
    summary = {
        "dodgers": {
            "batting": {"total": 0, "successful": 0, "failed": 0},
            "pitching": {"total": 0, "successful": 0, "failed": 0},
            "catching": {"total": 0, "successful": 0, "failed": 0},
        },
        "opponents": {
            "batting": {"total": 0, "successful": 0, "failed": 0},
            "pitching": {"total": 0, "successful": 0, "failed": 0},
            "catching": {"total": 0, "successful": 0, "failed": 0},
        },
        "challenge_log": challenge_log
    }
    
    for _, row in df.iterrows():
        bucket = summary[row['team']][row['role']]
        bucket['total'] += 1
        if row['outcome'] == 'overturned':
            bucket['successful'] += 1
        else:
            bucket['failed'] += 1
    
    return summary


def main():
    """Main execution function."""
    # Get current year
    year = datetime.now().year
    
    # Fetch games from season start (March 1) through today
    start_date = f"{year}-03-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Fetching Dodgers games from {start_date} to {end_date}...")
    game_pks = get_dodgers_games(start_date, end_date)
    print(f"Found {len(game_pks)} completed games")
    
    # Fetch challenges from each game
    all_challenges = []
    for game_pk in game_pks:
        print(f"Processing game {game_pk}...", end=" ")
        challenges = fetch_game_challenges(game_pk)
        if challenges:
            print(f"Found {len(challenges)} challenge(s)")
            all_challenges.extend(challenges)
        else:
            print("No challenges")
    
    print(f"\nTotal challenges found: {len(all_challenges)}")
    
    # Process and aggregate
    summary = process_challenges(all_challenges)
    
    # Save locally
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(LOCAL_JSON_PATH, 'w') as f:
        json.dump(summary, f, indent=4)
    print(f"Summary saved to {LOCAL_JSON_PATH}")
    
    # Upload to S3
    upload_to_s3(LOCAL_JSON_PATH)
    
    # Print summary
    print("\n" + "="*50)
    print("ABS Challenge Summary")
    print("="*50)
    dodgers = summary['dodgers']
    opponents = summary['opponents']
    
    dodgers_total = sum(dodgers[r]['total'] for r in ['batting', 'pitching', 'catching'])
    opponents_total = sum(opponents[r]['total'] for r in ['batting', 'pitching', 'catching'])
    
    print(f"\nDodgers: {dodgers_total} total challenges")
    for role in ['batting', 'pitching', 'catching']:
        stats = dodgers[role]
        if stats['total'] > 0:
            print(f"  {role.capitalize()}: {stats['total']} ({stats['successful']}W-{stats['failed']}L)")
    
    print(f"\nOpponents: {opponents_total} total challenges")
    for role in ['batting', 'pitching', 'catching']:
        stats = opponents[role]
        if stats['total'] > 0:
            print(f"  {role.capitalize()}: {stats['total']} ({stats['successful']}W-{stats['failed']}L)")


if __name__ == "__main__":
    main()
