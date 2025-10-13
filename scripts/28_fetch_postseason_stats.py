import os
import requests
import pandas as pd
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# We'll fetch all batters (non-pitchers) and filter to top 12 by plate appearances

# Output files
output_dir = "data/postseason"
json_file = f"{output_dir}/dodgers_postseason_stats_2025.json"
series_file = f"{output_dir}/dodgers_postseason_series_2025.json"

def fetch_roster_data():
    """Fetch roster data from local file or URL"""
    local_file = "data/roster/dodgers_roster_current.json"
    if os.path.exists(local_file):
        with open(local_file, 'r') as f:
            return json.load(f)
    else:
        # Fallback to URL
        s3_key_json = "https://stilesdata.com/dodgers/data/roster/dodgers_roster_current.json"
        response = requests.get(s3_key_json)
        return response.json()

def get_all_batters():
    """Get all non-pitcher players from roster data"""
    roster_json = fetch_roster_data()
    roster_df = pd.DataFrame(roster_json)
    
    # Filter out pitchers and get only batters
    batters = roster_df[~roster_df['position_group'].isin(['Pitchers'])]
    
    player_ids = {}
    for _, player_row in batters.iterrows():
        player_name = player_row['name']
        player_id = player_row['player_id']
        player_ids[player_name] = player_id
        logging.info(f"Found batter {player_name}: {player_id}")
    
    logging.info(f"Total batters found: {len(player_ids)}")
    return player_ids

def fetch_postseason_series():
    """Fetch postseason series data from MLB API"""
    # Try different parameter combinations to get the most current data
    urls = [
        # Most comprehensive - all postseason game types with current season
        "https://statsapi.mlb.com/api/v1/schedule/postseason/series?sportId=1&season=2025&language=en&timeZone=America/New_York&hydrate=team,linescore(matchup),flags,statusFlags,broadcasts(all),venue(location),decisions,game(content(media(epg),summary),tickets),seriesStatus(useOverride=true)&sortBy=gameDate",
        # Alternative with specific game types
        "https://statsapi.mlb.com/api/v1/schedule/postseason/series?sportId=1&gameType=D&gameType=F&gameType=L&gameType=W&season=2025&language=en&hydrate=team,seriesStatus(useOverride=true)&sortBy=gameDate",
        # Simpler call to avoid potential caching issues
        "https://statsapi.mlb.com/api/v1/schedule/postseason?sportId=1&season=2025&hydrate=team,seriesStatus&language=en"
    ]
    
    for i, url in enumerate(urls):
        try:
            logging.info(f"Trying API URL {i+1}/{len(urls)}")
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            logging.info(f"API response keys: {list(data.keys())}")
            if 'series' in data:
                logging.info(f"Found {len(data['series'])} series groups")
            
            # Extract Dodgers-relevant series information
            dodgers_series = []
            
            if 'series' in data:
                for series_group in data['series']:
                    if 'games' in series_group:
                        logging.info(f"Processing series group with {len(series_group['games'])} games")
                        for game in series_group['games']:
                            # Check if Dodgers are involved
                            home_team = game.get('teams', {}).get('home', {}).get('team', {}).get('name', '')
                            away_team = game.get('teams', {}).get('away', {}).get('team', {}).get('name', '')
                            
                            if 'Los Angeles Dodgers' in [home_team, away_team]:
                                series_status = game.get('seriesStatus', {})
                                series_name = series_status.get('shortName', 'Unknown Series')
                                game_date = game.get('gameDate', '')
                                
                                logging.info(f"Found Dodgers game: {series_name} on {game_date}")
                                logging.info(f"Series status: {series_status}")
                                
                                # Determine series info
                                series_info = {
                                    'series_name': series_name,
                                    'description': series_status.get('description', ''),
                                    'is_over': series_status.get('isOver', False),
                                    'result': series_status.get('result', ''),
                                    'wins': series_status.get('wins', 0),
                                    'losses': series_status.get('losses', 0),
                                    'total_games': series_status.get('totalGames', 0),
                                    'opponent': away_team if home_team == 'Los Angeles Dodgers' else home_team,
                                    'game_date': game_date,
                                    'status': game.get('status', {}).get('detailedState', ''),
                                    'game_number': series_status.get('gameNumber', 0)
                                }
                                
                                # Avoid duplicates by checking if we already have this series
                                existing_series = next((s for s in dodgers_series if s['series_name'] == series_name), None)
                                if not existing_series:
                                    dodgers_series.append(series_info)
                                    logging.info(f"Added new series: {series_name} vs {series_info['opponent']} - {series_info['result']}")
                                else:
                                    # Update with latest info if this game is more recent
                                    if game_date > existing_series.get('game_date', ''):
                                        existing_series.update(series_info)
                                        logging.info(f"Updated series: {series_name} with more recent data")
            
            if dodgers_series:
                logging.info(f"Successfully found {len(dodgers_series)} Dodgers series with URL {i+1}")
                return dodgers_series
            else:
                logging.warning(f"No Dodgers series found with URL {i+1}")
                
        except Exception as e:
            logging.error(f"Error with API URL {i+1}: {e}")
            continue
    
    logging.error("All API URLs failed")
    return []

def fetch_postseason_stats(player_id, player_name):
    """Fetch postseason stats for a specific player"""
    headers = {
        'sec-ch-ua-platform': '"macOS"',
        'Referer': f'https://www.mlb.com/player/{player_name.lower().replace(" ", "-")}-{player_id}',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
    }
    
    url = f'https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=yearByYear&gameType=P&leagueListId=mlb_hist&group=hitting&hydrate=team(league)&language=en'
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Extract 2025 postseason stats
        stats_2025 = None
        if 'stats' in data and len(data['stats']) > 0:
            for stat_group in data['stats']:
                if stat_group['type']['displayName'] == 'yearByYear':
                    for split in stat_group['splits']:
                        if split['season'] == '2025':
                            stats_2025 = split['stat']
                            break
                    break
        
        if stats_2025:
            logging.info(f"Found 2025 postseason stats for {player_name}")
            return {
                'player_id': player_id,
                'player_name': player_name,
                'season': '2025',
                'stats': stats_2025
            }
        else:
            logging.warning(f"No 2025 postseason stats found for {player_name}")
            return None
            
    except Exception as e:
        logging.error(f"Error fetching stats for {player_name}: {e}")
        return None

def main():
    """Main function to fetch all postseason stats and series data"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Fetch series data
    logging.info("Fetching postseason series data...")
    series_data = fetch_postseason_series()
    
    # Create a structured playoff journey
    playoff_journey = [
        {"round": "Wild Card", "series_name": "NL Wild Card Series", "status": "upcoming", "opponent": "?", "result": "?"},
        {"round": "NLDS", "series_name": "NL Division Series", "status": "upcoming", "opponent": "?", "result": "?"},
        {"round": "NLCS", "series_name": "NL Championship Series", "status": "upcoming", "opponent": "?", "result": "?"},
        {"round": "World Series", "series_name": "World Series", "status": "upcoming", "opponent": "?", "result": "?"}
    ]
    
    # Update with actual data
    for series in series_data:
        series_name = series.get('series_name', '').lower()
        description = series.get('description', '').lower()
        
        logging.info(f"Processing series: {series_name}, description: {description}")
        
        if 'wild card' in series_name or 'wild card' in description:
            playoff_journey[0].update({
                "status": "completed" if series.get('is_over') else "in_progress",
                "opponent": series.get('opponent', '?'),
                "result": series.get('result', '?'),
                "wins": series.get('wins', 0),
                "losses": series.get('losses', 0)
            })
            logging.info(f"Updated Wild Card: {playoff_journey[0]}")
        elif 'division' in series_name or 'nlds' in series_name.lower() or 'division' in description:
            playoff_journey[1].update({
                "status": "completed" if series.get('is_over') else "in_progress",
                "opponent": series.get('opponent', '?'),
                "result": series.get('result', '?'),
                "wins": series.get('wins', 0),
                "losses": series.get('losses', 0)
            })
            logging.info(f"Updated NLDS: {playoff_journey[1]}")
        elif 'championship' in series_name or 'nlcs' in series_name.lower() or 'championship' in description:
            playoff_journey[2].update({
                "status": "completed" if series.get('is_over') else "in_progress",
                "opponent": series.get('opponent', '?'),
                "result": series.get('result', '?'),
                "wins": series.get('wins', 0),
                "losses": series.get('losses', 0)
            })
            logging.info(f"Updated NLCS: {playoff_journey[2]}")
        elif 'world series' in series_name or 'world series' in description:
            playoff_journey[3].update({
                "status": "completed" if series.get('is_over') else "in_progress",
                "opponent": series.get('opponent', '?'),
                "result": series.get('result', '?'),
                "wins": series.get('wins', 0),
                "losses": series.get('losses', 0)
            })
            logging.info(f"Updated World Series: {playoff_journey[3]}")
        else:
            logging.warning(f"Could not categorize series: {series_name} - {description}")
    
    # Manual override based on known current state (Oct 13, 2025)
    # Update to reflect current NLCS vs Brewers starting today
    
    # NLDS vs Phillies is completed
    for journey in playoff_journey:
        if journey['round'] == 'NLDS':
            journey.update({
                "status": "completed",
                "opponent": "Philadelphia Phillies", 
                "result": "LAD wins 3-1",
                "wins": 3,
                "losses": 1
            })
            logging.info("Applied manual override for completed NLDS vs Phillies (3-1)")
        elif journey['round'] == 'NLCS':
            journey.update({
                "status": "in_progress",
                "opponent": "Milwaukee Brewers",
                "result": "Series tied 0-0",
                "wins": 0,
                "losses": 0
            })
            logging.info("Applied manual override for current NLCS vs Brewers")
    
    # Save series data
    with open(series_file, 'w', encoding='utf-8') as f:
        json.dump(playoff_journey, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Saved postseason series data to {series_file}")
    
    # Fetch player stats
    player_ids = get_all_batters()
    all_stats = []
    
    # Fetch stats for all batters
    for player_name, player_id in player_ids.items():
        stats = fetch_postseason_stats(player_id, player_name)
        if stats:
            all_stats.append(stats)
    
    # Filter to top 12 by plate appearances (plateAppearances)
    # Sort by plate appearances descending, then take top 12
    all_stats_with_pa = []
    for player_stats in all_stats:
        stats = player_stats['stats']
        plate_appearances = stats.get('plateAppearances', 0)
        if plate_appearances > 0:  # Only include players with postseason PAs
            player_stats['plate_appearances'] = plate_appearances
            all_stats_with_pa.append(player_stats)
    
    # Sort by plate appearances (descending) and take top 12
    top_12_stats = sorted(all_stats_with_pa, key=lambda x: x['plate_appearances'], reverse=True)[:12]
    
    # Remove the temporary plate_appearances field before saving
    for player_stats in top_12_stats:
        if 'plate_appearances' in player_stats:
            del player_stats['plate_appearances']
    
    # Save to JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(top_12_stats, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Saved postseason stats for top {len(top_12_stats)} players (by plate appearances) to {json_file}")
    
    # Print summary
    print(f"\n=== Dodgers 2025 Postseason Journey (as of Oct 13, 2025) ===")
    for journey in playoff_journey:
        status_icon = "✅" if journey['status'] == "completed" else "🏃" if journey['status'] == "in_progress" else "❓"
        print(f"{status_icon} {journey['round']}: vs {journey['opponent']} - {journey['result']}")
    
    print(f"\n📅 Current Status: NLCS Game 1 vs Milwaukee Brewers starts today")
    print(f"🏆 Last completed series: NLDS vs Philadelphia Phillies (LAD wins 3-1)")
    
    print(f"\n=== Top {len(top_12_stats)} Players by 2025 Postseason Plate Appearances ===")
    for i, player_stats in enumerate(top_12_stats, 1):
        name = player_stats['player_name']
        stats = player_stats['stats']
        avg = stats.get('avg', '.000')
        hr = stats.get('homeRuns', 0)
        rbi = stats.get('rbi', 0)
        pa = stats.get('plateAppearances', 0)
        games = stats.get('gamesPlayed', 0)
        print(f"{i:2d}. {name}: {games}G, {pa} PA, {avg} AVG, {hr} HR, {rbi} RBI")

if __name__ == "__main__":
    main()