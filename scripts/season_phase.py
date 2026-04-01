#!/usr/bin/env python
"""
Season phase detector for LA Dodgers

Queries MLB StatsAPI to determine the current season phase:
- regular_season: LAD has upcoming/active regular season games
- postseason: LAD has upcoming/active postseason games
- offseason: No upcoming games for LAD

This replaces the simple date-based heuristic with real schedule data.
"""

import requests
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DODGERS_TEAM_ID = 119
BASE_URL = "https://statsapi.mlb.com/api/v1"

def get_dodgers_schedule(start_date, end_date, game_type=None):
    """
    Fetch Dodgers schedule from MLB StatsAPI
    
    Args:
        start_date: datetime object for start of range
        end_date: datetime object for end of range
        game_type: Optional game type filter ('R' for regular, 'P' for postseason)
    
    Returns:
        List of game dictionaries
    """
    url = f"{BASE_URL}/schedule"
    params = {
        "sportId": 1,
        "teamId": DODGERS_TEAM_ID,
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "hydrate": "team,linescore"
    }
    
    if game_type:
        params["gameType"] = game_type
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for date_entry in data.get("dates", []):
            for game in date_entry.get("games", []):
                games.append(game)
        
        return games
    except Exception as e:
        logging.error(f"Failed to fetch schedule: {e}")
        return []

def has_active_or_upcoming_games(games):
    """Check if any games are active or upcoming (not Final/Completed)"""
    for game in games:
        status = game.get("status", {}).get("detailedState", "")
        if status not in ["Final", "Completed", "Postponed", "Cancelled"]:
            return True
    return False

def detect_season_phase():
    """
    Detect current season phase for the Dodgers
    
    Returns:
        tuple: (phase, postseason_active, season_year)
        - phase: 'regular_season', 'postseason', or 'offseason'
        - postseason_active: boolean
        - season_year: int (current MLB season year)
    """
    now = datetime.now()
    current_year = now.year
    
    # Check next 7 days for upcoming games
    future_window = now + timedelta(days=7)
    
    logging.info(f"Checking Dodgers schedule from {now.date()} to {future_window.date()}")
    
    # Check for postseason games first (higher priority)
    postseason_games = get_dodgers_schedule(now, future_window, game_type="P")
    logging.info(f"Found {len(postseason_games)} postseason games in next 7 days")
    
    if postseason_games and has_active_or_upcoming_games(postseason_games):
        logging.info("✅ Phase detected: POSTSEASON (active or upcoming postseason games)")
        return ("postseason", True, current_year)
    
    # Check for regular season games
    regular_games = get_dodgers_schedule(now, future_window, game_type="R")
    logging.info(f"Found {len(regular_games)} regular season games in next 7 days")
    
    if regular_games and has_active_or_upcoming_games(regular_games):
        logging.info("✅ Phase detected: REGULAR_SEASON (active or upcoming regular season games)")
        return ("regular_season", False, current_year)
    
    # No upcoming games = offseason
    logging.info("✅ Phase detected: OFFSEASON (no upcoming games in next 7 days)")
    
    # In offseason, determine which year's season we're in
    # If before March, we're still in previous year's offseason
    if now.month < 3:
        season_year = current_year - 1
    else:
        season_year = current_year
    
    return ("offseason", False, season_year)

def get_postseason_series_status():
    """
    Get detailed postseason series status if in postseason
    
    Returns:
        dict with series information or None
    """
    now = datetime.now()
    current_year = now.year
    
    url = f"{BASE_URL}/schedule/postseason/series"
    params = {
        "sportId": 1,
        "season": current_year,
        "hydrate": "team,seriesStatus"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Find Dodgers' current series
        for series_group in data.get("series", []):
            for game in series_group.get("games", []):
                home_team = game.get("teams", {}).get("home", {}).get("team", {}).get("id")
                away_team = game.get("teams", {}).get("away", {}).get("team", {}).get("id")
                
                if DODGERS_TEAM_ID in [home_team, away_team]:
                    series_status = game.get("seriesStatus", {})
                    return {
                        "series_name": series_status.get("shortName", "Unknown"),
                        "is_over": series_status.get("isOver", False),
                        "result": series_status.get("result", "In Progress")
                    }
        
        return None
    except Exception as e:
        logging.error(f"Failed to fetch postseason series: {e}")
        return None

def main():
    """Test the phase detector"""
    phase, postseason_active, season_year = detect_season_phase()
    
    print(f"\n{'='*50}")
    print(f"Season Phase Detection Results")
    print(f"{'='*50}")
    print(f"Phase: {phase}")
    print(f"Postseason Active: {postseason_active}")
    print(f"Season Year: {season_year}")
    
    if postseason_active:
        series = get_postseason_series_status()
        if series:
            print(f"\nCurrent Series: {series['series_name']}")
            print(f"Status: {series['result']}")
    
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
