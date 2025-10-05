#!/usr/bin/env python
# coding: utf-8


"""
LA Dodgers toplines
This notebook extracts key statistics from the project's processed tables for display in a dashboard.
"""

import os
from typing import Union
import pandas as pd
import boto3
from io import BytesIO
import logging
from datetime import datetime, timezone, timedelta, date
import json
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Base directory calculation for file paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Get the update time
def get_pacific_time():
    utc_zone = timezone.utc
    utc_time = datetime.now(utc_zone)
    pacific_offset = timedelta(hours=-8)
    if utc_time.astimezone(timezone.utc).replace(tzinfo=None).month in {4, 5, 6, 7, 8, 9, 10}:
        pacific_offset = timedelta(hours=-7)
    pacific_zone = timezone(pacific_offset)
    pacific_time = utc_time.astimezone(pacific_zone)
    formatted_time = pacific_time.strftime("%B %-d, %Y, %-I:%M %p PT")
    return formatted_time

# Store the update time
update_time = get_pacific_time()

# Get the update date
def get_pacific_date():
    utc_zone = timezone.utc
    utc_time = datetime.now(utc_zone)
    pacific_offset = timedelta(hours=-8)
    if utc_time.astimezone(timezone.utc).replace(tzinfo=None).month in {4, 5, 6, 7, 8, 9, 10}:
        pacific_offset = timedelta(hours=-7)
    pacific_zone = timezone(pacific_offset)
    pacific_time = utc_time.astimezone(pacific_zone)
    formatted_date = pacific_time.strftime("%B %-d")
    return formatted_date

# Store the update date
update_date = get_pacific_date()

def read_parquet_s3(url, sort_by=None):
    """Read a Parquet file from the S3 URL.
    Only sort the dataframe if a sort column is provided.
    Batting doesn't have game dates because it's annual totals."""
    df = pd.read_parquet(url)
    if sort_by and sort_by in df.columns:
        df.sort_values(sort_by, ascending=False, inplace=True)
    return df

def to_ordinal(n):
    # Ensure n is an integer before performing modulo and dictionary lookup
    if isinstance(n, (int, float)) and not pd.isna(n):
        n_int = int(n)
        return str(n_int) + {1: "st", 2: "nd", 3: "rd"}.get(n_int % 10 if n_int % 100 not in (11, 12, 13) else 99, "th")
    return str(n) # Return as string if not a number or if NaN

def format_int_with_commas(value):
    """Format an integer-like value with thousands separators.
    Returns original value if it cannot be parsed as int."""
    try:
        return f"{int(value):,}"
    except Exception:
        return value

def parse_games_back(value):
    """Parse games-back values which may be '-', None, strings, floats."""
    if value in (None, '-', '—', ''):
        return 0
    try:
        num = float(value)
        # Coerce .0 to int for cleaner display
        return int(num) if num.is_integer() else num
    except Exception:
        return 0

def compute_games_up_back_from_live(live_df: pd.DataFrame, team_name: str) -> Union[int, float, None]:
    """Compute a positive 'games up/back' value from live standings for the given team.
    - If the team is in 1st, return the lead over the closest trailing team
    - Otherwise, return the team's own games_back
    Falls back to 0 when values are unavailable.
    """
    try:
        lad_row = live_df.query("team_name == @team_name").iloc[0]
        division = lad_row.get('division_name')
        division_df = live_df.query("division_name == @division").copy()
        if division_df.empty:
            return 0
        # Normalize GB to numeric
        division_df['__gb_num'] = division_df['games_back'].apply(parse_games_back)
        division_df['__rank_num'] = pd.to_numeric(division_df['division_rank'], errors='coerce')
        division_df = division_df.sort_values(['__rank_num', '__gb_num']).reset_index(drop=True)
        lad_rank = int(lad_row.get('division_rank')) if pd.notna(lad_row.get('division_rank')) else 99
        
        if lad_rank == 1:
            # Check if there are any teams tied for first (GB = 0)
            tied_teams = division_df[division_df['__gb_num'] == 0]
            if len(tied_teams) > 1:
                # Multiple teams tied for first = 0 games up/back
                return 0
            else:
                # Sole first place, find lead over 2nd place
                if len(division_df) >= 2:
                    second_place_gb = division_df.iloc[1]['__gb_num']
                    return int(second_place_gb) if float(second_place_gb).is_integer() else second_place_gb
                return 0
        else:
            gb = parse_games_back(lad_row.get('games_back'))
            return int(gb) if isinstance(gb, (int, float)) and float(gb).is_integer() else gb
    except Exception:
        return None

# URLs for data
standings_live_url = "https://stilesdata.com/dodgers/data/standings/all_teams_standings_metrics_2025.json"
standings_url = "https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.parquet"
batting_url = "https://stilesdata.com/dodgers/data/batting/dodgers_team_batting_1958_present.parquet"
pitching_url = 'https://stilesdata.com/dodgers/data/pitching/dodgers_pitching_totals_current.parquet'
# pitching_ranks_url = 'https://stilesdata.com/dodgers/data/pitching/dodgers_pitching_ranks_current.parquet' # Removed
# batting_ranks_url = 'https://stilesdata.com/dodgers/data/batting/dodgers_team_batting_ranks_1958_present.parquet' # Removed

mlb_teams = {
    "ARI": "Arizona Diamondbacks",
    "ATL": "Atlanta Braves",
    "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox",
    "CHC": "Chicago Cubs",
    "CHW": "Chicago White Sox",
    "CIN": "Cincinnati Reds",
    "CLE": "Cleveland Guardians",
    "COL": "Colorado Rockies",
    "DET": "Detroit Tigers",
    "HOU": "Houston Astros",
    "KCR": "Kansas City Royals",
    "LAA": "Los Angeles Angels",
    "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers",
    "MIN": "Minnesota Twins",
    "NYM": "New York Mets",
    "NYY": "New York Yankees",
    "ATH": "Athletics",
    "PHI": "Philadelphia Phillies",
    "PIT": "Pittsburgh Pirates",
    "SDP": "San Diego Padres",
    "SFG": "San Francisco Giants",
    "SEA": "Seattle Mariners",
    "STL": "St. Louis Cardinals",
    "TBR": "Tampa Bay Rays",
    "TEX": "Texas Rangers",
    "TOR": "Toronto Blue Jays",
    "WSN": "Washington Nationals"
}

# Load the data
now = pd.to_datetime("now")
year = now.strftime("%Y")  # current year
last_year = (now - pd.DateOffset(years=1)).strftime("%Y")  # subtract one year

# Load league ranks data from JSON
league_ranks_data = {}
ranks_file_path = os.path.join(base_dir, 'data', 'standings', f'dodgers_league_ranks_{year}.json')
try:
    with open(ranks_file_path, 'r') as f:
        league_ranks_data = json.load(f)
    logging.info(f"Successfully loaded league ranks from {ranks_file_path}")
except FileNotFoundError:
    logging.warning(f"League ranks file not found at {ranks_file_path}. Ranks will be 'N/A'.")
except json.JSONDecodeError:
    logging.error(f"Error decoding JSON from {ranks_file_path}. Ranks will be 'N/A'.")


# Standings
standings = read_parquet_s3(standings_url, sort_by='game_date').query(f"year == '{year}'")
standings['result'] = standings['result'].str.split('-wo', expand=True)[0]
standings['opp_name'] = standings['opp'].map(mlb_teams)
standings.loc[standings.result == "L", "result_clean"] = "loss"
standings.loc[standings.result == "W", "result_clean"] = "win"
standings_past = read_parquet_s3(standings_url, sort_by='game_date').query(f"year == '{last_year}'")
standings_now = standings.query("game_date == game_date.max()").copy()
# Prefer local _data standings file (same one the site tables use); fallback to remote
local_live_path = os.path.join(base_dir, '_data', 'standings', f'all_teams_standings_metrics_{year}.json')
try:
    if os.path.exists(local_live_path):
        with open(local_live_path, 'r') as f:
            import json
            data = json.load(f)
            # Handle new metadata structure
            if isinstance(data, dict) and 'teams' in data:
                standings_live = pd.DataFrame(data['teams'])
            else:
                standings_live = pd.DataFrame(data)
    else:
        response = requests.get(standings_live_url)
        data = response.json()
        # Handle new metadata structure
        if isinstance(data, dict) and 'teams' in data:
            standings_live = pd.DataFrame(data['teams'])
        else:
            standings_live = pd.DataFrame(data)
except Exception:
    response = requests.get(standings_live_url)
    data = response.json()
    # Handle new metadata structure
    if isinstance(data, dict) and 'teams' in data:
        standings_live = pd.DataFrame(data['teams'])
    else:
        standings_live = pd.DataFrame(data)
        
standings_live_lad = standings_live.query("team_name == 'Los Angeles Dodgers'")
print(standings_live_lad.iloc[0])

# Derive last game result from live standings (streak_type)
last_game_result_live = None
try:
    if not standings_live_lad.empty:
        streak_type_val = standings_live_lad.iloc[0].get('streak_type', None)
#if streak type is 'wins' then the most recent game was a win, else a loss
        if isinstance(streak_type_val, str):
            last_game_result_live = 'win' if streak_type_val.lower() == 'wins' else 'loss'
except Exception as _:
    last_game_result_live = None

game_number = standings_now['gm'].iloc[0]
standings_last = standings_past.query(f"gm == {game_number}").head(1).reset_index(drop=True).copy()
standings_last_season = standings_past.query(f"gm <= {game_number} and year=='{last_year}'").reset_index(drop=True).copy()
standings["rank_ordinal"] = standings["rank"].map(to_ordinal)
# Use live standings for division rank to match NL tables
try:
    live_division_rank = int(standings_live_lad.iloc[0].get('division_rank'))
    standings_division_rank = live_division_rank
    standings_division_rank_ordinal = to_ordinal(live_division_rank)
except Exception:
    standings_division_rank = standings['rank'].iloc[0]
    standings_division_rank_ordinal = standings['rank_ordinal'].iloc[0]

# Prefer live standings to compute a positive 'games up/back' value
games_up_back_value = compute_games_up_back_from_live(standings_live, 'Los Angeles Dodgers')
# If live data couldn't compute, fall back; otherwise keep live (including 0 for ties)
if games_up_back_value is None:
    games_back_raw = standings['gb'].iloc[0]
    try:
        games_up_back_value = int(float(games_back_raw))
    except Exception:
        try:
            games_up_back_value = int(games_back_raw)
        except Exception:
            games_up_back_value = 0

# Ensure non-negative display value (treat "games up" as positive)
if isinstance(games_up_back_value, (int, float)):
    val = abs(float(games_up_back_value))
    if abs(val) < 1e-9:
        val = 0
    games_up_back_value = int(val) if float(val).is_integer() else val
# Note: Removed problematic secondary fallback that was overriding correct 0 values for ties

# Batting
batting = read_parquet_s3(batting_url)
batting_past = batting.query(f"season != '{year}'").copy()
batting_now = batting.query(f"season == '{year}'").copy()
# batting_ranks = read_parquet_s3(batting_ranks_url, sort_by='game_date').query(f"season == '{year}'") # Removed

# Pitching
pitching = read_parquet_s3(pitching_url)
# pitching_ranks = read_parquet_s3(pitching_ranks_url) # Removed

def current_season_stats(standings_now, standings_past, pitching, standings_last):
    games = standings_now["gm"].iloc[0]
    wins = standings_now["wins"].iloc[0]
    wins_last = standings_last["wins"].iloc[0]
    losses = standings_now["losses"].iloc[0]
    losses_last = standings_last["losses"].iloc[0]
    record = standings_now["record"].iloc[0]
    record_last = standings_last["record"].iloc[0]
    win_pct = int(standings_now["win_pct"].iloc[0] * 100)
    win_pct_last = int(standings_last["win_pct"].iloc[0] * 100)
    win_pct_decade_thispoint = int(
        standings_past.query(f"gm == {games}").head(10)["win_pct"].mean().round(2) * 100
    )
    era = pitching['era'].iloc[0]
    era_rank = to_ordinal(league_ranks_data.get('pitching_earnedRunAverage', 'N/A'))
    strikeouts = pitching['so'].iloc[0]
    strikeouts_rank = to_ordinal(league_ranks_data.get('pitching_strikeouts', 'N/A'))
    walks = pitching['bb'].iloc[0]
    walks_rank = to_ordinal(league_ranks_data.get('pitching_walks', 'N/A'))
    home_runs_allowed = pitching['hr'].iloc[0]
    # home_runs_allowed_rank = league_ranks_data.get('pitching_homeRunsAllowed', 'N/A') # This stat is not in the current ranks JSON

    return games, wins, losses, record, win_pct, win_pct_decade_thispoint, era, era_rank, strikeouts, strikeouts_rank, walks, walks_rank, wins_last, losses_last, record_last, win_pct_last, home_runs_allowed

def run_differential(standings):
    runs = standings["r"].sum()
    runs_last = standings_last_season['r'].sum()
    runs_rank = to_ordinal(league_ranks_data.get('hitting_runs', 'N/A'))
    runs_against = standings["ra"].sum()
    runs_against_last = standings_last_season['ra'].sum()
    run_diff = runs - runs_against
    run_diff_last = runs_last - runs_against_last
    mean_attendance = standings.query('home_away == "home"')['attendance'].mean()
    home_games_count = len(standings.query('home_away == "home"'))
    formatted_mean_attendance = f"{mean_attendance:,.0f}"
    
    return runs, runs_last, runs_rank, runs_against, runs_against_last, run_diff, run_diff_last, mean_attendance, formatted_mean_attendance, home_games_count

def home_run_stats(batting_now, batting_past):
    games = int(batting_now["g"].iloc[0])
    home_runs = int(batting_now["hr"].sum())
    home_runs_rank = to_ordinal(league_ranks_data.get('hitting_homeRuns', 'N/A'))
    home_runs_game = round(home_runs / games, 2) if games > 0 else 0
    batting_past["hr_game"] = batting_past["hr"].astype(int) / batting_past["g"].astype(int).round(2)
    home_runs_game_last = batting_past.query(f'season == "{last_year}"')["hr_game"].iloc[0] if not batting_past.query(f'season == "{last_year}"').empty else 'N/A'
    games_decade = batting_past.head(10)["g"].astype(int).sum()
    home_runs_decade = batting_past.head(10)["hr"].astype(int).sum()
    home_runs_game_decade = round(home_runs_decade / games_decade, 2) if games_decade > 0 else 'N/A'
    return home_runs, home_runs_rank, home_runs_game, home_runs_game_last, home_runs_game_decade


def batting_and_stolen_base_stats(batting_now, batting_past, games):
    batting_average = batting_now["ba"].iloc[0]
    batting_average_decade = round(
        batting_past.head(10)["ba"].astype(float).mean(), 3
    ).astype(str).replace("0.", ".")
    on_base_pct = batting_now["obp"].iloc[0]
    on_base_pct_decade = round(
        batting_past.head(10)["obp"].astype(float).mean(), 3
    ).astype(str).replace("0.", ".")
    stolen_bases = int(batting_now["sb"].iloc[0])
    stolen_bases_rank = to_ordinal(league_ranks_data.get('hitting_stolenBases', 'N/A'))
    stolen_bases_game = round(stolen_bases / games, 2) if games > 0 else 0
    stolen_bases_last_rate = round(batting_past.head(1)["sb"].astype(int).sum() / batting_past.head(1)["g"].astype(int).sum(), 2) if not batting_past.head(1).empty and batting_past.head(1)["g"].astype(int).sum() > 0 else 'N/A'
    
    return batting_average, batting_average_decade, stolen_bases, stolen_bases_rank, stolen_bases_game, stolen_bases_last_rate, on_base_pct, on_base_pct_decade

def calculate_projected_wins(current_wins, games_played_so_far, total_season_games=162):
    """Calculates the projected number of wins for a full season based on current performance."""
    if games_played_so_far == 0:
        return 0  # Avoid division by zero and project 0 wins if no games played
    win_rate = current_wins / games_played_so_far
    projected_wins_val = round(win_rate * total_season_games)
    return projected_wins_val


def get_projection_final_mean(local_path: str, remote_url: str) -> int:
    """Return the rounded final projected wins from the projection timeseries JSON.
    Attempts local first, then remote. Returns None when unavailable or malformed.
    """
    data = None
    try:
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception:
        data = None

    if data is None:
        try:
            resp = requests.get(remote_url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            data = None

    try:
        if not data or "timeseries" not in data:
            return None
        ts = data.get("timeseries") or []
        if not ts:
            return None
        # Prefer game_number 162 if present; otherwise use the last element
        final_point = next((p for p in ts if int(p.get("game_number", 0)) == 162), ts[-1])
        mean_val = final_point.get("mean_projected_wins")
        if mean_val is None:
            return None
        return int(round(float(mean_val)))
    except Exception:
        return None

def get_live_last_game_summary():
    """Fetches live game data to find the last completed game and returns a summary fragment."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    
    # Fetch data for today and the last 5 days to find the last completed game
    today = date.today()
    five_days_ago = today - timedelta(days=5)
    
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=119&startDate={five_days_ago.strftime('%Y-%m-%d')}&endDate={today.strftime('%Y-%m-%d')}&hydrate=team,linescore"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Debug logging
        logging.info(f"Fetched schedule data for {five_days_ago} to {today}")
        logging.info(f"Found {len(data.get('dates', []))} date(s) in response")
        
        # Iterate backwards through dates and games to find the most recent final game
        for day in reversed(data.get('dates', [])):
            logging.info(f"Checking date: {day.get('date', 'Unknown')}")
            for game in reversed(day.get('games', [])):
                game_status = game['status']['abstractGameState']
                game_teams = game.get('teams', {})
                away_team = game_teams.get('away', {}).get('team', {}).get('abbreviation', 'Unknown')
                home_team = game_teams.get('home', {}).get('team', {}).get('abbreviation', 'Unknown')
                logging.info(f"Game: {away_team} @ {home_team}, Status: {game_status}")
                
                if game_status == 'Final':
                    teams = game['teams']
                    
                    # Check if LAD is either away or home team
                    away_abbr = teams.get('away', {}).get('team', {}).get('abbreviation')
                    home_abbr = teams.get('home', {}).get('team', {}).get('abbreviation')
                    logging.info(f"Processing final game: {away_abbr} @ {home_abbr}")
                    
                    if away_abbr == 'LAD':
                        home_away = "away"
                        result_clean = "win" if teams['away'].get('isWinner') else "loss"
                        r = teams['away'].get('score', 'N/A')
                        ra = teams['home'].get('score', 'N/A')
                        opp_name = teams.get('home', {}).get('team', {}).get('name', 'N/A')
                        
                        logging.info(f"Found LAD away game: {r}-{ra} {result_clean} vs {opp_name}")
                        return (
                            f"The last game was a <span class='highlight'>{r}-{ra}</span> "
                            f"{home_away} <span class='highlight'>{result_clean}</span>."
                        )
                    elif teams.get('home', {}).get('team', {}).get('abbreviation') == 'LAD':
                        home_away = "home"
                        result_clean = "win" if teams['home'].get('isWinner') else "loss"
                        r = teams['home'].get('score', 'N/A')
                        ra = teams['away'].get('score', 'N/A')
                        opp_name = teams.get('away', {}).get('team', {}).get('name', 'N/A')
                        
                        return (
                            f"The last game was a <span class='highlight'>{r}-{ra}</span> "
                            f"{home_away} <span class='highlight'>{result_clean}</span>."
                        )
        return "The last game's result is not yet available."
        
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        logging.error(f"Could not fetch or parse live last game data: {e}")
        return "Could not retrieve the result of the last game."


def get_live_last_game_result():
    """Returns 'win' or 'loss' for the most recent completed Dodgers game using MLB Stats API.
    Returns None if it cannot be determined."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    today = date.today()
    yesterday = today - timedelta(days=1)
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=119&startDate={yesterday.strftime('%Y-%m-%d')}&endDate={today.strftime('%Y-%m-%d')}&hydrate=team,linescore"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        for day in reversed(data.get('dates', [])):
            for game in reversed(day.get('games', [])):
                if game['status']['abstractGameState'] == 'Final':
                    teams = game['teams']
                    # Determine result for LAD
                    if teams.get('away', {}).get('team', {}).get('abbreviation') == 'LAD':
                        return 'win' if teams['away'].get('isWinner') else 'loss'
                    else:
                        return 'win' if teams['home'].get('isWinner') else 'loss'
        return None
    except (requests.exceptions.RequestException, KeyError, IndexError):
        return None

def get_next_game_info():
    """Fetches the next scheduled Dodgers game and returns formatted info."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    
    # Fetch upcoming games for the next 10 days
    today = date.today()
    ten_days_ahead = today + timedelta(days=10)
    
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=119&startDate={today.strftime('%Y-%m-%d')}&endDate={ten_days_ahead.strftime('%Y-%m-%d')}&hydrate=team,venue"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Find the next scheduled game
        for date_entry in data.get('dates', []):
            for game in date_entry.get('games', []):
                if game.get('status', {}).get('abstractGameState') == 'Preview':
                    # Parse game info
                    game_date_utc = datetime.fromisoformat(game['gameDate'].replace('Z', '+00:00'))
                    # Convert to ET
                    et_tz = timezone(timedelta(hours=-5))  # EST/EDT approximation
                    game_date_et = game_date_utc.astimezone(et_tz)
                    
                    # Format day and time
                    day_name = game_date_et.strftime('%A')  # Monday, Tuesday, etc.
                    time_str = game_date_et.strftime('%-I:%M p.m. ET')
                    
                    # Get venue info
                    venue_name = game.get('venue', {}).get('name', '')
                    
                    # Determine if home or away
                    home_team_id = game.get('teams', {}).get('home', {}).get('team', {}).get('id')
                    is_dodgers_home = home_team_id == 119
                    
                    location_text = f"at {venue_name}" if not is_dodgers_home else f"at {venue_name}"
                    
                    return f"The next game is {day_name} at {time_str} {location_text}"
        
        return None
        
    except Exception as e:
        logging.warning(f"Could not fetch next game info: {e}")
        return None

def generate_postseason_summary():
    """Generate a summary of the current postseason status"""
    try:
        # Try to load postseason series data
        postseason_file = "data/postseason/dodgers_postseason_series_2025.json"
        if os.path.exists(postseason_file):
            with open(postseason_file, 'r') as f:
                postseason_data = json.load(f)
            
            # Find current series status
            current_series = None
            completed_series = []
            
            for series in postseason_data:
                if series['status'] == 'in_progress':
                    current_series = series
                elif series['status'] == 'completed':
                    completed_series.append(series)
            
            if current_series:
                # Currently playing a series
                opponent = current_series['opponent']
                round_name = current_series['round']
                result = current_series['result']

                # Parse the series result to determine who's leading
                result = current_series['result']
                if 'LAD leads' in result:
                    series_status = result.replace('LAD leads', 'The Dodgers lead the series')
                elif 'LAD wins' in result:
                    series_status = result.replace('LAD wins', 'The Dodgers won the series')
                elif 'leads' in result and 'LAD' not in result:
                    # Handle case where opponent is leading
                    series_status = result.replace('leads', 'lead the series')
                else:
                    series_status = result
                
                return {
                    'competing': f"The team is competing in the {round_name} against the {opponent}.",
                    'series_status': series_status
                }
            
            elif completed_series:
                # All completed, check if they advanced or were eliminated
                last_series = completed_series[-1]
                if 'LAD wins' in last_series['result'] or 'LAD leads' in last_series['result']:
                    return {"text": f"The team advanced through the {last_series['round']} and continues in the postseason."}
                else:
                    return {"text": f"The team was eliminated in the {last_series['round']}."}
            else:
                return {"text": "The team is preparing for their postseason run."}
        else:
            return {"text": "The team won the National League West division and is off to the postseason!"}
            
    except Exception as e:
        logging.warning(f"Could not generate postseason summary: {e}")
        return {"text": "The team won the National League West division and is off to the postseason!"}

def generate_summary(
    update_date_str, standings_live_lad=None
):
    """Generates a narrative summary of the team's current status using live data."""
    current_year = datetime.now().year
    
    # Use existing standings data if provided, otherwise fall back to API call
    if standings_live_lad is not None and not standings_live_lad.empty:
        logging.info("Using existing standings data for summary generation")
        row = standings_live_lad.iloc[0]
        
        # Parse variables from existing standings data
        games_played = row["games_played"]
        division_place = int(row["division_rank"])
        division_place_ord = to_ordinal(division_place)
        record = f"{row['wins']}-{row['losses']}"
        win_pct = float(row["winning_percentage"]) * 100
        # Extract last 10 from streak if possible, otherwise use a default
        try:
            # Parse streak info if available
            streak_type = row.get("streak_type", "")
            streak_number = row.get("streak_number", 0)
            # For simplicity, just use streak number as last 10 wins approximation
            last_10_wins = min(int(streak_number), 10) if streak_type == "wins" else 8  # reasonable default
        except:
            last_10_wins = 8  # reasonable default
            
    else:
        # Fallback to API call if no standings data provided
        logging.info("Falling back to API call for summary generation")
        headers = {
            "sec-ch-ua-platform": '"macOS"',
            "Referer": "https://www.mlb.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
        }
        today_str = date.today().strftime("%Y-%m-%d")
        url = f"https://bdfed.stitch.mlbinfra.com/bdfed/transform-mlb-standings?&splitPcts=false&numberPcts=false&standingsView=division&sortTemplate=3&season={current_year}&leagueIds=103&&leagueIds=104&standingsTypes=regularSeason&contextTeamId=&teamId=&date={today_str}&hydrateAlias=noSchedule&favoriteTeams=119&sortDivisions=201,202,200,204,205,203&sortLeagues=103,104,115,114&sortSports=1"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            json_data = response.json()
            team_records = []
            for record in json_data["records"]:
                team_records.extend(record["teamRecords"])
            
            df = pd.json_normalize(team_records, sep="_")
            # Try different possible column names for team abbreviation
            if 'abbreviation' in df.columns:
                row = df.query('abbreviation == "LAD"').iloc[0]
            elif 'team_abbreviation' in df.columns:
                row = df.query('team_abbreviation == "LAD"').iloc[0]
            elif 'teamAbbreviation' in df.columns:
                row = df.query('teamAbbreviation == "LAD"').iloc[0]
            else:
                # Fallback: find by team name
                lad_rows = df[df.astype(str).apply(lambda x: x.str.contains('Los Angeles Dodgers|LAD', na=False)).any(axis=1)]
                if len(lad_rows) > 0:
                    row = lad_rows.iloc[0]
                else:
                    raise ValueError("Could not find LAD team in standings data")

            # Parse variables from API data
            games_played = row["wins"] + row["losses"]
            division_place = int(row["divisionRank"])
            division_place_ord = to_ordinal(division_place)
            record = f"{row['wins']}-{row['losses']}"
            win_pct = float(row["pct"]) * 100
            last_10_wins = int(row["record_lastTen"].split("-")[0])

        except (requests.exceptions.RequestException, KeyError, IndexError) as e:
            logging.warning(f"Could not fetch or parse live data, using stale data for summary: {e}")
            return "Summary could not be generated due to a data fetching issue."

    # Handle cases where last_game_info_series might be None or empty if no games played
    last_game_summary_fragment = get_live_last_game_summary()
    postseason_summary = generate_postseason_summary()
    next_game_info = get_next_game_info()
    
    # Use current date with single digit day format
    current_date = datetime.now().strftime("%B %-d")

    # summary = (
    #     f"<span class='highlight'>LOS ANGELES</span> <span class='updated'>({update_date_str})</span> — "
    #     f"After <span class='highlight'>{games_played}</span> games this season, the Dodgers are in <span class='highlight'>{division_place_ord}</span> place in the National League West division. "
    #     f"The team has compiled a <span class='highlight'>{record}</span> record, winning <span class='highlight'>{win_pct:.0f}%</span> of its games so far. "
    #     f"{last_game_summary_fragment} "
    #     f"They've won <span class='highlight'>{last_10_wins} of the last 10</span> and are on pace to win at least <span class='highlight'>{projected_wins}</span> games in the regular season."
    # )

    # Format next game info to connect smoothly with series status
    next_game_text = ""
    if next_game_info:
        # Convert "The next game is Monday..." to "and the next game is Monday..."
        next_game_text = f" and the {next_game_info.replace('The next game is ', 'next game is ')}"
    
    # Handle fallback postseason summary (when no series data available)
    if isinstance(postseason_summary, dict) and ('competing' in postseason_summary or 'series_status' in postseason_summary):
        # Structured format with competing/series_status
        competing_text = postseason_summary.get('competing', '')
        series_status = postseason_summary.get('series_status', '')
        
        summary = (
            f"<span class='highlight'>LOS ANGELES</span> <span class='updated'>({current_date})</span> — "
            f"The Dodgers compiled a <span class='highlight'>{record}</span> record in the {current_year} regular season, a <span class='highlight'>{win_pct:.0f}%</span> winning percentage. "
            f"{competing_text} "
            f"{last_game_summary_fragment} "
            f"{series_status}{next_game_text}."
        )
    else:
        # Simple text format (fallback)
        postseason_text = postseason_summary.get('text', '') if isinstance(postseason_summary, dict) else postseason_summary
        
        summary = (
            f"<span class='highlight'>LOS ANGELES</span> <span class='updated'>({current_date})</span> — "
            f"The Dodgers compiled a <span class='highlight'>{record}</span> record in the {current_year} regular season, a <span class='highlight'>{win_pct:.0f}%</span> winning percentage. "
            f"{postseason_text} "
            f"{last_game_summary_fragment}{next_game_text}."
        )
    return summary


def recent_trend(standings):
    last_10 = standings.iloc[:10]['result']  # Ensuring the last 10 games are considered
    win_count_trend = last_10[last_10 == "W"].count()
    loss_count_trend = last_10[last_10 == "L"].count()
    return win_count_trend, loss_count_trend, f"Recent trend: {win_count_trend} wins, {loss_count_trend} losses"

games, wins, losses, record, win_pct, win_pct_decade_thispoint, era, era_rank, strikeouts, strikeouts_rank, walks, walks_rank, wins_last, losses_last, record_last, win_pct_last, home_runs_allowed = current_season_stats(standings_now, standings_past, pitching, standings_last)
runs, runs_last, runs_rank, runs_against, runs_against_last, run_diff, run_diff_last, mean_attendance, formatted_mean_attendance, home_games_count = run_differential(standings)
home_runs, home_runs_rank, home_runs_game, home_runs_game_last, home_runs_game_decade = home_run_stats(batting_now, batting_past)
batting_average, batting_average_decade, stolen_bases, stolen_bases_rank, stolen_bases_game, stolen_bases_last_rate, on_base_pct, on_base_pct_decade = batting_and_stolen_base_stats(batting_now, batting_past, games)
win_count_trend, loss_count_trend, win_loss_trend = recent_trend(standings.iloc[:10])

# Prepare last_game_info, handling empty standings_now for very early season
last_game_data = None
if not standings_now.empty:
    last_game_data = standings_now.iloc[0]

summary = generate_summary(
    update_date, standings_live_lad
)

summary_data = [
    # Standings
    {"stat_label": "Wins", "stat": "wins", "value": wins, "category": "standings", "context_value": wins_last, "context_value_label": "This point last season"},
    {"stat_label": "Losses", "stat": "losses", "value": losses, "category": "standings", "context_value": losses_last, "context_value_label": "This point last season"},
    {"stat_label": "Record", "stat": "record", "value": record, "category": "standings", "context_value": record_last, "context_value_label": "This point last season"},
   
    {"stat_label": "Win percentage", "stat": "win_pct", "value": f"{win_pct}%", "category": "standings", "context_value": f"{win_pct_last}%", "context_value_label": "This point last season"},
    {"stat_label": "Games up/back", "stat": "games_up_back", "value": games_up_back_value, "category": "standings", "context_value": standings_division_rank_ordinal, "context_value_label": 'Division rank'},
    {"stat_label": "Avg. home attendance", "stat": "mean_attendance", "value": formatted_mean_attendance, "category": "standings", "context_value": home_games_count, "context_value_label": 'Home games this season'},
    
    {"stat_label": "Runs", "stat": "runs", "value": runs, "category": "standings", "context_value": runs_rank, "context_value_label": "League rank"},
    {"stat_label": "Runs against", "stat": "runs_against", "value": runs_against, "category": "standings", "context_value": runs_against_last, "context_value_label": "This point last season"},
    {"stat_label": "Run differential", "stat": "run_differential", "value": run_diff, "category": "standings", "context_value": run_diff_last, "context_value_label": "This point last season"},
    
    # Batting
    {"stat_label": "Batting average", "stat": "batting_average", "value": batting_average, "category": "batting", "context_value": batting_average_decade, "context_value_label": "Last decade average"},
    {"stat_label": "Home runs", "stat": "home_runs", "value": home_runs, "category": "batting", "context_value": home_runs_rank,  "context_value_label": "League rank"},
    {"stat_label": "Home runs/game", "stat": "home_runs_game", "value": home_runs_game, "category": "batting", "context_value": home_runs_game_decade, "context_value_label": "Last decade average"},
    
    {"stat_label": "On-base percentage", "stat": "on_base_pct", "value": on_base_pct, "category": "batting", "context_value": on_base_pct_decade, "context_value_label": "Last decade average"},
    {"stat_label": "Stolen bases", "stat": "stolen_bases", "value": stolen_bases, "category": "batting", "context_value": stolen_bases_rank, "context_value_label": "League rank"},
    {"stat_label": "Stolen bases/game", "stat": "stolen_bases_game", "value": stolen_bases_game, "category": "batting", "context_value": stolen_bases_last_rate, "context_value_label": "Rate all last season"},
    
    # Pitching
    {"stat_label": "Strikeouts", "stat": "strikeouts", "value": format_int_with_commas(strikeouts), "category": "pitching", "context_value": strikeouts_rank, "context_value_label": "League rank"},
    {"stat_label": "Walks", "stat": "walks", "value": walks, "category": "pitching", "context_value": walks_rank, "context_value_label": "League rank"},
    # {"stat_label": "Home runs allowed", "stat": "home_runs_allowed", "value": home_runs_allowed, "category": "pitching", "context_value": home_runs_allowed_rank, "context_value_label": "League rank"}, # Rank not available in current JSON
    {"stat_label": "ERA", "stat": "era", "value": era, "category": "pitching", "context_value": era_rank, "context_value_label": "League rank"},
    
    # Summary
    {"stat_label": "Last updated", "stat": "update_time", "value": update_time, "category": "summary", "context_value": "", "context_value_label": ''}, 
    {"stat_label": "Team summary", "stat": "summary", "value": summary, "category": "summary", "context_value": "", "context_value_label": ''},
]
summary_df = pd.DataFrame(summary_data)

# Determine last game result, preferring live standings, then MLB API, then BR fallback
last_game_result_final = None
if last_game_result_live is not None:
    last_game_result_final = last_game_result_live
else:
    last_game_result_api = get_live_last_game_result()
    if last_game_result_api is not None:
        last_game_result_final = last_game_result_api
    else:
        try:
            last_game_result_final = standings_now.iloc[0]['result_clean']
        except Exception:
            last_game_result_final = None

if last_game_result_final is not None:
    summary_df = pd.concat([
        summary_df,
        pd.DataFrame([{ "stat_label": "Last game result", "stat": "last_game_result", "value": last_game_result_final, "category": "summary", "context_value": "", "context_value_label": '' }])
    ], ignore_index=True)
summary_df.to_csv(os.path.join(base_dir, 'data', 'standings', 'season_summary_latest.csv'), index=False)
summary_df.to_json(os.path.join(base_dir, 'data', 'standings', 'season_summary_latest.json'), orient='records', indent=4, lines=False)
summary_df.to_json(os.path.join(base_dir, '_data', 'season_summary_latest.json'), orient='records', indent=4, lines=False)

def save_to_s3(df, base_path, s3_bucket, formats=["csv", "json"]):
    # Attempt to use AWS credentials from environment variables first (for GitHub Actions)
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if aws_access_key_id and aws_secret_access_key:
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name="us-west-1"
        )
        logging.info("Using AWS credentials from environment variables for S3 upload.")
    else:
        # Fallback to local AWS profile if environment variables are not set
        profile_name = os.environ.get("AWS_PERSONAL_PROFILE", "haekeo")
        session = boto3.Session(profile_name=profile_name, region_name="us-west-1")
        logging.info(f"Using AWS profile '{profile_name}' for S3 upload.")
        
    s3_resource = session.resource("s3")
    for fmt in formats:
        file_path = f"{base_path}.{fmt}"
        buffer = BytesIO()
        if fmt == "csv":
            df.to_csv(buffer, index=False)
            content_type = "text/csv"
        elif fmt == "json":
            df.to_json(buffer, orient="records", indent=4, lines=False)
            content_type = "application/json"
        buffer.seek(0)
        s3_resource.Bucket(s3_bucket).put_object(Key=file_path, Body=buffer, ContentType=content_type)
        logging.info(f"Uploaded {fmt} to {s3_bucket}/{file_path}")

save_to_s3(summary_df, "dodgers/data/standings/season_summary_latest", "stilesdata.com")