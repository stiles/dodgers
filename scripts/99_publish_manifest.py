#!/usr/bin/env python
"""
Generate and publish the data manifest.
This script reads metadata from existing outputs and consolidates into manifest.json.
"""
import os
import json
import boto3
from datetime import datetime
import pytz
import logging

# Import season phase detector
from season_phase import detect_season_phase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
OUTPUT_FILE = "data/manifest.json"
S3_BUCKET = "stilesdata.com"
S3_KEY = "dodgers/data/manifest.json"

def get_pacific_time():
    """Return current Pacific time as ISO string."""
    pacific = pytz.timezone('US/Pacific')
    return datetime.now(pacific).isoformat()

def build_manifest():
    """Build the manifest structure."""
    # Use real MLB API-based phase detection
    phase, postseason_active, season_year = detect_season_phase()
    season = str(season_year)
    
    logging.info(f"Detected phase: {phase}, postseason_active: {postseason_active}, season: {season}")
    
    manifest = {
        "version": "1.0",
        "last_updated": get_pacific_time(),
        "season": season,
        "phase": phase,
        "postseason_active": postseason_active,
        "datasets": []
    }
    
    # Dataset definitions (migrated from data_inventory.md)
    # For v1, we're just wrapping existing URLs
    datasets = [
        {
            "id": "standings_1958_present",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Game-by-game standings 1958-present",
            "cadence": "regular_season_daily",
            "source": "mlb_statsapi",
            "source_historical": "baseball_reference_archives"
        },
        {
            "id": "standings_1958_present_optimized",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present_optimized.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Optimized standings (year, gm, win_pct, gb only)",
            "cadence": "regular_season_daily",
            "source": "mlb_statsapi",
            "source_historical": "baseball_reference_archives"
        },
        {
            "id": "wins_losses_current",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/dodgers_wins_losses_current.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Current season wins/losses/run differential",
            "cadence": "regular_season_daily",
            "source": "mlb_statsapi"
        },
        {
            "id": "schedule_current",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/dodgers_schedule.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Last 10 games and next 10 games",
            "cadence": "regular_season_daily",
            "source": "mlb_statsapi"
        },
        {
            "id": "all_teams_standings_current",
            "version": "v1",
            "url": f"https://stilesdata.com/dodgers/data/standings/all_teams_standings_metrics_{season}.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Current year standings for all MLB teams",
            "cadence": "regular_season_daily",
            "source": "mlb_statsapi"
        },
        {
            "id": "mlb_team_attendance",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/mlb_team_attendance.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "MLB attendance by team",
            "cadence": "regular_season_weekly",
            "source": "baseball_reference_scrape"
        },
        {
            "id": "player_batting_current",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_current_table.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Current season player batting stats",
            "cadence": "regular_season_daily",
            "source": "mlb_bdfed"
        },
        {
            "id": "xwoba_current",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/batting/dodgers_xwoba_current.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Rolling 100 PA xwOBA per player",
            "cadence": "regular_season_daily",
            "source": "baseball_savant"
        },
        {
            "id": "shohei_home_runs",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/batting/shohei_home_runs_cumulative_timeseries_combined.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Shohei Ohtani cumulative home runs",
            "cadence": "regular_season_daily",
            "source": "mlb_bdfed"
        },
        {
            "id": "shohei_stolen_bases",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/batting/shohei_stolen_bases_cumulative_timeseries_combined.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Shohei Ohtani cumulative stolen bases",
            "cadence": "regular_season_daily",
            "source": "mlb_bdfed"
        },
        {
            "id": "historic_batting_gamelogs",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/batting/archive/dodgers_historic_batting_gamelogs.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Game-by-game batting stats (doubles, homers, hits)",
            "cadence": "regular_season_daily",
            "source": "mlb_statsapi",
            "source_historical": "baseball_reference_archives"
        },
        {
            "id": "historic_pitching_gamelogs",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/pitching/dodgers_historic_pitching_gamelogs_1958-present.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Game-by-game pitching stats (ERA, K's, hits allowed)",
            "cadence": "regular_season_daily",
            "source": "mlb_statsapi",
            "source_historical": "baseball_reference_archives"
        },
        {
            "id": "shohei_pitch_mix",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/pitching/shohei_ohtani_pitch_mix.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Shohei Ohtani pitch type distribution",
            "cadence": "regular_season_daily",
            "source": "baseball_savant"
        },
        {
            "id": "shohei_pitches",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/pitching/shohei_ohtani_pitches.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Shohei Ohtani pitch-by-pitch data",
            "cadence": "regular_season_daily",
            "source": "baseball_savant"
        },
        {
            "id": "umpire_summary",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/summary/umpire_summary.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Umpire scorecard summary",
            "cadence": "regular_season_daily",
            "source": "baseball_savant"
        },
        {
            "id": "abs_challenges",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/summary/abs_challenges.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "ABS challenge tracking",
            "cadence": "regular_season_daily",
            "source": "mlb_statsapi"
        },
        {
            "id": "postseason_players_current",
            "version": "v1",
            "url": f"https://stilesdata.com/dodgers/data/postseason/dodgers_postseason_stats_{season}.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Current postseason player stats",
            "cadence": "postseason_only",
            "source": "mlb_statsapi"
        },
        {
            "id": "postseason_series_current",
            "version": "v1",
            "url": f"https://stilesdata.com/dodgers/data/postseason/dodgers_postseason_series_{season}.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Current postseason series journey",
            "cadence": "postseason_only",
            "source": "mlb_statsapi"
        },
        {
            "id": "wins_projection",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/dodgers_wins_projection_timeseries.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Projected final wins (simulation)",
            "cadence": "regular_season_daily",
            "source": "derived"
        }
    ]
    
    manifest["datasets"] = datasets
    return manifest

def main():
    """Generate and publish manifest."""
    logging.info("Generating manifest...")
    manifest = build_manifest()
    
    # Write locally
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(manifest, f, indent=2)
    logging.info(f"✅ Manifest written to {OUTPUT_FILE}")
    logging.info(f"   Season: {manifest['season']}, Phase: {manifest['phase']}, Postseason active: {manifest['postseason_active']}")
    logging.info(f"   Datasets: {len(manifest['datasets'])}")
    
    # Upload to S3
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    if is_github_actions:
        session = boto3.Session(
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name="us-west-1"
        )
    else:
        session = boto3.Session(profile_name="haekeo", region_name="us-west-1")
    
    s3 = session.resource('s3')
    s3.Bucket(S3_BUCKET).upload_file(
        OUTPUT_FILE, 
        S3_KEY, 
        ExtraArgs={'ContentType': 'application/json'}
    )
    logging.info(f"✅ Manifest uploaded to s3://{S3_BUCKET}/{S3_KEY}")
    logging.info(f"   Public URL: https://stilesdata.com/{S3_KEY}")

if __name__ == "__main__":
    main()
