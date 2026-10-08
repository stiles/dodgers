#!/usr/bin/env python
"""
Fetch league-wide postseason series results for the playoff bracket.

scripts/28_fetch_postseason_stats.py only tracks the Dodgers' own path through
the postseason. The bracket diagram on the homepage shows all 6 teams per
league, so it needs every series' result (wild card, division, championship,
World Series) regardless of whether the Dodgers are involved.
"""

import json
import logging
import os
from datetime import datetime

import boto3
import pytz
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

CURRENT_SEASON = str(datetime.now().year)
OUTPUT_DIR = "data/postseason"
OUTPUT_FILE = f"{OUTPUT_DIR}/all_teams_postseason_series_{CURRENT_SEASON}.json"
S3_BUCKET = "stilesdata.com"
S3_KEY = f"dodgers/{OUTPUT_FILE}"

ROUND_NAMES = {
    "F": "Wild Card",
    "D": "Division Series",
    "L": "Championship Series",
    "W": "World Series",
}


def get_s3_resource():
    """Create an S3 resource using CI env credentials or the local profile."""
    if os.getenv("GITHUB_ACTIONS") == "true":
        session = boto3.Session(
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name="us-west-1",
        )
    else:
        profile = os.environ.get("AWS_PERSONAL_PROFILE", "haekeo")
        session = boto3.Session(profile_name=profile, region_name="us-west-1")
    return session.resource("s3")


def get_pacific_time() -> str:
    pacific = pytz.timezone("US/Pacific")
    return datetime.now(pacific).isoformat()


def fetch_all_series():
    """Fetch every postseason series group from the MLB Stats API."""
    url = (
        "https://statsapi.mlb.com/api/v1/schedule/postseason/series"
        f"?sportId=1&season={CURRENT_SEASON}&language=en"
        "&hydrate=team,seriesStatus(useOverride=true)&sortBy=gameDate"
    )
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json().get("series", [])


def build_bracket(series_groups):
    """Reduce each series group to the fields the bracket UI needs."""
    series_list = []

    for group in series_groups:
        meta = group.get("series", {})
        game_type = meta.get("gameType")
        round_name = ROUND_NAMES.get(game_type)
        games = group.get("games", [])
        if not round_name or not games:
            continue

        # Games within a series are sorted by date; the last one carries the
        # most current seriesStatus (wins/losses/winner through that game).
        last_game = games[-1]
        teams = last_game.get("teams", {})
        home = teams.get("home", {}).get("team", {})
        away = teams.get("away", {}).get("team", {})
        status = last_game.get("seriesStatus", {})

        winning_team = status.get("winningTeam") or {}
        losing_team = status.get("losingTeam") or {}

        home_league = home.get("league", {}).get("name")
        league = "AL" if home_league == "American League" else "NL" if home_league == "National League" else None

        series_list.append(
            {
                "series_id": meta.get("id"),
                "round": round_name,
                "game_type": game_type,
                "league": league,
                "home_team": home.get("name"),
                "home_team_id": home.get("id"),
                "away_team": away.get("name"),
                "away_team_id": away.get("id"),
                "wins": status.get("wins", 0),
                "losses": status.get("losses", 0),
                "is_over": bool(status.get("isOver")),
                "winner_team": winning_team.get("name"),
                "winner_team_id": winning_team.get("id"),
                "loser_team": losing_team.get("name"),
                "loser_team_id": losing_team.get("id"),
                "description": status.get("shortName") or round_name,
            }
        )

    return series_list


def save_locally(payload: dict):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved all-teams postseason series locally -> {OUTPUT_FILE}")


def save_to_s3(payload: dict):
    try:
        s3 = get_s3_resource()
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        s3.Bucket(S3_BUCKET).put_object(Key=S3_KEY, Body=body, ContentType="application/json")
        logging.info(f"Uploaded all-teams postseason series -> s3://{S3_BUCKET}/{S3_KEY}")
    except Exception as exc:
        logging.error(f"S3 upload failed: {exc}")


def main():
    logging.info(f"Fetching {CURRENT_SEASON} postseason series for all teams")
    series_groups = fetch_all_series()
    series_list = build_bracket(series_groups)

    payload = {
        "season": CURRENT_SEASON,
        "last_updated": get_pacific_time(),
        "series": series_list,
    }

    save_locally(payload)
    save_to_s3(payload)
    logging.info(f"Done. {len(series_list)} series captured.")


if __name__ == "__main__":
    main()
