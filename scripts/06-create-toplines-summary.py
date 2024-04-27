#!/usr/bin/env python
# coding: utf-8

"""LA Dodgers toplines
This notebook extracts key statistics from the project's processed tables for display in a dashboard.
"""

# Import Python tools and Jupyter config

import os
import boto3
import pandas as pd
import altair as alt
from io import BytesIO

"""
Read
"""

# Standings

standings = pd.read_json(
    "https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.json"
).query("year == 2024")
standings_past = pd.read_json(
    "https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.json"
).query("year != 2024")
standings_now = standings.query("game_date == game_date.max()").copy()


standings_now.loc[standings_now.result == "L", "result_clean"] = "loss"
standings_now.loc[standings_now.result == "W", "result_clean"] = "win"


batting = pd.read_json(
    "https://stilesdata.com/dodgers/data/batting/dodgers_team_batting_1958_present.json", lines=True
)


batting_past = batting.query("season != 2024").copy()
batting_now = batting.query("season == 2024").copy()

"""
Key statistics
"""

# 1. Current season record (Wins-Losses)
# > Provides an immediate understanding of the team's overall performance for the season.

games = standings_now["gm"].loc[0]
wins = standings_now["wins"].loc[0]
losses = standings_now["losses"].loc[0]


record = standings_now["record"].loc[0]


# 2. Win percentage
# > Allows for normalization of success to compare across different seasons or different numbers of games played.

win_pct = int(standings_now["win_pct"].loc[0] * 100)
win_pct_decade_thispoint = int(
    standings_past.query(f"gm == {games}").head(10)["win_pct"].mean().round(2) * 100
)


# 3. Run differential
# > A positive run differential generally correlates with a stronger team performance and is predictive of future success.

runs = standings["r"].sum()
runs_against = standings["ra"].sum()


run_diff = runs - runs_against


# 4. Home runs and home runs per game
# > Reflects the team's power-hitting capabilities, significant for scoring strategies.

batting_past["hr_game"] = (
    batting_past["hr"].astype(int) / batting_past["g"].astype(int)
).round(2)


home_runs = int(batting_now["hr"].sum())
home_runs_game = (home_runs / games).round(2)
home_runs_game_last = batting_past.query('season == "2023"')["hr_game"].iloc[0]


games_decade = batting_past.head(10)["g"].astype(int).sum()
home_runs_decade = batting_past.head(10)["hr"].astype(int).sum()


home_runs_game_decade = (home_runs_decade / games_decade).round(2)


# 5. Earned run average (ERA)
# > A key measure of pitching staff effectiveness, with a lower ERA indicating better performance.

# Batting average and on
# > Summarizes players' strength in getting on base — and hopefully scoring runs.

batting_average = batting_now["ba"].iloc[0]


batting_average_decade = (
    batting_past.head(10)["ba"]
    .astype(float)
    .mean()
    .round(3)
    .astype(str)
    .replace("0.", ".")
)


# 7. Stolen bases
# > Stolen bases can significantly impact game dynamics and indicate the team's strategic play.

stolen_bases = int(batting_now["sb"].iloc[0])
stolen_bases_game = (stolen_bases / games).round(2)


stolen_decade = batting_past.head(10)["sb"].astype(int).sum()
games_decade = batting_past.head(10)["g"].astype(int).sum()
stolen_bases_decade_game = (stolen_decade / games_decade).round(2)


# 8. Fielding percentage
# > Indicates the team's defensive capabilities, with a higher percentage reflecting better performance.

# 9. Recent trend (last 10 games)
# > Provides insight into the team's current form and momentum, which is essential for assessing changes in performance.

last_10 = standings["result"].head(10)
win_count_trend = last_10[last_10 == "W"].count()
loss_count_trend = last_10[last_10 == "L"].count()


win_loss_trend = f"Recent trend: {win_count_trend} wins, {loss_count_trend} losses"


# 10. Summary
# > Creates one file to import for topline statistics and a narrative summary of the standings now.

summary = f"The Dodgers have played {games} games this season compiling a {record} record — a winning percentage of {win_pct}%. The team's last game was a {standings_now['r'].iloc[0]}-{standings_now['ra'].iloc[0]} {standings_now['home_away'].iloc[0]} {standings_now['result_clean'].iloc[0]} to the {standings_now['opp'].iloc[0]} in front of {'{:,}'.format(standings_now['attendance'].iloc[0])} fans. The team has won {win_count_trend} of its last 10 games."


summary_data = {
    "stat": [
        "wins",
        "losses",
        "record",
        "win_pct",
        "win_pct_decade_thispoint",
        "runs",
        "runs_against",
        "run_differential",
        "home_runs",
        "home_runs_game",
        "home_runs_game_last",
        "home_runs_game_decade",
        "stolen_bases",
        "stolen_bases_game",
        "stolen_bases_decade_game",
        "batting_average",
        "batting_average_decade",
        "summary",
    ],
    "stat_value": [
        wins,
        losses,
        record,
        f"{win_pct}%",
        f"{win_pct_decade_thispoint}%",
        runs,
        runs_against,
        run_diff,
        home_runs,
        home_runs_game,
        home_runs_game_last,
        home_runs_game_decade,
        stolen_bases,
        stolen_bases_game,
        stolen_bases_decade_game,
        batting_average,
        batting_average_decade,
        summary,
    ],
    "category": [
        "standings",
        "standings",
        "standings",
        "standings",
        "standings",
        "standings",
        "standings",
        "standings",
        "batting",
        "batting",
        "batting",
        "batting",
        "batting",
        "batting",
        "batting",
        "batting",
        "batting",
        "standings",
    ],
}

summary_df = pd.DataFrame(summary_data)

print(summary_df)

summary_df.to_csv("data/standings/season_summary_latest.csv", index=False)
summary_df.to_json(
    "data/standings/season_summary_latest.json", indent=4, orient="records"
)


# S3

def save_to_s3(df, base_path, s3_bucket, formats=["csv", "json"]):
    try:
        session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name="us-west-1"
        )
        s3_resource = session.resource("s3")

        for fmt in formats:
            file_path = f"{base_path}.{fmt}"
            buffer = BytesIO()
            if fmt == "csv":
                df.to_csv(buffer, index=False)
                content_type = "text/csv"
            elif fmt == "json":
                df.to_json(buffer, indent=4, orient="records", lines=True)
                content_type = "application/json"

            buffer.seek(0)
            s3_resource.Bucket(s3_bucket).put_object(
                Key=file_path, Body=buffer, ContentType=content_type
            )
            print(f"Uploaded {fmt} to {s3_bucket}/{file_path}")
    except Exception as e:
        print(f"Failed to upload to S3: {e}")


# Save to S3
# save_to_s3(
#     summary_df,
#     "dodgers/data/standings/season_summary_latest",
#     "stilesdata.com",
# )