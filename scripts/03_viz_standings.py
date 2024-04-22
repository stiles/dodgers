#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers standings, 1958-2024
This notebook visusalizes the team's historic standings with data from Baseball Reference.
URL: https://www.baseball-reference.com/teams/LAD/2024-schedule-scores.shtml
"""

import os
import pandas as pd
import altair as alt
import altair_stiles as altstiles

alt.data_transformers.disable_max_rows()
alt.themes.register("stiles", altstiles.theme)
alt.themes.enable("stiles")

"""
Fetch
"""

# Read historical archive, compiled in notebooks `00` and `01`, from S3

df = pd.read_parquet(
    "https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.parquet"
)

game_number = df.query("game_date == game_date.max()")["gm"].iloc[0]


"""
Standings chart
"""

font = "Roboto"

# Limit dataframe to latest game number this season

limit_df = df.query(f"gm <= {game_number}").copy()


past = (
    alt.Chart(df.query("year != 2024"))
    .mark_line(size=0.8)
    .encode(
        x=alt.X(
            "gm",
            title="Game number in season",
            axis=alt.Axis(values=[20, 40, 60, 80, 100, 120, 140, 160]),
            scale=alt.Scale(domain=[0, 162]),
        ),
        y=alt.Y("gb:Q", title="Games ahead/back by game in the season: 1958-2024"),
        color=alt.Color("year:O", scale={"range": ["#bbbbbb"]}, legend=None),
    )
    .properties(
        width=800,
        height=400,
        title="LA Dodgers historical standings",
    )
)

current = (
    alt.Chart(df.query("year == '2024'"))
    .mark_line(size=2, color="#005A9C")
    .encode(
        x=alt.X("gm", scale=alt.Scale(domain=[0, 160])),  # Apply the same domain limit
        y="gb:Q",
    )
)

hline = (
    alt.Chart(pd.DataFrame({"y": [0]}))
    .mark_rule(color="black", strokeWidth=0.5)
    .encode(y="y")
)

# Define a text annotation just above the horizontal line
text = (
    alt.Chart(pd.DataFrame({"y": [0], "text": ["Leading ↑"]}))
    .mark_text(
        color="#666666",
        align="center",
        baseline="bottom",
        dy=-0,
        dx=370,
        fontSize=12,
        fontWeight="bold",
    )
    .encode(y="y:Q", text="text:N")
)

# Define a text annotation just above the horizontal line
anno_text = (
    alt.Chart(pd.DataFrame({"y": [20], "text": ["1958-2023"]}))
    .mark_text(
        color="#bbbbbb",
        align="center",
        baseline="bottom",
        dy=20,
        dx=20,
        fontSize=12,
        fontWeight="bold",
    )
    .encode(y="y:Q", text="text:N")
)

# Extract the last point of the 2024 season
last_point_df = df.query("year == '2024'").tail(1).copy()
last_point_df["annotation"] = "2024"

# Create a text annotation chart for the "current" line
current_text_annotation = (
    alt.Chart(last_point_df)
    .mark_text(
        align="left",
        baseline="middle",
        dx=15,
        dy=-30,
        fontSize=12,
        fontWeight="bold",
        color="#005A9C",  # Match the line color or choose a different one
    )
    .encode(x=alt.X("gm:Q"), y=alt.Y("gb:Q"), text="annotation:N")
)

# Combine everything, including the new text annotation
chart = (past + hline + current + text + anno_text + current_text_annotation).configure_title(
    # fontSize=20,
    font=font
).configure_axis(
    labelFont=font,
    titleFont=font
)

# Show the chart
chart


chart.save("visuals/standings.png", scale_factor=2.0)


alt.Chart(limit_df.query(f"gm == {game_number}")).mark_bar().encode(
    x=alt.Y(
        "year:O",
        axis=alt.Axis(
            values=[1960, 1970, 1980, 1990, 2000, 2010, 2024],
            title="",
        ),
    ),
    y=alt.Y("gb:Q", title=""),
    color=alt.condition(
        alt.datum.gb > 0,
        alt.value("#005A9C"),
        alt.value("#e9e9e9"),
    ),
).properties(
    width=650,
    height=200,
    title=f"LA Dodgers historical standings: Games back by game {game_number} of the season: 1958-2024",
)



"""
Scoring
"""

# Group by season and sum runs, runs against

runs_season_limit = (
    df.groupby("year").agg({"r": "sum", "ra": "sum", "gm": "size"}).reset_index()
).rename(columns={"r": "runs", "ra": "runs_against", "gm": "games"})


# Runs and runs against per game

runs_season_limit["runs_per_game"] = (
    runs_season_limit["runs"] / runs_season_limit["games"]
).round(2)


runs_season_limit["runs_against_per_game"] = (
    runs_season_limit["runs_against"] / runs_season_limit["games"]
).round(2)


# Difference

runs_season_limit["runs_per_game_diff"] = (
    runs_season_limit["runs_per_game"] - runs_season_limit["runs_against_per_game"]
)


"""
Runs scrored chart
"""

limit_df["r"] = limit_df["r"].astype(int)


runs_so_far = (
    limit_df.groupby("year")["r"]
    .sum()
    .reset_index(name="runs_to_date")
    .sort_values("year", ascending=False)
)


runs_this_season = int(runs_so_far.query("year == year.max()")["runs_to_date"].iloc[0])


base = (
    alt.Chart(runs_so_far)
    .encode(
        x=alt.X(
            "runs_to_date",
            title=f"Runs by game no. {game_number}",
            axis=alt.Axis(tickCount=6),
        ),
        y=alt.Y("year:O", title="").sort("x"),
        color=alt.condition(
            alt.datum.year == "2024",
            alt.value("steelblue"),
            alt.value("#e3e3e3"),
        ),
        text=alt.Text("runs_to_date", title=""),
    )
    .properties(
        height=1100,
        width=650,
        title=f"Dodgers historical offense: Total runs through game {game_number}, 1958-2024",
    )
)

base.mark_bar(color="#005A9C") + base.mark_text(align="left", dx=2, color="#000")

# Define the vertical line for "runs_this_season"
vertical_line = (
    alt.Chart(pd.DataFrame({"x": [runs_this_season]}))
    .mark_rule(color="black", size=0.5)
    .encode(
        x="x:Q",
    )
)

# Define the text annotation for the vertical line
text_annotation = (
    alt.Chart(pd.DataFrame({"x": [runs_this_season], "y": [runs_so_far["year"].max()]}))
    .mark_text(
        text=[f"Runs this season: {runs_this_season}"],
        align="left",
        dx=5,  # Adjust text position horizontally
        dy=-1005,  # Adjust text position vertically
    )
    .encode(
        x="x:Q",
        y=alt.Y("y:O", axis=alt.Axis(title="")),
    )
)

# Combine your base chart with the vertical line and text annotation
final_chart = (
    base.mark_bar(color="#005A9C")
    + base.mark_text(align="left", dx=2, color="#000")
    + vertical_line
    + text_annotation
).properties(
    height=1100,
    width=650,
    title=f"Dodgers historical offense: Total runs through game {game_number}, 1958-2024",
).configure_title(
    # fontSize=20,
    font=font
).configure_axis(
    labelFont=font,
    titleFont=font
)

final_chart.save("visuals/runs.png", scale_factor=2.0)
