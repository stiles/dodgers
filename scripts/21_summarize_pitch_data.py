import json
import pandas as pd
import os
import boto3
from botocore.exceptions import NoCredentialsError

# === Configuration ===
LOCAL_JSON_PATH = "data/summary/umpire_summary.json"
S3_BUCKET = "stilesdata.com"
S3_KEY = "dodgers/data/summary/umpire_summary.json"

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

def analyze_pitches(file_path):
    """
    Analyzes pitch data and saves a JSON summary locally and to S3.
    """
    try:
        with open(file_path, 'r') as f:
            pitches = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading pitch data file: {e}")
        return

    if not pitches:
        print("No pitch data available.")
        return

    df = pd.DataFrame(pitches)
    df['game_date'] = pd.to_datetime(df['game_date'])
    df['dist_from_sz_edge_inches'] = pd.to_numeric(df['dist_from_sz_edge_inches'], errors='coerce')

    # --- Calculations ---
    df_called_strikes = df[df['pitch_call'] == 'called_strike'].copy()
    df_bad_calls = df_called_strikes[~df_called_strikes['pitch_in_zone']].copy()
    
    # Season Summary
    season_total_strikes = len(df_called_strikes)
    season_bad_calls = len(df_bad_calls)
    season_correct_calls = season_total_strikes - season_bad_calls
    season_correct_pct = (season_correct_calls / season_total_strikes * 100) if season_total_strikes > 0 else 0
    season_incorrect_pct = 100 - season_correct_pct

    # Last Game Summary
    most_recent_date = df['game_date'].max()
    df_game = df[df['game_date'] == most_recent_date]
    game_called_strikes = df_game[df_game['pitch_call'] == 'called_strike']
    game_bad_calls = game_called_strikes[~game_called_strikes['pitch_in_zone']]
    game_total_strikes = len(game_called_strikes)
    game_bad_calls_count = len(game_bad_calls)
    game_correct_calls = game_total_strikes - game_bad_calls_count
    game_correct_pct = (game_correct_calls / game_total_strikes * 100) if game_total_strikes > 0 else 0
    game_incorrect_pct = 100 - game_correct_pct

    # Worst Calls
    df_rankable = df_bad_calls.dropna(subset=['dist_from_sz_edge_inches'])
    df_worst = df_rankable.sort_values(by='dist_from_sz_edge_inches', ascending=False).head(4)
    worst_calls_list = [
        {
            "distance_inches": row['dist_from_sz_edge_inches'],
            "batter": row['batter'],
            "pitcher": row['pitcher'],
            "pitch_type": row['pitch_name'],
            "velocity_mph": row['pitch_velocity'],
            "date": row['game_date'].strftime('%Y-%m-%d'),
            "date_formatted": row['game_date'].strftime('%B %-d, %Y'),
            "video_link": f"https://baseballsavant.mlb.com/sporty-videos?playId={row['pitch_id']}"
        }
        for _, row in df_worst.iterrows()
    ]
    
    # --- Create Summary Object ---
    summary_data = {
        "season_summary": {
            "correct_strikes_pct": season_correct_pct,
            "incorrect_strikes_pct": season_incorrect_pct,
            "total_called_strikes": season_total_strikes,
            "bad_calls_count": season_bad_calls
        },
        "last_game_summary": {
            "date": most_recent_date.strftime("%B %-d, %Y"),
            "correct_strikes_pct": game_correct_pct,
            "incorrect_strikes_pct": game_incorrect_pct,
            "total_called_strikes": game_total_strikes,
            "bad_calls_count": game_bad_calls_count
        },
        "worst_calls_of_season": worst_calls_list
    }

    # --- Save and Upload ---
    os.makedirs(os.path.dirname(LOCAL_JSON_PATH), exist_ok=True)
    with open(LOCAL_JSON_PATH, 'w') as f:
        json.dump(summary_data, f, indent=4)
    print(f"Summary saved locally to {LOCAL_JSON_PATH}")

    upload_to_s3(LOCAL_JSON_PATH)

if __name__ == "__main__":
    analyze_pitches('data/pitches/dodgers_pitches_2025.json') 