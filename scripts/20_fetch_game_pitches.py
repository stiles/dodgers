import requests
import pandas as pd
from datetime import datetime, timedelta
from tqdm import tqdm
import math
import os
import boto3

# === Constants ===
SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
GAMEFEED_URL = "https://baseballsavant.mlb.com/gf"
BALL_RADIUS_FEET = 1.45 / 12
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# === Configuration ===
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "data", "pitches")
S3_BUCKET = "stilesdata.com"
current_year_for_paths = datetime.now().year
S3_KEY_CSV = f"dodgers/data/pitches/dodgers_pitches_{current_year_for_paths}.csv"
S3_KEY_JSON = f"dodgers/data/pitches/dodgers_pitches_{current_year_for_paths}.json"

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

# === Date Range for the current regular season ===
current_year = datetime.now().year
current_month = datetime.now().month
current_day = datetime.now().day
start_date = datetime(current_year, 3, 20)
end_date = datetime(current_year, current_month, current_day)

# === Helpers ===
def daterange(start, end):
    while start <= end:
        yield start
        start += timedelta(days=1)

def _get_team_name(game, team_type):
    """Safely retrieves a team's name from a game dictionary."""
    try:
        return game["teams"][team_type]["team"]["name"]
    except KeyError:
        return None

def get_dodgers_game_ids(date_str):
    params = {"sportId": 1, "date": date_str}
    try:
        resp = requests.get(SCHEDULE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch schedule for {date_str}: {e}")
        return []

    dates = data.get("dates", [])
    if not dates:
        return []
    
    games = dates[0].get("games", [])
    dodgers_games = []
    for g in games:
        home_team = _get_team_name(g, "home")
        away_team = _get_team_name(g, "away")
        game_date = g.get("officialDate")

        if home_team == "Los Angeles Dodgers":
            dodgers_games.append({"gamePk": g.get("gamePk"), "team_side": "home_batters", "game_date": game_date})
        elif away_team == "Los Angeles Dodgers":
            dodgers_games.append({"gamePk": g.get("gamePk"), "team_side": "away_batters", "game_date": game_date})
    
    return dodgers_games

def fetch_game_pitches(game_pk):
    resp = requests.get(GAMEFEED_URL, params={"game_pk": game_pk})
    resp.raise_for_status()
    return resp.json()

def load_existing_json(url: str) -> pd.DataFrame:
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200 and resp.content:
            return pd.DataFrame(resp.json())
    except Exception:
        pass
    return pd.DataFrame()

def analyze_pitches(game_info, batting_side_override: str = None, team_role: str = None):
    game_pk = game_info["gamePk"]
    team_side = batting_side_override if batting_side_override else game_info["team_side"]
    game_date = game_info.get("game_date")
    try:
        data = fetch_game_pitches(game_pk)
    except Exception as e:
        print(f"⚠️ Failed to fetch game {game_pk}: {e}")
        return []

    rows = []
    # Strike zone horizontal boundaries (in feet)
    sz_right = 0.708 
    sz_left = -0.708

    for batter_id, pitches in data.get(team_side, {}).items():
        for pitch in pitches:
            px = pitch.get("px")
            pz = pitch.get("pz")
            sz_bot = pitch.get("sz_bot")
            sz_top = pitch.get("sz_top")

            dist_from_sz_center_feet = None
            dist_from_sz_edge_feet = None
            dist_from_sz_center_inches = None
            dist_from_sz_edge_inches = None
            if all(v is not None for v in [px, pz, sz_bot, sz_top]):
                closest_x = max(sz_left, min(sz_right, px))
                closest_z = max(sz_bot, min(sz_top, pz))
                dist_from_sz_center_feet = math.sqrt((px - closest_x)**2 + (pz - closest_z)**2)
                dist_from_sz_edge_feet = dist_from_sz_center_feet - BALL_RADIUS_FEET
                dist_from_sz_center_inches = dist_from_sz_center_feet * 12
                dist_from_sz_edge_inches = dist_from_sz_edge_feet * 12
            
            in_strike_zone = dist_from_sz_center_feet is not None and dist_from_sz_center_feet <= BALL_RADIUS_FEET
            
            rows.append({
                "game_pk": game_pk,
                "game_date": game_date,
                "pitch_id": pitch.get("play_id"),
                "inning": pitch.get("inning"),
                "ab_number": pitch.get("ab_number"),
                "pitch_number": pitch.get("pitch_number"),
                "batter": pitch.get("batter_name"),
                "pitcher": pitch.get("pitcher_name"),
                "pitch_name": pitch.get("pitch_name"),
                "pitch_velocity": pitch.get("start_speed"),
                "pitch_call": pitch.get("pitch_call"),
                "pitch_in_zone": in_strike_zone,
                "at_bat_eventual_result": pitch.get("result"),
                "at_bat_eventual_desc": pitch.get("des"),
                "dist_from_sz_center_inches": dist_from_sz_center_inches,
                "dist_from_sz_edge_inches": dist_from_sz_edge_inches,
                "zone": pitch.get("zone"),
                "px": px,
                "pz": pz,
                "sz_bot": sz_bot,
                "sz_top": sz_top,
                "team_role": team_role or "thrown_to_dodgers",
            })
    rows.sort(key=lambda p: (p.get('inning', 0), p.get('ab_number', 0), p.get('pitch_number', 0)))
    return rows

# === Main ===
all_dodgers_games = []
total_days = (end_date - start_date).days + 1
for day in tqdm(daterange(start_date, end_date), total=total_days, desc="Fetching game IDs"):
    date_str = day.strftime("%Y-%m-%d")
    games = get_dodgers_game_ids(date_str)
    all_dodgers_games.extend(games)

print(f"\nTotal Dodgers games found: {len(all_dodgers_games)}")

all_pitches = []
all_pitches_thrown_by_dodgers = []

# Load existing datasets from public URLs to support incremental updates
public_to_url = f"https://stilesdata.com/{S3_KEY_JSON}"
public_by_url = f"https://stilesdata.com/dodgers/data/pitches/dodgers_pitches_thrown_{current_year_for_paths}.json"
existing_to_df = load_existing_json(public_to_url)
existing_by_df = load_existing_json(public_by_url)
processed_gamepks_to = set(existing_to_df['game_pk'].unique()) if not existing_to_df.empty and 'game_pk' in existing_to_df.columns else set()
processed_gamepks_by = set(existing_by_df['game_pk'].unique()) if not existing_by_df.empty and 'game_pk' in existing_by_df.columns else set()

for game_info in tqdm(all_dodgers_games, desc="Analyzing games"):
    gpk = game_info.get('gamePk')

    # Pitches thrown to Dodgers batters (skip if already processed)
    if gpk not in processed_gamepks_to:
        all_pitches.extend(analyze_pitches(game_info, team_role="thrown_to_dodgers"))

    # Pitches thrown BY Dodgers pitchers (skip if already processed)
    if gpk not in processed_gamepks_by:
        ts = game_info.get("team_side")
        other_side = "away_batters" if ts == "home_batters" else "home_batters"
        all_pitches_thrown_by_dodgers.extend(
            analyze_pitches(game_info, batting_side_override=other_side, team_role="thrown_by_dodgers")
        )

# === Results ===
df = pd.DataFrame(all_pitches)
df_by_dodgers = pd.DataFrame(all_pitches_thrown_by_dodgers)

# Append to existing and dedupe
def combine_and_dedupe(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    if existing is None or existing.empty:
        combined = new.copy()
    elif new is None or new.empty:
        combined = existing.copy()
    else:
        combined = pd.concat([existing, new], ignore_index=True)
    if combined is None or combined.empty:
        return pd.DataFrame()
    subset_cols = [c for c in ['game_pk', 'ab_number', 'pitch_number'] if c in combined.columns]
    if subset_cols:
        combined = combined.drop_duplicates(subset=subset_cols)
    else:
        if 'pitch_id' in combined.columns:
            combined = combined.drop_duplicates(subset=['pitch_id'])
        else:
            combined = combined.drop_duplicates()
    return combined

df = combine_and_dedupe(existing_to_df, df)
df_by_dodgers = combine_and_dedupe(existing_by_df, df_by_dodgers)

# === Export the data ===
os.makedirs(OUTPUT_DIR, exist_ok=True)
csv_path = os.path.join(OUTPUT_DIR, f"dodgers_pitches_{current_year}.csv")
json_path = os.path.join(OUTPUT_DIR, f"dodgers_pitches_{current_year}.json")
csv_path_by = os.path.join(OUTPUT_DIR, f"dodgers_pitches_thrown_{current_year}.csv")
json_path_by = os.path.join(OUTPUT_DIR, f"dodgers_pitches_thrown_{current_year}.json")

df.to_csv(csv_path, index=False)
print(f"Pitch data saved locally to {csv_path}")
df.to_json(json_path, indent=4, orient="records")
print(f"Pitch data saved locally to {json_path}")

# Save pitches thrown by Dodgers
df_by_dodgers.to_csv(csv_path_by, index=False)
print(f"Pitch data (thrown by Dodgers) saved locally to {csv_path_by}")
df_by_dodgers.to_json(json_path_by, indent=4, orient="records")
print(f"Pitch data (thrown by Dodgers) saved locally to {json_path_by}")

# === Upload to S3 ===
try:
    s3.Bucket(S3_BUCKET).upload_file(csv_path, S3_KEY_CSV)
    print(f"Successfully uploaded {os.path.basename(csv_path)} to {S3_BUCKET}/{S3_KEY_CSV}")
    s3.Bucket(S3_BUCKET).upload_file(json_path, S3_KEY_JSON)
    print(f"Successfully uploaded {os.path.basename(json_path)} to {S3_BUCKET}/{S3_KEY_JSON}")

    # Upload thrown-by-Dodgers files
    s3_key_csv_by = f"dodgers/data/pitches/dodgers_pitches_thrown_{current_year_for_paths}.csv"
    s3_key_json_by = f"dodgers/data/pitches/dodgers_pitches_thrown_{current_year_for_paths}.json"
    s3.Bucket(S3_BUCKET).upload_file(csv_path_by, s3_key_csv_by)
    print(f"Successfully uploaded {os.path.basename(csv_path_by)} to {S3_BUCKET}/{s3_key_csv_by}")
    s3.Bucket(S3_BUCKET).upload_file(json_path_by, s3_key_json_by)
    print(f"Successfully uploaded {os.path.basename(json_path_by)} to {S3_BUCKET}/{s3_key_json_by}")
except Exception as e:
    print(f"An error occurred during S3 upload: {e}")