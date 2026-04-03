#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers batting: Fetch from MLB Stats API and combine with historical archive
This replaces Baseball Reference with the much faster MLB Stats API.
"""

import os
import boto3
import pandas as pd
import requests
import logging
from io import BytesIO
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

DODGERS_TEAM_ID = 119
year = datetime.now().year

# Headers for MLB Stats API
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
}


def fetch_team_batting_stats():
    """Fetch team batting totals from MLB Stats API"""
    url = f"https://statsapi.mlb.com/api/v1/teams/{DODGERS_TEAM_ID}/stats"
    params = {
        'stats': 'season',
        'group': 'hitting',
        'season': year
    }
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Extract hitting stats from the response
        stats = data['stats'][0]['splits'][0]['stat']
        
        # Map MLB API fields to our schema (matching Baseball Reference column names)
        team_stats = {
            'season': year,
            'name': 'Team Totals',
            'g': stats.get('gamesPlayed', 0),
            'pa': stats.get('plateAppearances', 0),
            'ab': stats.get('atBats', 0),
            'r': stats.get('runs', 0),
            'h': stats.get('hits', 0),
            '2b': stats.get('doubles', 0),
            '3b': stats.get('triples', 0),
            'hr': stats.get('homeRuns', 0),
            'rbi': stats.get('rbi', 0),
            'sb': stats.get('stolenBases', 0),
            'cs': stats.get('caughtStealing', 0),
            'bb': stats.get('baseOnBalls', 0),
            'so': stats.get('strikeOuts', 0),
            'ba': stats.get('avg', '.000'),
            'obp': stats.get('obp', '.000'),
            'slg': stats.get('slg', '.000'),
            'ops': stats.get('ops', '.000'),
            'tb': stats.get('totalBases', 0),
            'gdp': stats.get('groundIntoDoublePlay', 0),
            'hbp': stats.get('hitByPitch', 0),
            'sh': stats.get('sacBunts', 0),
            'sf': stats.get('sacFlies', 0),
            'ibb': stats.get('intentionalWalks', 0),
        }
        
        # Calculate OPS+ (league average is 100)
        # For now, set to None - would need league average to calculate properly
        team_stats['ops_plus'] = None
        
        logging.info(f"Successfully fetched team batting stats for {year}")
        return pd.DataFrame([team_stats])
        
    except Exception as e:
        logging.error(f"Failed to fetch team batting stats from MLB API: {e}")
        raise


def fetch_player_batting_stats():
    """Fetch individual player batting stats from MLB Stats API"""
    url = f"https://statsapi.mlb.com/api/v1/teams/{DODGERS_TEAM_ID}/roster"
    params = {
        'rosterType': 'active',
        'season': year
    }
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        roster_data = response.json()
        
        player_stats = []
        
        # Get stats for each player on the roster
        for player in roster_data.get('roster', []):
            player_id = player['person']['id']
            player_name = player['person']['fullName']
            position = player.get('position', {}).get('abbreviation', 'Unknown')
            
            # Fetch individual player stats
            stats_url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats"
            stats_params = {
                'stats': 'season',
                'group': 'hitting',
                'season': year
            }
            
            try:
                stats_response = requests.get(stats_url, params=stats_params, headers=HEADERS, timeout=10)
                stats_response.raise_for_status()
                stats_data = stats_response.json()
                
                if stats_data.get('stats') and len(stats_data['stats']) > 0:
                    if stats_data['stats'][0].get('splits') and len(stats_data['stats'][0]['splits']) > 0:
                        stats = stats_data['stats'][0]['splits'][0]['stat']
                        
                        # Determine batting stance (would need separate API call for full player info)
                        # For now, we'll leave it as Unknown and can enhance later
                        bats = 'Unknown'
                        
                        player_stat = {
                            'season': year,
                            'player': player_name,
                            'pos': position,
                            'g': stats.get('gamesPlayed', 0),
                            'pa': stats.get('plateAppearances', 0),
                            'ab': stats.get('atBats', 0),
                            'r': stats.get('runs', 0),
                            'h': stats.get('hits', 0),
                            '2b': stats.get('doubles', 0),
                            '3b': stats.get('triples', 0),
                            'hr': stats.get('homeRuns', 0),
                            'rbi': stats.get('rbi', 0),
                            'sb': stats.get('stolenBases', 0),
                            'cs': stats.get('caughtStealing', 0),
                            'bb': stats.get('baseOnBalls', 0),
                            'so': stats.get('strikeOuts', 0),
                            'ba': stats.get('avg', '.000'),
                            'obp': stats.get('obp', '.000'),
                            'slg': stats.get('slg', '.000'),
                            'ops': stats.get('ops', '.000'),
                            'tb': stats.get('totalBases', 0),
                            'gdp': stats.get('groundIntoDoublePlay', 0),
                            'hbp': stats.get('hitByPitch', 0),
                            'sh': stats.get('sacBunts', 0),
                            'sf': stats.get('sacFlies', 0),
                            'ibb': stats.get('intentionalWalks', 0),
                            'ops_plus': None,  # Would need league average to calculate
                            'bats': bats
                        }
                        
                        player_stats.append(player_stat)
                        
            except Exception as e:
                logging.warning(f"Could not fetch stats for {player_name}: {e}")
                continue
        
        logging.info(f"Successfully fetched stats for {len(player_stats)} players")
        return pd.DataFrame(player_stats).rename(columns={'player': 'name'})
        
    except Exception as e:
        logging.error(f"Failed to fetch player batting stats from MLB API: {e}")
        raise


def save_dataframe(df, path_without_extension, formats):
    """Save dataframes with different formats and file extensions"""
    os.makedirs(os.path.dirname(path_without_extension), exist_ok=True)
    for file_format in formats:
        file_path = f"{path_without_extension}.{file_format}"
        if file_format == "csv":
            df.to_csv(file_path, index=False)
        elif file_format == "json":
            df.to_json(file_path, orient="records", lines=True)
        elif file_format == "parquet":
            df.to_parquet(file_path, index=False)


def save_to_s3(df, base_path, s3_bucket, formats=["csv", "json", "parquet"]):
    """Save Pandas DataFrame in specified formats and upload to S3 bucket"""
    # Use environment variables if available (GitHub Actions), otherwise use local profile
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        session = boto3.Session(
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name='us-west-1'  
        )
        logging.info("Using AWS credentials from environment variables")
    else:
        profile_name = os.environ.get("AWS_PERSONAL_PROFILE", "haekeo")
        session = boto3.Session(profile_name=profile_name, region_name='us-west-1')
        logging.info(f"Using AWS profile: {profile_name}")
    
    s3_resource = session.resource("s3")

    for fmt in formats:
        file_path = f"{base_path}.{fmt}"
        buffer = BytesIO()
        if fmt == "csv":
            df.to_csv(buffer, index=False)
            content_type = "text/csv"
        elif fmt == "json":
            df.to_json(buffer, orient="records", lines=True)
            content_type = "application/json"
        elif fmt == "parquet":
            df.to_parquet(buffer, index=False)
            content_type = "application/octet-stream"

        buffer.seek(0)
        s3_resource.Bucket(s3_bucket).put_object(
            Key=file_path, Body=buffer, ContentType=content_type
        )
        logging.info(f"Uploaded {fmt} to {s3_bucket}/{file_path}")


def main():
    """Main execution function"""
    logging.info(f"Fetching Dodgers batting stats for {year} from MLB Stats API")
    
    # Fetch current season data from MLB API
    team_totals_df = fetch_team_batting_stats()
    player_totals_df = fetch_player_batting_stats()
    
    # Load historical archives
    logging.info("Loading historical batting archives")
    player_totals_archive_df = pd.read_parquet(
        "https://stilesdata.com/dodgers/data/batting/archive/dodgers_player_batting_statistics_1958_2024.parquet"
    )
    
    team_totals_archive_df = pd.read_parquet(
        "https://stilesdata.com/dodgers/data/batting/archive/dodgers_team_batting_statistics_1958_2024.parquet"
    )
    
    # Ensure season is consistent type (string) before combining
    player_totals_df['season'] = player_totals_df['season'].astype(str)
    team_totals_df['season'] = team_totals_df['season'].astype(str)
    
    # Combine current season with historical data
    players_full_df = (
        pd.concat([player_totals_df, player_totals_archive_df])
        .sort_values("season", ascending=False)
        .reset_index(drop=True)
    )
    
    team_full_df = (
        pd.concat([team_totals_df, team_totals_archive_df])
        .sort_values("season", ascending=False)
        .reset_index(drop=True)
    )
    
    # Clean data types for integer columns (handle mixed types from historical data)
    int_columns = ['g', 'pa', 'ab', 'r', 'h', '2b', '3b', 'hr', 'rbi', 'sb', 'cs', 
                   'bb', 'so', 'tb', 'gdp', 'hbp', 'sh', 'sf', 'ibb']
    # Keep batting average columns as strings (format like .264 not 0.264)
    avg_columns = ['ba', 'obp', 'slg', 'ops']
    
    for col in int_columns:
        if col in players_full_df.columns:
            players_full_df[col] = pd.to_numeric(players_full_df[col], errors='coerce').fillna(0).astype(int)
        if col in team_full_df.columns:
            team_full_df[col] = pd.to_numeric(team_full_df[col], errors='coerce').fillna(0).astype(int)
    
    # Keep average columns as strings but ensure consistent format
    for col in avg_columns:
        if col in players_full_df.columns:
            players_full_df[col] = players_full_df[col].astype(str)
        if col in team_full_df.columns:
            team_full_df[col] = team_full_df[col].astype(str)
    
    # Note: Team ranks are no longer fetched from Baseball Reference
    # They're now fetched by script 03_scrape_league_ranks.py
    # We'll just load the historical ranks for archival purposes
    try:
        team_ranks_archive_df = pd.read_parquet(
            "https://stilesdata.com/dodgers/data/batting/archive/dodgers_team_batting_rankings_1958_2024.parquet"
        )
        team_ranks_full_df = team_ranks_archive_df.copy()
    except Exception as e:
        logging.warning(f"Could not load historical team ranks: {e}")
        team_ranks_full_df = pd.DataFrame()
    
    # Save local files
    logging.info("Saving files locally")
    formats = ["csv", "json", "parquet"]
    try:
        save_dataframe(
            players_full_df,
            "data/batting/dodgers_player_batting_1958_present",
            formats,
        )
        save_dataframe(
            team_full_df, 
            "data/batting/dodgers_team_batting_1958_present", 
            formats
        )
        if not team_ranks_full_df.empty:
            save_dataframe(
                team_ranks_full_df,
                "data/batting/dodgers_team_batting_ranks_1958_present",
                formats,
            )
    except Exception as e:
        logging.error(f"An error occurred saving local files: {e}")
        raise
    
    # Upload to S3
    logging.info("Uploading to S3")
    save_to_s3(
        players_full_df,
        "dodgers/data/batting/dodgers_player_batting_1958_present",
        "stilesdata.com",
    )
    save_to_s3(
        team_full_df,
        "dodgers/data/batting/dodgers_team_batting_1958_present",
        "stilesdata.com",
    )
    if not team_ranks_full_df.empty:
        save_to_s3(
            team_ranks_full_df,
            "dodgers/data/batting/dodgers_team_batting_ranks_1958_present",
            "stilesdata.com",
        )
    
    logging.info("Batting data fetch and processing complete!")


if __name__ == "__main__":
    main()
