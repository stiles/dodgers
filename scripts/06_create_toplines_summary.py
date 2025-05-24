#!/usr/bin/env python
# coding: utf-8


"""
LA Dodgers toplines
This notebook extracts key statistics from the project's processed tables for display in a dashboard.
"""

import os
import pandas as pd
import boto3
from io import BytesIO
import logging
from datetime import datetime, timezone, timedelta
import json

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

# URLs for data
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
game_number = standings_now['gm'].iloc[0]
standings_last = standings_past.query(f"gm == {game_number}").head(1).reset_index(drop=True).copy()
standings_last_season = standings_past.query(f"gm <= {game_number} and year=='{last_year}'").reset_index(drop=True).copy()
standings["rank_ordinal"] = standings["rank"].map(to_ordinal)
standings_division_rank = standings['rank'].iloc[0]
standings_division_rank_ordinal = standings['rank_ordinal'].iloc[0]
standings_division_rank_games_back = standings['gb'].iloc[0]

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

def generate_summary(
    update_date_str,
    games_played_count,
    division_rank_ord_str,
    team_record_str,
    team_win_pct_val,
    last_game_info_series, # Expects a Pandas Series, e.g., standings_now.iloc[0]
    win_trend_count,
    current_wins_total
):
    """Generates a narrative summary of the team's current status."""
    projected_total_wins = calculate_projected_wins(current_wins_total, games_played_count)
    
    # Handle cases where last_game_info_series might be None or empty if no games played
    if last_game_info_series is None or last_game_info_series.empty:
        last_game_summary_fragment = "The season is yet to begin or data is not available for the last game."
    else:
        last_game_summary_fragment = (
            f"The last game was a <span class='highlight'>{last_game_info_series.get('r', 'N/A')}-{last_game_info_series.get('ra', 'N/A')}</span> "
            f"{last_game_info_series.get('home_away', 'N/A')} <span class='highlight'>{last_game_info_series.get('result_clean', 'N/A')}</span> "
            f"against the {last_game_info_series.get('opp_name', 'N/A')} in front of <span class='highlight'>{last_game_info_series.get('attendance', 0):,}</span> fans."
        )

    summary = (
        f"<span class='highlight'>LOS ANGELES</span> <span class='updated'>({update_date_str})</span> — "
        f"After <span class='highlight'>{games_played_count}</span> games this season, the Dodgers are in <span class='highlight'>{division_rank_ord_str}</span> place in the National League West division. "
        f"The team has compiled a <span class='highlight'>{team_record_str}</span> record, winning <span class='highlight'>{team_win_pct_val}%</span> of its games so far. "
        f"{last_game_summary_fragment} "
        f"They've won <span class='highlight'>{win_trend_count} of the last 10</span> and are on pace to win about <span class='highlight'>{projected_total_wins}</span> games in the regular season."
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
    update_date, 
    games, 
    standings_division_rank_ordinal, 
    record, 
    win_pct, 
    last_game_data, # Use the potentially None series
    win_count_trend, 
    wins
)

summary_data = [
    # Standings
    {"stat_label": "Wins", "stat": "wins", "value": wins, "category": "standings", "context_value": wins_last, "context_value_label": "This point last season"},
    {"stat_label": "Losses", "stat": "losses", "value": losses, "category": "standings", "context_value": losses_last, "context_value_label": "This point last season"},
    {"stat_label": "Record", "stat": "record", "value": record, "category": "standings", "context_value": record_last, "context_value_label": "This point last season"},
   
    {"stat_label": "Win percentage", "stat": "win_pct", "value": f"{win_pct}%", "category": "standings", "context_value": f"{win_pct_last}%", "context_value_label": "This point last season"},
    {"stat_label": "Games up/back", "stat": "games_up_back", "value": standings_division_rank_games_back, "category": "standings", "context_value": standings_division_rank_ordinal, "context_value_label": 'Division rank'},
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
    {"stat_label": "Strikeouts", "stat": "strikeouts", "value": strikeouts, "category": "pitching", "context_value": strikeouts_rank, "context_value_label": "League rank"},
    {"stat_label": "Walks", "stat": "walks", "value": walks, "category": "pitching", "context_value": walks_rank, "context_value_label": "League rank"},
    # {"stat_label": "Home runs allowed", "stat": "home_runs_allowed", "value": home_runs_allowed, "category": "pitching", "context_value": home_runs_allowed_rank, "context_value_label": "League rank"}, # Rank not available in current JSON
    {"stat_label": "ERA", "stat": "era", "value": era, "category": "pitching", "context_value": era_rank, "context_value_label": "League rank"},
    
    # Summary
    {"stat_label": "Last updated", "stat": "update_time", "value": update_time, "category": "summary", "context_value": "", "context_value_label": ''}, 
    {"stat_label": "Team summary", "stat": "summary", "value": summary, "category": "summary", "context_value": "", "context_value_label": ''},
]
summary_data.append(
    {"stat_label": "Last game result", "stat": "last_game_result", "value": standings_now.iloc[0]['result_clean'], "category": "summary", "context_value": "", "context_value_label": ''}
)
summary_df = pd.DataFrame(summary_data)
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