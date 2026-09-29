import os
import requests
import pandas as pd
import json
import logging
import boto3
from datetime import datetime
from dateutil import parser
import pytz

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# We'll fetch all batters (non-pitchers) and filter to top 12 by plate appearances

CURRENT_SEASON = str(datetime.now().year)

# Output files
output_dir = "data/postseason"
json_file = f"{output_dir}/dodgers_postseason_stats_{CURRENT_SEASON}.json"
series_file = f"{output_dir}/dodgers_postseason_series_{CURRENT_SEASON}.json"

is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
aws_region = "us-west-1"
s3_bucket_name = "stilesdata.com"


def get_s3_resource():
    """Create an S3 resource using CI env credentials or the local profile."""
    if is_github_actions:
        session = boto3.Session(
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=aws_region,
        )
    else:
        profile_name = os.environ.get("AWS_PERSONAL_PROFILE", "haekeo")
        session = boto3.Session(profile_name=profile_name, region_name=aws_region)
    return session.resource("s3")


def upload_to_s3(local_path):
    """Publish a local postseason file to the S3 path the manifest points at."""
    if not os.path.exists(local_path):
        logging.warning(f"Local file {local_path} not found. Skipping S3 upload.")
        return

    s3_key = f"dodgers/{local_path.replace(os.sep, '/')}"
    try:
        get_s3_resource().Bucket(s3_bucket_name).upload_file(local_path, s3_key)
        logging.info(f"Uploaded {local_path} to S3 at '{s3_key}'")
    except Exception as e:
        logging.error(f"Failed to upload {local_path} to S3: {e}")

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

def get_next_game_info(series_data):
    """Get information about the next upcoming game"""
    next_game_info = None
    
    # Look for the current series (in_progress)
    current_series = None
    for series in series_data:
        if not series.get('is_over', True):
            current_series = series
            break
    
    if current_series:
        # Try to get more detailed game info from API
        try:
            # Get current series schedule to find next game
            current_year = datetime.now().year
            url = f"https://statsapi.mlb.com/api/v1/schedule/postseason?sportId=1&season={current_year}&hydrate=team,venue,linescore&language=en"
            
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if 'dates' in data:
                for date_entry in data['dates']:
                    for game in date_entry.get('games', []):
                        home_team = game.get('teams', {}).get('home', {}).get('team', {}).get('name', '')
                        away_team = game.get('teams', {}).get('away', {}).get('team', {}).get('name', '')
                        
                        if 'Los Angeles Dodgers' in [home_team, away_team]:
                            game_status = game.get('status', {}).get('detailedState', '')
                            
                            # Look for upcoming games (Scheduled, Pre-Game, etc.)
                            if game_status in ['Scheduled', 'Pre-Game', 'Warmup']:
                                game_datetime = game.get('gameDate', '')
                                venue_name = game.get('venue', {}).get('name', '')
                                
                                if game_datetime:
                                    # Parse the game time and convert to PT
                                    try:
                                        game_dt = parser.parse(game_datetime)
                                        pt_tz = pytz.timezone('US/Pacific')
                                        game_pt = game_dt.astimezone(pt_tz)
                                        start_tbd = game.get('status', {}).get('startTimeTBD', False)
                                        am_pm = game_pt.strftime('%p').lower().replace('m', '.m.')
                                        
                                        next_game_info = {
                                            'opponent': away_team if home_team == 'Los Angeles Dodgers' else home_team,
                                            'venue': venue_name,
                                            'datetime_pt': game_pt,
                                            'start_time_tbd': start_tbd,
                                            'time_pt': 'time TBA' if start_tbd else f"{game_pt.strftime('%-I:%M')} {am_pm} PT",
                                            'day': game_pt.strftime('%A'),
                                            'is_home': home_team == 'Los Angeles Dodgers'
                                        }
                                        
                                        logging.info(f"Found next game: {next_game_info}")
                                        return next_game_info
                                        
                                    except Exception as e:
                                        logging.warning(f"Error parsing game time: {e}")
                                        
        except Exception as e:
            logging.warning(f"Error fetching detailed game info: {e}")
    
    return next_game_info


def fetch_postseason_series():
    """Fetch postseason series data from MLB API"""
    # Try different parameter combinations to get the most current data
    urls = [
        # Most comprehensive - all postseason game types with current season
        f"https://statsapi.mlb.com/api/v1/schedule/postseason/series?sportId=1&season={CURRENT_SEASON}&language=en&timeZone=America/New_York&hydrate=team,linescore(matchup),flags,statusFlags,broadcasts(all),venue(location),decisions,game(content(media(epg),summary),tickets),seriesStatus(useOverride=true)&sortBy=gameDate",
        # Alternative with specific game types
        f"https://statsapi.mlb.com/api/v1/schedule/postseason/series?sportId=1&gameType=D&gameType=F&gameType=L&gameType=W&season={CURRENT_SEASON}&language=en&hydrate=team,seriesStatus(useOverride=true)&sortBy=gameDate",
        # Simpler call to avoid potential caching issues
        f"https://statsapi.mlb.com/api/v1/schedule/postseason?sportId=1&season={CURRENT_SEASON}&hydrate=team,seriesStatus&language=en"
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
        
        # Extract current-season postseason stats
        season_stats = None
        if 'stats' in data and len(data['stats']) > 0:
            for stat_group in data['stats']:
                if stat_group['type']['displayName'] == 'yearByYear':
                    for split in stat_group['splits']:
                        if split['season'] == CURRENT_SEASON:
                            season_stats = split['stat']
                            break
                    break
        
        if season_stats:
            logging.info(f"Found {CURRENT_SEASON} postseason stats for {player_name}")
            return {
                'player_id': player_id,
                'player_name': player_name,
                'season': CURRENT_SEASON,
                'stats': season_stats
            }
        else:
            logging.warning(f"No {CURRENT_SEASON} postseason stats found for {player_name}")
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
    
    # Get next game info with proper time zone handling
    next_game = get_next_game_info(series_data)
    
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
    
    # Note: Manual overrides removed to allow live API data to flow through
    # The API now correctly provides real-time series status
    logging.info("Using live API data without manual overrides")
    
    # Save series data
    with open(series_file, 'w', encoding='utf-8') as f:
        json.dump(playoff_journey, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Saved postseason series data to {series_file}")
    upload_to_s3(series_file)
    
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
    upload_to_s3(json_file)
    
    # Print summary
    print(f"\n=== Dodgers {CURRENT_SEASON} Postseason Journey ===")
    for journey in playoff_journey:
        status_icon = "✅" if journey['status'] == "completed" else "🏃" if journey['status'] == "in_progress" else "❓"
        print(f"{status_icon} {journey['round']}: vs {journey['opponent']} - {journey['result']}")
    
    # Enhanced current status with context
    current_series = None
    previous_series = None
    
    # Find current and most recent completed series
    for journey in playoff_journey:
        if journey['status'] == 'in_progress':
            current_series = journey
        elif journey['status'] == 'completed':
            if previous_series is None or journey['round'] in ['World Series', 'NLCS', 'NLDS', 'Wild Card']:
                # Get the most recent completed series
                round_order = {'Wild Card': 1, 'NLDS': 2, 'NLCS': 3, 'World Series': 4}
                if previous_series is None or round_order.get(journey['round'], 0) > round_order.get(previous_series['round'], 0):
                    previous_series = journey
    
    if next_game:
        game_time = next_game['time_pt']
        game_day = next_game['day']
        venue = next_game['venue']
        current_opponent = next_game['opponent']
        current_round = current_series['round'] if current_series else 'Postseason'
        when = f"{game_day} ({game_time})" if next_game.get('start_time_tbd') else f"{game_day} at {game_time}"
        
        print(f"\n📅 Current Status: {current_round} vs {current_opponent} starts {when}")
        print(f"🏟️ Venue: {venue}")
        
        if previous_series and previous_series['opponent'] != current_opponent:
            print(f"🏆 Last completed series: {previous_series['round']} vs {previous_series['opponent']} ({previous_series['result']})")
    else:
        # Fallback if we can't get detailed game info
        if current_series:
            print(f"\n📅 Current Status: {current_series['round']} vs {current_series['opponent']} - {current_series['result']}")
        if previous_series:
            print(f"🏆 Last completed series: {previous_series['round']} vs {previous_series['opponent']} ({previous_series['result']})")
    
    print(f"\n=== Top {len(top_12_stats)} Players by {CURRENT_SEASON} Postseason Plate Appearances ===")
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