import argparse
import json
import os
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

import boto3
from botocore.exceptions import ClientError
import pandas as pd
import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo


DODGERS_TEAM_ID = 119
BUCKET = "stilesdata.com"
ARCHIVE_KEY_JSON = "dodgers/data/standings/dodgers_boxscores.json"
ARCHIVE_KEY_CSV = "dodgers/data/standings/dodgers_boxscores.csv"  # legacy fallback
LOCAL_ARCHIVE_JSON = os.path.join("data", "standings", "dodgers_boxscores.json")
LOCAL_ARCHIVE_CSV = os.path.join("data", "standings", "dodgers_boxscores.csv")


def get_s3_client(profile_name: Optional[str] = None):
    """Return an S3 client with sensible local/CI behavior.

    Priority:
    1) Explicit CLI profile
    2) If running in GitHub Actions, use default chain (env/role)
    3) AWS_PROFILE env var
    4) Local fallback profile 'haekeo'
    """
    if profile_name:
        session = boto3.session.Session(profile_name=profile_name)
        return session.client("s3")

    if os.environ.get("GITHUB_ACTIONS") == "true":
        return boto3.client("s3")

    env_profile = os.environ.get("AWS_PROFILE")
    resolved = env_profile or "haekeo"
    session = boto3.session.Session(profile_name=resolved)
    return session.client("s3")


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def fetch_json(url: str) -> dict:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def find_gamelog_table(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("div.table-savant table")
    for table in tables:
        headers = [th.get_text(strip=True) for th in table.select("thead th")]
        if headers and headers[0] == "Game Date":
            return table
    raise RuntimeError("Could not find game logs table with 'Game Date' header")


def parse_game_log_rows(table: BeautifulSoup) -> pd.DataFrame:
    rows = table.select("tbody tr")
    parsed_rows = []
    for row in rows:
        date_link = row.select_one('td a[href*="gamefeed?gamePk="]')
        if not date_link:
            continue
        href_value = date_link.get("href", "")
        parsed_url = urlparse(href_value)
        query_params = parse_qs(parsed_url.query)
        game_pk = (query_params.get("gamePk") or query_params.get("game_pk") or [None])[0]
        try:
            game_pk_int = int(game_pk) if game_pk is not None else None
        except ValueError:
            game_pk_int = None
        game_date = date_link.get_text(strip=True)

        cells = row.select("td")
        opponent_text = cells[1].get_text(strip=True) if len(cells) > 1 else None

        parsed_rows.append(
            {
                "date": game_date,
                "opponent": opponent_text,
                "game_pk": game_pk_int,
            }
        )
    return pd.DataFrame(parsed_rows)


def get_los_angeles_date_iso() -> str:
    """Return today's date string in America/Los_Angeles as YYYY-MM-DD."""
    la_now = datetime.now(ZoneInfo("America/Los_Angeles"))
    return la_now.strftime("%Y-%m-%d")


def get_dodgers_final_gamepks_for_date(date_iso: str) -> List[int]:
    """Query MLB Stats API schedule for the given local date and return any
    Dodgers gamePk values that are Final.
    """
    url = (
        f"https://statsapi.mlb.com/api/v1/schedule?timeZone=America/Los_Angeles&sportId=1&date={date_iso}"
    )
    try:
        payload = fetch_json(url)
    except Exception:
        return []

    dodgers_pks: List[int] = []
    for day in payload.get("dates", []):
        for game in day.get("games", []):
            teams = game.get("teams", {})
            home_id = teams.get("home", {}).get("team", {}).get("id")
            away_id = teams.get("away", {}).get("team", {}).get("id")
            status = game.get("status", {}).get("detailedState")
            if status == "Final" and (home_id == DODGERS_TEAM_ID or away_id == DODGERS_TEAM_ID):
                try:
                    dodgers_pks.append(int(game.get("gamePk")))
                except (TypeError, ValueError):
                    continue
    return dodgers_pks


def extract_runs_by_inning(linescore_innings: List[dict], side: str) -> List[int]:
    return [int(max(0, inning.get(side, {}).get("runs", 0))) for inning in linescore_innings]


def build_boxscore_row(gamefeed: dict) -> Optional[dict]:
    try:
        sb = gamefeed["scoreboard"]
        linescore = sb["linescore"]
        teams = sb["teams"]

        home = teams["home"]
        away = teams["away"]

        home_runs = int(linescore["teams"]["home"]["runs"])
        away_runs = int(linescore["teams"]["away"]["runs"])
        home_id = int(home["id"]) if isinstance(home, dict) and "id" in home else int(home["team"]["id"]) if "team" in home else None
        away_id = int(away["id"]) if isinstance(away, dict) and "id" in away else int(away["team"]["id"]) if "team" in away else None

        # Normalize name/abbrev fields
        def team_name_fields(t: dict):
            if "name" in t and "abbreviation" in t:
                return t["name"], t["abbreviation"], t.get("teamName") or t.get("clubName")
            team = t.get("team", {})
            return team.get("name"), team.get("abbreviation"), team.get("teamName") or team.get("clubName")

        home_name, home_abbr, home_short = team_name_fields(home)
        away_name, away_abbr, away_short = team_name_fields(away)

        innings = linescore.get("innings", [])
        rbi_home = extract_runs_by_inning(innings, "home")
        rbi_away = extract_runs_by_inning(innings, "away")

        game_pk = int(sb["gamePk"])
        game_date = gamefeed.get("game_date") or gamefeed.get("gameDate")
        status = sb.get("status", {}).get("detailedState")
        is_final = status == "Final"

        dodgers_is_home = home_id == DODGERS_TEAM_ID
        if dodgers_is_home:
            dodgers_runs = home_runs
            opponent_runs = away_runs
            opponent_name = away_name
            opponent_abbr = away_abbr
        else:
            dodgers_runs = away_runs
            opponent_runs = home_runs
            opponent_name = home_name
            opponent_abbr = home_abbr

        winner_abbr = home_abbr if home_runs > away_runs else away_abbr if away_runs > home_runs else None

        venue = linescore.get("teams", {}).get("home", {}).get("team", {}).get("venue") or {}
        if not venue:
            venue = home.get("venue", {})

        return {
            "game_pk": game_pk,
            "date": game_date,
            "home_team_id": home_id,
            "home_team_abbr": home_abbr,
            "home_team_name": home_name,
            "away_team_id": away_id,
            "away_team_abbr": away_abbr,
            "away_team_name": away_name,
            "home_runs": home_runs,
            "away_runs": away_runs,
            "winner": winner_abbr,
            "dodgers_is_home": dodgers_is_home,
            "dodgers_runs": dodgers_runs,
            "opponent_runs": opponent_runs,
            "opponent_name": opponent_name,
            "opponent_abbr": opponent_abbr,
            "diff": dodgers_runs - opponent_runs,
            "runs_by_inning_home": rbi_home,
            "runs_by_inning_away": rbi_away,
            "status": status,
            "is_final": is_final,
            "venue_id": venue.get("id"),
            "venue_name": venue.get("name"),
        }
    except Exception:
        return None


def load_archive(profile_name: Optional[str] = None) -> pd.DataFrame:
    s3 = get_s3_client(profile_name)
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=ARCHIVE_KEY_JSON)
        text = obj["Body"].read().decode("utf-8")
        return pd.DataFrame(json.loads(text))
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "NoSuchKey":
            # Legacy CSV fallback in S3
            try:
                obj = s3.get_object(Bucket=BUCKET, Key=ARCHIVE_KEY_CSV)
                return pd.read_csv(obj["Body"])
            except Exception:
                pass
    except Exception:
        pass
    # Fallback to local archive if S3 is unavailable
    try:
        if os.path.exists(LOCAL_ARCHIVE_JSON):
            with open(LOCAL_ARCHIVE_JSON, "r", encoding="utf-8") as f:
                return pd.DataFrame(json.load(f))
        if os.path.exists(LOCAL_ARCHIVE_CSV):
            return pd.read_csv(LOCAL_ARCHIVE_CSV)
    except Exception:
        pass
    return pd.DataFrame()


def save_archive(df: pd.DataFrame, profile_name: Optional[str] = None) -> None:
    s3 = get_s3_client(profile_name)
    json_bytes = json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2).encode("utf-8")
    try:
        s3.put_object(Bucket=BUCKET, Key=ARCHIVE_KEY_JSON, Body=json_bytes, ContentType="application/json")
        print(f"Uploaded archive -> s3://{BUCKET}/{ARCHIVE_KEY_JSON}")
    except Exception as exc:
        # Write locally as a fallback
        os.makedirs(os.path.dirname(LOCAL_ARCHIVE_JSON), exist_ok=True)
        with open(LOCAL_ARCHIVE_JSON, "wb") as f:
            f.write(json_bytes)
        print(f"S3 upload failed ({exc}). Saved locally -> {LOCAL_ARCHIVE_JSON}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Dodgers boxscore archive from Baseball Savant")
    parser.add_argument(
        "--profile",
        default=os.environ.get("AWS_PROFILE"),
        help="AWS profile to use for S3 (omit on GitHub Actions; locally defaults to 'haekeo')",
    )
    args = parser.parse_args()

    current_year = pd.Timestamp.now().year
    gamelogs_url = (
        f"https://baseballsavant.mlb.com/team/{DODGERS_TEAM_ID}?view=gamelogs&nav=hitting&season={current_year}"
    )
    html = fetch_text(gamelogs_url)
    table = find_gamelog_table(html)
    logs_df = parse_game_log_rows(table)

    archive_df = load_archive(args.profile)
    existing_pks = set(archive_df["game_pk"].astype(int).tolist()) if not archive_df.empty else set()

    new_rows = []
    # Candidate ids from Savant gamelog table
    candidate_pks = set(logs_df["game_pk"].dropna().astype(int).tolist())

    # Augment with same-day Final games from MLB schedule (LA local date)
    la_date = get_los_angeles_date_iso()
    schedule_pks = set(get_dodgers_final_gamepks_for_date(la_date))
    candidate_pks.update(schedule_pks)

    for game_pk in sorted(candidate_pks):
        if game_pk in existing_pks:
            continue
        gf_url = f"https://baseballsavant.mlb.com/gf?game_pk={game_pk}"
        gf = fetch_json(gf_url)
        row = build_boxscore_row(gf)
        if row is not None:
            new_rows.append(row)

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        combined = (
            pd.concat([archive_df, new_df], ignore_index=True)
            .drop_duplicates(subset=["game_pk"], keep="last")
        )
        # Normalize date and sort for convenience
        if "date" in combined.columns:
            combined["date"] = pd.to_datetime(combined["date"]).dt.strftime("%Y-%m-%d")
        combined = combined.sort_values(["date", "game_pk"]).reset_index(drop=True)
        save_archive(combined, args.profile)
        print(f"Archive now contains {len(combined)} games")
    else:
        print("No new games to add. Archive unchanged.")


if __name__ == "__main__":
    main()


