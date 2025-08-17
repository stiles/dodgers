import json
import os
from urllib.parse import urlparse, parse_qs

import pandas as pd
import requests
from bs4 import BeautifulSoup


CURRENT_YEAR = pd.Timestamp.now().year
GAME_LOGS_URL = (
    f"https://baseballsavant.mlb.com/team/119?view=gamelogs&nav=hitting&season={CURRENT_YEAR}"
)


def fetch_game_logs_html(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def find_gamelog_table(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("div.table-savant table")
    for table in tables:
        header_cells = [th.get_text(strip=True) for th in table.select("thead th")]
        if header_cells and header_cells[0] == "Game Date":
            return table
    raise RuntimeError("Could not find game logs table with 'Game Date' header")


def parse_game_rows(table: BeautifulSoup) -> pd.DataFrame:
    rows = table.select("tbody tr")
    parsed_rows = []
    for row in rows:
        date_link = row.select_one('td a[href*="gamefeed?gamePk="]')
        if not date_link:
            # Skip rows without a game link
            continue
        href_value = date_link.get("href", "")
        parsed_url = urlparse(href_value)
        query_params = parse_qs(parsed_url.query)
        game_pk = (
            (query_params.get("gamePk") or query_params.get("game_pk") or [None])[0]
        )
        game_date = date_link.get_text(strip=True)

        cells = row.select("td")
        opponent_text = cells[1].get_text(strip=True) if len(cells) > 1 else None

        try:
            game_pk_int = int(game_pk) if game_pk is not None else None
        except ValueError:
            game_pk_int = None

        parsed_rows.append(
            {
                "date": game_date,
                "opponent": opponent_text,
                "game_pk": game_pk_int,
            }
        )

    return pd.DataFrame(parsed_rows)


def fetch_and_save_gamefeed(game_pk: int, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    url = f"https://baseballsavant.mlb.com/gf?game_pk={game_pk}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    out_path = os.path.join(out_dir, f"{game_pk}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return out_path


def main() -> None:
    html = fetch_game_logs_html(GAME_LOGS_URL)
    table = find_gamelog_table(html)
    logs_df = parse_game_rows(table)

    print(logs_df.head())

    # Save and fetch detailed gamefeed JSON for each game id we found
    gamefeeds_dir = os.path.join("data", "gamefeeds")
    for game_pk in logs_df["game_pk"].dropna().astype(int).tolist():
        try:
            out_file = fetch_and_save_gamefeed(game_pk, gamefeeds_dir)
            print(f"Saved gamefeed {game_pk} -> {out_file}")
        except Exception as exc:
            print(f"Failed to fetch gamefeed for {game_pk}: {exc}")


if __name__ == "__main__":
    main()


