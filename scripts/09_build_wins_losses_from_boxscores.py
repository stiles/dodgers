import argparse
import json
import os
from typing import Optional

import boto3
import pandas as pd


BUCKET = "stilesdata.com"
BOXES_KEY_JSON = "dodgers/data/standings/dodgers_boxscores.json"
BOXES_KEY_CSV = "dodgers/data/standings/dodgers_boxscores.csv"
LOCAL_BOXES_JSON = os.path.join("data", "standings", "dodgers_boxscores.json")
LOCAL_BOXES_CSV = os.path.join("data", "standings", "dodgers_boxscores.csv")

OUT_KEY_JSON = "dodgers/data/standings/dodgers_wins_losses_current.json"
LOCAL_OUT_JSON = os.path.join("data", "standings", "dodgers_wins_losses_current.json")


def get_s3_client(profile_name: Optional[str]) -> boto3.client:
    # Priority:
    # 1) Explicit CLI profile
    # 2) If running in GitHub Actions, use default chain (env/role)
    # 3) AWS_PROFILE env var
    # 4) Local fallback profile 'haekeo'
    if profile_name:
        session = boto3.session.Session(profile_name=profile_name)
        return session.client("s3")

    if os.environ.get("GITHUB_ACTIONS") == "true":
        return boto3.client("s3")

    env_profile = os.environ.get("AWS_PROFILE")
    resolved = env_profile or "haekeo"
    session = boto3.session.Session(profile_name=resolved)
    return session.client("s3")


def load_boxscores(profile_name: Optional[str]) -> pd.DataFrame:
    # Prefer S3 JSON
    try:
        s3 = get_s3_client(profile_name)
        obj = s3.get_object(Bucket=BUCKET, Key=BOXES_KEY_JSON)
        text = obj["Body"].read().decode("utf-8")
        return pd.DataFrame(json.loads(text))
    except Exception:
        pass

    # Fallback S3 CSV
    try:
        s3 = get_s3_client(profile_name)
        obj = s3.get_object(Bucket=BUCKET, Key=BOXES_KEY_CSV)
        return pd.read_csv(obj["Body"])
    except Exception:
        pass

    # Local JSON
    if os.path.exists(LOCAL_BOXES_JSON):
        with open(LOCAL_BOXES_JSON, "r", encoding="utf-8") as f:
            return pd.DataFrame(json.load(f))

    # Local CSV
    if os.path.exists(LOCAL_BOXES_CSV):
        return pd.read_csv(LOCAL_BOXES_CSV)

    raise FileNotFoundError("Boxscores archive not found in S3 or local.")


def build_wins_losses(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Only include final games
    if "is_final" in df.columns:
        df = df[df["is_final"] == True]

    # Normalize and sort by date
    df["game_date"] = pd.to_datetime(df.get("date", df.get("game_date")))
    df = df.sort_values("game_date")
    
    # Filter out exhibition/spring training games
    # Method 1: Exclude games against Angels (Freeway Series exhibitions)
    # Method 2: Only include games from April onwards (regular season typically starts in April)
    # Method 3: Exclude games with gaps > 3 days early in season (likely exhibitions)
    
    # For now, use a combination approach:
    # 1. Exclude Angels games in March (Freeway Series exhibitions)
    # 2. Could add other heuristics in the future
    
    march_angels_games = (
        (df["game_date"].dt.month == 3) & 
        (df["opponent_name"].str.contains("Angels", na=False))
    )
    df = df[~march_angels_games]
    
    # Alternative approach for future: only include games from regular season start
    # Uncomment and adjust if needed:
    # regular_season_start = pd.Timestamp(f"{df['game_date'].dt.year.iloc[0]}-03-20")
    # df = df[df["game_date"] >= regular_season_start]

    # Compute fields
    df["r"] = df["dodgers_runs"].astype(int)
    df["ra"] = df["opponent_runs"].astype(int)
    df["run_diff"] = df["r"] - df["ra"]
    df["result"] = pd.Series(
        ["W" if v > 0 else ("L" if v < 0 else "T") for v in df["run_diff"].tolist()], index=df.index
    )
    df["gm"] = range(1, len(df) + 1)
    df["game_date"] = df["game_date"].dt.strftime("%Y-%m-%d")

    return df[["gm", "game_date", "result", "r", "ra", "run_diff"]].reset_index(drop=True)


def save_json(df: pd.DataFrame, profile_name: Optional[str]) -> None:
    # Local
    os.makedirs(os.path.dirname(LOCAL_OUT_JSON), exist_ok=True)
    with open(LOCAL_OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
    print(f"Saved locally -> {LOCAL_OUT_JSON}")

    # S3
    try:
        s3 = get_s3_client(profile_name)
        payload = json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2).encode("utf-8")
        s3.put_object(Bucket=BUCKET, Key=OUT_KEY_JSON, Body=payload, ContentType="application/json")
        print(f"Uploaded -> s3://{BUCKET}/{OUT_KEY_JSON}")
    except Exception as exc:
        print(f"S3 upload failed ({exc}). Using local file only.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build wins/losses JSON from Savant boxscores archive")
    parser.add_argument(
        "--profile",
        default=os.environ.get("AWS_PROFILE"),
        help="AWS profile for S3 (omit on GitHub Actions; locally defaults to 'haekeo')",
    )
    args = parser.parse_args()

    box_df = load_boxscores(args.profile)
    wl_df = build_wins_losses(box_df)
    save_json(wl_df, args.profile)


if __name__ == "__main__":
    main()


