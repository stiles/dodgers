#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd
import requests

def fetch_data(url):
    """Fetches data from a URL and returns a pandas DataFrame."""
    with requests.Session() as session:
        response = session.get(url)
        response.raise_for_status()  # Will halt the script if the request failed
        return pd.read_html(response.text)[0]

def clean_names(df):
    """Cleans player names and extracts batting stance."""
    df['name'] = df['name'].str.split(' (', expand=True)[0].str.strip()
    conditions = [
        (df['name'].str.endswith('*'), 'Left'),
        (df['name'].str.endswith('#'), 'Both'),
        (df['name'].str.endswith('?'), 'Unknown'),
        (True, 'Right')
    ]
    df['bats'] = np.select([cond for cond, _ in conditions], [name for _, name in conditions], default='Right')
    df['name'] = df['name'].str.rstrip('*#?')
    return df

def process_player_totals(url, year):
    """Processes player totals."""
    df = fetch_data(url).query("~Rk.isna() and Rk != 'Rk'").dropna(thresh=7)
    df.columns = df.columns.str.lower().str.replace("+", "_plus")
    df = clean_names(df.assign(season=year))
    numeric_cols = df.columns[df.columns.str.contains("^(g|pa|ab|r|h|2b|3b|hr|rbi|sb|cs|bb|so|tb|gdp|hbp|sh|sf|ibb|ba|obp|slg|ops|ops_plus)$")]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
    return df

def main():
    year = pd.to_datetime("now").year
    url = f"https://www.baseball-reference.com/teams/LAD/{year}-batting.shtml"

    player_totals_df = process_player_totals(url, year)
    team_totals_df, team_ranks_df = process_team_data(url, year)

    # Combine current season data with historical archive
    archive_url = "https://stilesdata.com/dodgers/data/batting/archive/dodgers_player_batting_statistics_1958_2023.parquet"
    player_archive_df = pd.read_parquet(archive_url)
    players_full_df = pd.concat([player_totals_df, player_archive_df]).reset_index(drop=True)

    # Save dataframes in multiple formats
    save_dataframe(players_full_df, f"../data/batting/dodgers_player_batting_{year}_present", ["csv", "json", "parquet"])

if __name__ == "__main__":
    main()
