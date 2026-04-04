#!/usr/bin/env python
"""
Phase-based dataset configuration

Defines which scripts should run in each season phase.
This allows workflows to automatically adjust based on the current phase.
"""

# Dataset/script configuration by phase
PHASE_CONFIG = {
    "regular_season": {
        "description": "Full data refresh during active season",
        "scripts": [
            "scripts/00_fetch_league_standings.py",
            "scripts/02_update_boxscores_archive.py",
            "scripts/03_scrape_league_ranks.py",
            "scripts/04_fetch_process_standings.py",
            "scripts/05_fetch_process_batting.py",
            "scripts/06_fetch_process_pitching.py",
            "scripts/09_build_wins_losses_from_boxscores.py",
            "scripts/10_fetch_process_historic_batting_gamelogs.py",
            "scripts/12_fetch_process_historic_pitching_gamelogs.py",
            "scripts/13_fetch_process_schedule.py",
            "scripts/14_fetch_process_batting_mlb.py",
            "scripts/15_fetch_xwoba.py",
            "scripts/16_fetch_shohei.py",
            "scripts/19_fetch_roster.py",
            "scripts/20_fetch_game_pitches.py",
            "scripts/21_summarize_pitch_data.py",
            "scripts/30_fetch_abs_challenges.py",
            "scripts/11_fetch_process_attendance.py",
            # Projection only during regular season
            "scripts/18_generate_projection.py",
            # Summary aggregates
            "scripts/07_create_toplines_summary.py",
        ],
        "cadence": "multiple_times_daily"
    },
    
    "postseason": {
        "description": "Postseason-focused updates + maintained regular season datasets",
        "scripts": [
            # Postseason-specific
            "scripts/28_fetch_postseason_stats.py",
            # Keep roster/transactions active
            "scripts/19_fetch_roster.py",
            "scripts/26_post_transactions.py",
            # Optionally refresh final regular season snapshots (low frequency)
            "scripts/00_fetch_league_standings.py",
            "scripts/07_create_toplines_summary.py",
        ],
        "cadence": "daily"
    },
    
    "offseason": {
        "description": "Minimal updates: roster, transactions, news",
        "scripts": [
            "scripts/19_fetch_roster.py",
            "scripts/26_post_transactions.py",
            "scripts/24_fetch_news.py",
            # Occasional historical data refresh
            "scripts/08_fetch_process_season_outcomes.py",
            "scripts/10_fetch_process_historic_batting_gamelogs.py",
            "scripts/11_fetch_process_attendance.py",
            "scripts/12_fetch_process_historic_pitching_gamelogs.py",
        ],
        "cadence": "weekly"
    }
}

def get_scripts_for_phase(phase):
    """
    Get list of scripts to run for a given phase
    
    Args:
        phase: 'regular_season', 'postseason', or 'offseason'
    
    Returns:
        list of script paths
    """
    return PHASE_CONFIG.get(phase, {}).get("scripts", [])

def get_phase_description(phase):
    """Get human-readable description of what runs in a phase"""
    return PHASE_CONFIG.get(phase, {}).get("description", "Unknown phase")

def get_phase_cadence(phase):
    """Get recommended run cadence for a phase"""
    return PHASE_CONFIG.get(phase, {}).get("cadence", "daily")

if __name__ == "__main__":
    # Print phase configuration
    for phase, config in PHASE_CONFIG.items():
        print(f"\n{'='*60}")
        print(f"Phase: {phase.upper()}")
        print(f"{'='*60}")
        print(f"Description: {config['description']}")
        print(f"Cadence: {config['cadence']}")
        print(f"\nScripts ({len(config['scripts'])}):")
        for script in config['scripts']:
            print(f"  - {script}")
