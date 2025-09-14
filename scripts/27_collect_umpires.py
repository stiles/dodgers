#!/usr/bin/env python
# coding: utf-8

"""
Collect season home plate umpires for all Dodgers games and save to JSON + S3.

Data source:
- MLB StatsAPI live feed: https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live

Output:
- data/pitches/dodgers_umpires_{year}.json
- s3://stilesdata.com/dodgers/data/pitches/dodgers_umpires_{year}.json

Idempotent: Reuses existing output and appends only missing game_pks.
Also reuses local Savant gamefeeds (data/gamefeeds/*.json) to seed game_pks.
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import requests
import pandas as pd
import boto3


DODGERS_TEAM_ID = 119
SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
LIVE_FEED_URL_TMPL = "https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_GAMEFEEDS_DIR = os.path.join(BASE_DIR, "data", "gamefeeds")
LOCAL_OUT_DIR = os.path.join(BASE_DIR, "data", "pitches")

YEAR = pd.Timestamp.now().year
LOCAL_OUT_PATH = os.path.join(LOCAL_OUT_DIR, f"dodgers_umpires_{YEAR}.json")

S3_BUCKET = "stilesdata.com"
S3_KEY = f"dodgers/data/pitches/dodgers_umpires_{YEAR}.json"


def get_session():
    """Return a boto3 session consistent with the repo's conventions."""
    is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
    if is_github_actions:
        aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        return boto3.Session(
            aws_access_key_id=aws_key_id,
            aws_secret_access_key=aws_secret_key,
            region_name="us-west-1",
        )
    # Local default profile fallback
    return boto3.Session(profile_name=os.environ.get("AWS_PERSONAL_PROFILE", "haekeo"), region_name="us-west-1")


def find_local_gamepks(gamefeeds_dir: str) -> List[int]:
    game_pks: List[int] = []
    if not os.path.isdir(gamefeeds_dir):
        return game_pks
    for name in os.listdir(gamefeeds_dir):
        if re.fullmatch(r"\d+\.json", name):
            try:
                game_pks.append(int(name.split(".")[0]))
            except Exception:
                continue
    return sorted(set(game_pks))


def fetch_season_schedule_gamepks(year: int) -> List[Tuple[int, str]]:
    """Return list of (gamePk, date_iso) for all Dodgers games in the given year."""
    params = {
        "sportId": 1,
        "teamId": DODGERS_TEAM_ID,
        "startDate": f"{year}-03-01",
        "endDate": f"{year}-11-30",
    }
    resp = requests.get(SCHEDULE_URL, params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    out: List[Tuple[int, str]] = []
    for day in payload.get("dates", []):
        date_iso = day.get("date")
        for g in day.get("games", []):
            try:
                gpk = int(g.get("gamePk"))
            except Exception:
                continue
            out.append((gpk, date_iso))
    # Dedupe with preference for first seen
    seen = set()
    result: List[Tuple[int, str]] = []
    for gpk, d in out:
        if gpk not in seen:
            seen.add(gpk)
            result.append((gpk, d))
    return result


def load_existing_output(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return pd.DataFrame(json.load(f))
        except Exception:
            pass
    return pd.DataFrame(columns=["game_pk", "date", "ump_id", "ump_name"])  # schema


def fetch_home_plate_umpire(game_pk: int) -> Optional[Dict]:
    url = LIVE_FEED_URL_TMPL.format(game_pk=game_pk)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        officials = (
            payload.get("liveData", {}).get("boxscore", {}).get("officials", [])
        )
        for off in officials:
            if str(off.get("officialType", "")).lower() == "home plate":
                official = off.get("official", {})
                return {"ump_id": official.get("id"), "ump_name": official.get("fullName")}
    except Exception:
        return None
    return None


def main() -> None:
    os.makedirs(LOCAL_OUT_DIR, exist_ok=True)

    # Start with existing rows to keep idempotent behavior
    existing_df = load_existing_output(LOCAL_OUT_PATH)
    existing_gpk = set(existing_df.get("game_pk", pd.Series([], dtype=int)).astype(int).tolist())

    # Collect candidate game_pks
    local_gpk = find_local_gamepks(LOCAL_GAMEFEEDS_DIR)
    sched = fetch_season_schedule_gamepks(YEAR)
    sched_map: Dict[int, str] = {gpk: date for gpk, date in sched}
    union_gpks = sorted(set(local_gpk).union(set(sched_map.keys())))

    new_rows: List[Dict] = []
    pending: List[int] = []

    for gpk in union_gpks:
        if gpk in existing_gpk:
            continue
        ump = fetch_home_plate_umpire(gpk)
        if ump is None:
            pending.append(gpk)
            continue
        new_rows.append({
            "game_pk": int(gpk),
            "date": sched_map.get(gpk),
            "ump_id": ump.get("ump_id"),
            "ump_name": ump.get("ump_name"),
        })

    if new_rows:
        add_df = pd.DataFrame(new_rows)
        combined = (
            pd.concat([existing_df, add_df], ignore_index=True)
            .drop_duplicates(subset=["game_pk"], keep="first")
            .sort_values(["date", "game_pk"], na_position="last")
            .reset_index(drop=True)
        )
    else:
        combined = existing_df

    # Write locally
    with open(LOCAL_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(combined.to_dict(orient="records"), f, indent=2)
    print(f"Saved umpires -> {LOCAL_OUT_PATH} (added {len(new_rows)}, pending {len(pending)})")

    # Upload to S3
    try:
        session = get_session()
        s3 = session.resource("s3")
        payload = json.dumps(combined.to_dict(orient="records"), ensure_ascii=False, indent=2).encode("utf-8")
        s3.Bucket(S3_BUCKET).put_object(Key=S3_KEY, Body=payload, ContentType="application/json")
        print(f"Uploaded -> s3://{S3_BUCKET}/{S3_KEY}")
    except Exception as exc:
        print(f"S3 upload failed ({exc}). Using local file only.")

    if pending:
        # Print a small note to retry soon; often games not yet final
        print(f"Pending (no officials yet or unavailable): {len(pending)} games. Example: {pending[:5]}")


if __name__ == "__main__":
    main()


