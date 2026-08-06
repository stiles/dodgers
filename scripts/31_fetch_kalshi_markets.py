#!/usr/bin/env python
# coding: utf-8

"""
Kalshi prediction markets for the Dodgers.

Collects daily implied-probability time series from Kalshi for:
  - Dodgers to win the World Series (KXMLB-26-LAD)
  - NL MVP race, focused on the leading contenders (Dodgers highlighted)

Implied probability is Kalshi's contract price in dollars (e.g. 0.38 = 38%),
which reflects traders' bets rather than a traditional statistical forecast.

Outputs JSON to data/markets/ locally and uploads to S3 (stilesdata.com).
"""

import os
import json
import logging
from datetime import datetime, timezone

import boto3
import requests
import pytz

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BUCKET = "stilesdata.com"
S3_PREFIX = "dodgers/data/markets"
LOCAL_DIR = "data/markets"

# Kalshi endpoints
CANDLES_URL = (
    "https://external-api.kalshi.com/trade-api/v2/series/{series}/markets/{market}/candlesticks"
)
EVENT_URL = "https://api.elections.kalshi.com/v1/events/{event}"
MARKET_URL = "https://api.elections.kalshi.com/v1/cached/markets_by_ticker/{market}"

# Market identifiers (2026 season)
WS_SERIES = "KXMLB"
WS_MARKET = "KXMLB-26-LAD"
MVP_SERIES = "KXMLBNLMVP"
MVP_EVENT = "KXMLBNLMVP-26"

# Daily candlesticks (1440 minutes). Start at Jan 1 of the season year to trim
# the thin, volatile opening prints from when these 2026 markets first listed in
# late 2025. Update alongside the "-26" tickers when the season rolls over.
PERIOD_INTERVAL = 1440
START_TS = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())

# Only chart contenders with a meaningful implied probability, but always
# keep Dodgers so the team angle is preserved.
MIN_PRICE = 0.05
MAX_CANDIDATES = 6

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


def get_s3_resource():
    """Get S3 resource with environment-based credentials."""
    if os.getenv("GITHUB_ACTIONS") == "true":
        session = boto3.Session(
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name="us-west-1",
        )
    else:
        profile = os.environ.get("AWS_PROFILE", "haekeo")
        session = boto3.Session(profile_name=profile, region_name="us-west-1")
    return session.resource("s3")


def get_pacific_time():
    """Return current Pacific time as an ISO string."""
    return datetime.now(pytz.timezone("US/Pacific")).isoformat()


def _to_float(value):
    """Parse a dollar/price string or number into a float, or None."""
    if value in (None, ""):
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def fetch_candlesticks(series, market):
    """Fetch daily candlesticks and return a clean [{date, price}] series."""
    end_ts = int(datetime.now(timezone.utc).timestamp())
    url = CANDLES_URL.format(series=series, market=market)
    params = {"period_interval": PERIOD_INTERVAL, "start_ts": START_TS, "end_ts": end_ts}

    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    candles = resp.json().get("candlesticks", [])

    series_out = []
    for candle in candles:
        ts = candle.get("end_period_ts")
        price_block = candle.get("price", {}) or {}
        # Prefer the day's closing trade price; fall back to mean, then previous.
        price = (
            _to_float(price_block.get("close_dollars"))
            or _to_float(price_block.get("mean_dollars"))
            or _to_float(price_block.get("previous_dollars"))
        )
        if ts is None or price is None:
            continue
        # end_period_ts marks the end of the daily period; label it by that date.
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        series_out.append({"date": date, "price": price})

    logging.info(f"Fetched {len(series_out)} daily points for {market}")
    return series_out


def fetch_world_series():
    """Build the World Series odds payload."""
    series = fetch_candlesticks(WS_SERIES, WS_MARKET)

    resp = requests.get(MARKET_URL.format(market=WS_MARKET), headers=HEADERS, timeout=30)
    resp.raise_for_status()
    market = resp.json().get("market", {}) or {}

    current = {
        "price": _to_float(market.get("last_price_dollars")),
        "yes_bid": _to_float(market.get("yes_bid_dollars")),
        "yes_ask": _to_float(market.get("yes_ask_dollars")),
        "previous_day": _to_float(market.get("previous_day_price_dollars")),
        "previous_week": _to_float(market.get("previous_week_price_dollars")),
        "volume": _to_float(market.get("volume_fp")),
        "open_interest": _to_float(market.get("open_interest_fp")),
    }

    return {
        "title": "Dodgers to win the 2026 World Series",
        "ticker": WS_MARKET,
        "source": "kalshi",
        "last_updated": get_pacific_time(),
        "current": current,
        "series": series,
    }


def fetch_nl_mvp():
    """Build the NL MVP payload for the leading contenders."""
    resp = requests.get(EVENT_URL.format(event=MVP_EVENT), headers=HEADERS, timeout=30)
    resp.raise_for_status()
    markets = resp.json().get("event", {}).get("markets", []) or []

    all_markets = []
    for market in markets:
        player = market.get("name") or market.get("yes_sub_title")
        ticker = market.get("ticker_name")
        if not player or not ticker:
            continue
        if "tie" in player.lower() or "co-winner" in player.lower():
            continue

        team = (market.get("sub_title") or "").replace("::", "").strip()
        price = _to_float(market.get("last_price_dollars"))
        if price is None:
            continue

        all_markets.append(
            {
                "ticker": ticker,
                "player": player,
                "team": team,
                "is_dodger": "Los Angeles" in team,
                "current": {
                    "price": price,
                    "yes_bid": _to_float(market.get("yes_bid_dollars")),
                    "yes_ask": _to_float(market.get("yes_ask_dollars")),
                    "previous_day": _to_float(market.get("previous_day_price_dollars")),
                    "previous_week": _to_float(market.get("previous_week_price_dollars")),
                },
            }
        )

    all_markets.sort(key=lambda c: c["current"]["price"] or 0, reverse=True)

    # Chart the meaningful contenders; avoid a wall of flat 1% lines.
    contenders = [c for c in all_markets if (c["current"]["price"] or 0) >= MIN_PRICE][:MAX_CANDIDATES]

    # If no Dodger is among the leaders, add the top Dodger for context.
    if not any(c["is_dodger"] for c in contenders):
        top_dodger = next((c for c in all_markets if c["is_dodger"]), None)
        if top_dodger:
            contenders.append(top_dodger)

    for contender in contenders:
        contender["series"] = fetch_candlesticks(MVP_SERIES, contender["ticker"])

    return {
        "title": "NL MVP odds",
        "event_ticker": MVP_EVENT,
        "source": "kalshi",
        "last_updated": get_pacific_time(),
        "candidates": contenders,
    }


def save_json(payload, name):
    """Save payload locally and upload to S3."""
    os.makedirs(LOCAL_DIR, exist_ok=True)
    local_path = os.path.join(LOCAL_DIR, f"{name}.json")
    with open(local_path, "w") as f:
        json.dump(payload, f, indent=2)
    logging.info(f"Saved locally: {local_path}")

    try:
        s3 = get_s3_resource()
        s3.Bucket(BUCKET).put_object(
            Key=f"{S3_PREFIX}/{name}.json",
            Body=json.dumps(payload, indent=2),
            ContentType="application/json",
        )
        logging.info(f"Uploaded to s3://{BUCKET}/{S3_PREFIX}/{name}.json")
    except Exception as e:
        logging.error(f"Failed to upload {name} to S3: {e}")


def main():
    logging.info("Fetching Kalshi prediction markets for the Dodgers")

    world_series = fetch_world_series()
    save_json(world_series, "dodgers_kalshi_world_series")

    nl_mvp = fetch_nl_mvp()
    save_json(nl_mvp, "dodgers_kalshi_nl_mvp")

    ws_current = world_series["current"]["price"]
    logging.info("Kalshi markets complete!")
    print("\nPrediction markets summary:")
    if ws_current is not None:
        print(f"  World Series: {ws_current * 100:.0f}% ({len(world_series['series'])} days)")
    for c in nl_mvp["candidates"]:
        flag = " (LAD)" if c["is_dodger"] else ""
        print(f"  MVP {c['player']}{flag}: {(c['current']['price'] or 0) * 100:.0f}%")


if __name__ == "__main__":
    main()
