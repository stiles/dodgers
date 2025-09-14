import json
import requests
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

def analyze_pitches(file_path, thrown_by_file_path=None):
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
    
    # --- Optional: Pitching-side analysis (balls called in zone against Dodgers pitchers) ---
    pitching_summary = None
    pitching_last_game = None
    pitching_worst_calls_list = []
    if thrown_by_file_path:
        try:
            with open(thrown_by_file_path, 'r') as f:
                pitches_by = json.load(f)
            if pitches_by:
                df_by = pd.DataFrame(pitches_by)
                df_by['game_date'] = pd.to_datetime(df_by['game_date'])
                df_by['dist_from_sz_edge_inches'] = pd.to_numeric(df_by['dist_from_sz_edge_inches'], errors='coerce')

                # Bad calls for pitching: balls called inside the zone
                df_called_balls = df_by[df_by['pitch_call'] == 'ball'].copy()
                df_bad_pitch_calls = df_called_balls[df_called_balls['pitch_in_zone']].copy()

                season_total_balls = len(df_called_balls)
                season_bad_balls = len(df_bad_pitch_calls)
                season_correct_balls = season_total_balls - season_bad_balls
                season_correct_pct_balls = (season_correct_balls / season_total_balls * 100) if season_total_balls > 0 else 0
                season_incorrect_pct_balls = 100 - season_correct_pct_balls

                # Last game summary (by game date)
                most_recent_date_by = df_by['game_date'].max()
                df_game_by = df_by[df_by['game_date'] == most_recent_date_by]
                game_called_balls = df_game_by[df_game_by['pitch_call'] == 'ball']
                game_bad_balls = game_called_balls[game_called_balls['pitch_in_zone']]
                game_total_balls = len(game_called_balls)
                game_bad_balls_count = len(game_bad_balls)
                game_correct_balls = game_total_balls - game_bad_balls_count
                game_correct_pct_balls = (game_correct_balls / game_total_balls * 100) if game_total_balls > 0 else 0
                game_incorrect_pct_balls = 100 - game_correct_pct_balls

                # Worst calls (how off): magnitude inside zone
                df_rankable_by = df_bad_pitch_calls.dropna(subset=['dist_from_sz_edge_inches']).copy()
                df_rankable_by['inside_inches'] = df_rankable_by['dist_from_sz_edge_inches'].abs()
                df_worst_by = df_rankable_by.sort_values(by='inside_inches', ascending=False).head(4)
                pitching_worst_calls_list = [
                    {
                        "distance_inches": row['inside_inches'],
                        "batter": row['batter'],
                        "pitcher": row['pitcher'],
                        "pitch_type": row['pitch_name'],
                        "velocity_mph": row['pitch_velocity'],
                        "date": row['game_date'].strftime('%Y-%m-%d'),
                        "date_formatted": row['game_date'].strftime('%B %-d, %Y'),
                        "video_link": f"https://baseballsavant.mlb.com/sporty-videos?playId={row['pitch_id']}"
                    }
                    for _, row in df_worst_by.iterrows()
                ]

                pitching_summary = {
                    "correct_balls_pct": season_correct_pct_balls,
                    "incorrect_balls_pct": season_incorrect_pct_balls,
                    "total_called_balls": season_total_balls,
                    "bad_calls_count": season_bad_balls
                }
                pitching_last_game = {
                    "date": most_recent_date_by.strftime('%B %-d, %Y'),
                    "correct_balls_pct": game_correct_balls and game_correct_pct_balls or 0,
                    "incorrect_balls_pct": game_incorrect_pct_balls,
                    "total_called_balls": game_total_balls,
                    "bad_calls_count": game_bad_balls_count
                }
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    # --- Helper: Fetch Home Plate Umpire for the last game ---
    def get_home_plate_umpire(game_pk: int):
        try:
            url = f"https://statsapi.mlb.com/api/v1.1/game/{int(game_pk)}/feed/live"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
            officials = (
                payload
                .get("liveData", {})
                .get("boxscore", {})
                .get("officials", [])
            )
            for off in officials:
                if str(off.get("officialType", "")).lower() == "home plate":
                    official = off.get("official", {})
                    return {
                        "id": official.get("id"),
                        "name": official.get("fullName"),
                    }
        except Exception:
            pass
        return None

    # Determine the gamePk for the most recent game in the dataset
    recent_game_pk = None
    try:
        # Use mode or first unique pk on the most recent date
        game_pks = df_game.get("game_pk")
        if game_pks is not None and not game_pks.empty:
            recent_game_pk = int(pd.Series(game_pks).mode().iloc[0])
    except Exception:
        recent_game_pk = None

    home_plate_umpire = get_home_plate_umpire(recent_game_pk) if recent_game_pk is not None else None

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
            "bad_calls_count": game_bad_calls_count,
            **({"home_plate_umpire": home_plate_umpire.get("name") if home_plate_umpire else None} ),
        },
        "worst_calls_of_season": worst_calls_list
    }

    if pitching_summary is not None and pitching_last_game is not None:
        summary_data["pitching_season_summary"] = pitching_summary
        summary_data["pitching_last_game_summary"] = pitching_last_game
        summary_data["pitching_worst_calls_of_season"] = pitching_worst_calls_list

    # --- Save and Upload ---
    os.makedirs(os.path.dirname(LOCAL_JSON_PATH), exist_ok=True)
    with open(LOCAL_JSON_PATH, 'w') as f:
        json.dump(summary_data, f, indent=4)
    print(f"Summary saved locally to {LOCAL_JSON_PATH}")

    upload_to_s3(LOCAL_JSON_PATH)

if __name__ == "__main__":
    year = pd.to_datetime("now").strftime("%Y")
    analyze_pitches(f'data/pitches/dodgers_pitches_{year}.json', thrown_by_file_path=f'data/pitches/dodgers_pitches_thrown_{year}.json') 