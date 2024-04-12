#!/usr/bin/env python
# coding: utf-8

import os
import pandas as pd
import altair as alt
import altair_stiles as altstiles

# Configuring Altair and the data display size
alt.data_transformers.disable_max_rows()
alt.themes.register("stiles", altstiles.theme)
alt.themes.enable("stiles")

def load_data():
    """Load historical standings data from a parquet file."""
    df = pd.read_parquet("https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.parquet")
    return df

def latest_game_number(df):
    """Return the latest game number."""
    return df['gm'].max()

def filter_data_by_game_number(df, game_number):
    """Limit data to latest game number this season."""
    return df[df['gm'] <= game_number].copy()

def historical_chart(df):
    """Generate historical standings line chart."""
    past_chart = (
        alt.Chart(df[df['year'] != 2024])
        .mark_line(size=0.8, color="#bbbbbb")
        .encode(
            x=alt.X("gm:Q", title="Game number in season", scale=alt.Scale(domain=[0, 162])),
            y=alt.Y("gb:Q", title="Games ahead/back by game"),
            tooltip=['year', 'gm', 'gb']
        )
    )

    current_chart = (
        alt.Chart(df[df['year'] == 2024])
        .mark_line(size=2, color="#005A9C")
        .encode(x="gm:Q", y="gb:Q", tooltip=['gm', 'gb'])
    )

    hline = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="black", strokeWidth=0.5).encode(y="y")

    return (past_chart + current_chart + hline).properties(
        width=800, height=400, title="LA Dodgers Historical Standings"
    )

def runs_chart(df):
    """Generate a chart for runs scored to this point."""
    df['r'] = df['r'].astype(int)
    runs_so_far = df.groupby('year')['r'].sum().reset_index(name='runs_to_date').sort_values('year', ascending=False)
    runs_this_season = runs_so_far.query("year == year.max()")['runs_to_date'].iloc[0]

    base = (
        alt.Chart(runs_so_far)
        .mark_bar()
        .encode(
            x=alt.X("runs_to_date:Q", title=f"Runs by game no. {latest_game_number(df)}"),
            y=alt.Y("year:O", sort='-x'),
            color=alt.condition(f"datum.year == 2024", alt.value("steelblue"), alt.value("lightgray"))
        )
        .properties(width=650, height=400, title=f"Dodgers Historical Offense: Total runs through game {latest_game_number(df)}")
    )

    text = base.mark_text(align='left', dx=5).encode(text='runs_to_date:Q')

    return (base + text)

def main():
    df = load_data()
    game_number = latest_game_number(df)
    limited_df = filter_data_by_game_number(df, game_number)
    
    chart1 = historical_chart(limited_df)
    chart1.save("../visuals/standings.png")
    
    chart2 = runs_chart(limited_df)
    chart1.save("../visuals/runs.png")

if __name__ == "__main__":
    main()
