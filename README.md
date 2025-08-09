# LA Dodgers team tracker

This repository — a growing work in progress — feeds [Dodgers Data Bot](https://dodgersdata.bot), a statistical dashboard about the LA Dodgers' performance.

The code executes an automated workflow to fetch, process and store the team's current standings along with historical game-by-game records dating back to 1958. It also collects batting and pitching data, among other statistics, for the same period. These records are processed and used to bake out the site using the Jekyll static site generator, in concert with Github Pages, and D3.js for charts. 

The data is sourced from the heroes at [Baseball Reference](https://www.baseball-reference.com/teams/LAD/2024-schedule-scores.shtml) and [Baseball Savant](https://baseballsavant.mlb.com/) and consolidated into unified datasets for analysis and visualization purposes only. The resulting site is a non-commercial fan project.

## Automated tweets

In addition to the data processing scripts, the repository contains scripts that generate and post daily updates to an account on Twitter, [@DodgersDataBot](https://x.com/DodgersDataBot).

- **Daily summaries**: The `scripts/23_post_daily_summaries.py` script fetches the latest team summary data and posts tweets about the team's overall performance, batting and pitching statistics. This is automated by the `.github/workflows/post_summaries.yml` workflow, which runs at different times throughout the day to provide timely updates.
- **Lineup and pitching matchup**: The `scripts/17_fetch_lineup.py` script fetches the daily starting lineup and tweets the pitching matchup once it's announced. This is automated by the `.github/workflows/tweet_lineup.yml` workflow.
- **News roundup**: The `scripts/24_fetch_news.py` script fetches the top Dodgers-related headlines from the LA Times, Dodgers Nation and MLB.com. It then formats these into a single tweet. This is automated by the `.github/workflows/post_news.yml` workflow, which runs every day at 1 p.m. PT.

## How it works

The repository includes numerous Python scripts that perform the following daily operations for team standings, pitching and batting, by season, including:

### Scripts:

- **Latest and historical standings:** `scripts/01_fetch_process_standings.py`
- **Team batting (figures and league ranks):** `scripts/02_fetch_process_batting.py`
- **Visual sketches for standings:** `scripts/03_viz_standings.py`
- **Visual sketches for batting:** `scripts/04_viz_batting.py`
- **Team pitching (figures and league ranks):** `scripts/05_fetch_process_pitching.py`
- **Dashboard summary statistics:** `scripts/06-create-toplines-summary.py`
- **Team post-season history:** `scripts/07_fetch_process_season_outcomes.py`
- **Run differential for current season:** `scripts/08_fetch_process_wins_losses_current.py`
- **Past/present team batting performance:** `scripts/09_fetch_process_historic_batting_gamelogs.py`
- **Team attendance (all teams):** `scripts/10_fetch_process_attendance.py`
- **Past/present team pitching performance:** `11_fetch_process_historic_pitching_gamelogs.py`
- **Starting lineups:** `scripts/17_fetch_lineup.py`
- **Daily summary tweets:** `scripts/23_post_daily_summaries.py`
- **News roundup tweets:** `scripts/24_fetch_news.py`
- **Shohei Ohtani pitching data:** `scripts/25_fetch_shohei_pitches.py`
- **xwOBA rolling windows (current season):** `scripts/15_fetch_xwoba.py`

### What they do:

1. **Fetch current season, batting and pitching data**: Download the current season's game-by-game standings for the LA Dodgers from [Baseball Reference](https://www.baseball-reference.com/teams/LAD/2024-schedule-scores.shtml). The latest season's batting statitics for each player also fetched, as are the latest season's pitching statistics for each pitcher and the team as a whole. A to-date season summary with standings information and major batting statistics is also created.
2. **Process data**: Cleans and formats the fetched standings and batting data for consistency with the historical dataset.
3. **Concatenate with historic data**: Merges the current season's data for batting and standings with pre-existing datasets containing records for the 1958 to 2023 seasons.
4. **Create three basic *standings* visualizations**: Reads the standings archive and produces a multi-series [line chart](/visuals/standings.png) comparing the current season with previous seasons. A horizontal [bar chart](/visuals/runs.png) is also produced showing the number of runs produced in each season to the current point for comparison. The script also creates a [facet barcode chart](/visuals/batting_rates.png) showing the per-bat rates for various categories (hits, homers, etc.) over the years. Both rely on the [Altair visualization library](https://altair-viz.github.io/) to create and save the charts into a `visuals` directory.
5. **Save and export data**: Outputs the combined datasets in CSV, JSON and Parquet formats.
6. **Upload to AWS S3**: Uploads the files to an AWS S3 bucket for use and archiving.

## GitHub Actions workflow

The repository uses GitHub Actions to automate the execution of the scripts each day, ensuring the datasets remains up-to-date throughout the baseball season. The key workflows include:

- **`fetch_dodgers_data.yml`**: This is the main data pipeline, running multiple times a day during the season. It executes all the Python scripts responsible for fetching, processing, and saving the core team and player statistics needed to build the site.
- **`build_site.yml`**: Fetches and processes all core team data (standings, batting, pitching, etc.) and rebuilds the site. Runs daily.
- **`post_summaries.yml`**: Posts statistical summaries to Twitter at 8am, 10am, and 12pm PT.
- **`tweet_lineup.yml`**: Checks hourly for the day's lineup and posts the pitching matchup to Twitter once available.
- **`post_news.yml`**: Fetches and posts a news roundup to Twitter at 1pm PT.

## Configuration and usage

To utilize this repository for your own tracking or analysis on the Dodgers or another team, follow these steps:

1. **Fork the repository**: Create a copy of this repository under your own GitHub account.
2. **Configure secrets**: Add the following secrets to your repository settings for secure AWS S3 uploads (optional):
    - `AWS_ACCESS_KEY_ID`: Your AWS Access Key ID.
    - `AWS_SECRET_ACCESS_KEY`: Your AWS Secret Access Key.
3. **Adjust the scripts (Optional)**: Modify the Python scripts as necessary to fit your specific team, data processing or analysis needs.
4. **Monitor actions**: Check the "Actions" tab in your GitHub repository to see the workflow executions and ensure data is being updated as expected.

## Data storage and access

The processed datasets — which aren't all documented below yet — are uploaded to an AWS S3 bucket. 

### Standings

**Latest season summary**

- [JSON](https://stilesdata.com/dodgers/data/standings/season_summary_latest.json)
- [CSV](https://stilesdata.com/dodgers/data/standings/season_summary_latest.csv)

**Data structure:**
*Each row represents a statistic for the latest point in the season*

| Stat                        | Value | Category  |
|-----------------------------|-------|-----------|
| wins                        | 15    | standings |
| losses                      | 11    | standings |
| record                      | 15-11 | standings |
| win_pct                     | 57%   | standings |
| win_pct_decade_thispoint    | 57%   | standings |
| runs                        | 139   | standings |
| runs_against                | 112   | standings |
| run_differential            | 27    | standings |
| home_runs                   | 30    | batting   |
| home_runs_game              | 1.15  | batting   |
| home_runs_game_last         | 1.54  | batting   |
| home_runs_game_decade       | 1.36  | batting   |
| stolen_bases                | 16    | batting   |
| stolen_bases_game           | 0.62  | batting   |
| stolen_bases_decade_game    | 0.49  | batting   |
| batting_average             | .268  | batting   |
| batting_average_decade      | .253  | batting   |
| summary                     | The Dodgers have played 26 games this season compiling a 15-11 record — a winning percentage of 57%. The team's last game was an 11-2 away win to the WSN in front of 26,298 fans. The team has won 5 of its last 10 games. | standings |

**Game-by-game standings, 1958 to present (10,400+ rows):**

- [JSON](https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.json)
- [CSV](https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.csv)
- [Parquet](https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.parquet)

**Data structure:**
*Each row represents a game in a specific season*

| column_name     | column_type     | column_description                   |
|-----------------|-----------------|--------------------------------------|
| `gm`            | int64           | Game number of season                |
| `game_date`     | datetime64[ns]  | Game date (%Y-%m-%d)                 |
| `home_away`     | object          | Game location ("home" vs. "away")    |
| `opp`           | object          | Three-digit opponent abbreviation    |
| `result`        | object          | Dodgers result ("W" vs. "L")         |
| `r`             | int64           | Dodgers runs scored                  |
| `ra`            | int64           | Runs allowed by Dodgers              |
| `record`        | object          | Dodgers season record after game     |
| `wins`        | int64          | Dodgers wins after game     |
| `losses`        | int64          | Dodgers losses after game     |
| `win_pct`        | float64          | Dodgers season record after game     |
| `rank`          | object          | Rank in division*                    |
| `gb`            | float64         | Games back in division*              |
| `time`          | object          | Game length                          |
| `time_minutes`  | int64           | Game length, in minutes              |
| `day_night`     | object          | Start time: "D" vs. "N"              |
| `attendance`    | int64           | Home team attendance                 |
| `year`          | object          | Season year                          |


\* *Before divisional reorganization in the National League in 1969, these figures represented league standings.*

### Batting

**Season-by-season batting statistics, by player, 1958 to present:**

- [JSON](https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_1958_present.json)
- [CSV](https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_1958_present.csv)
- [Parquet](https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_1958_present.parquet)

**Data structure:**
*Each row represents a player in a specific season*

| column_name | column_type | column_description                                      |
|-------------|-------------|---------------------------------------------------------|
| `rk`        | object      | Rank order at output                                    |
| `pos`       | object      | Position                                                |
| `name`      | object      | Player name                                             |
| `age`       | object      | Player age on June 30                                   |
| `g`         | int64       | Game appearances                                        |
| `pa`        | int64       | Plate appearances*                                      |
| `ab`        | int64       | At-bats*                                                |
| `r`         | int64       | Runs scored                                             |
| `h`         | int64       | Hits                                                    |
| `2b`        | int64       | Doubles                                                 |
| `3b`        | int64       | Triples                                                 |
| `hr`        | int64       | Home runs                                               |
| `rbi`       | int64       | Runs batted in                                          |
| `sb`        | int64       | Stolen bases                                            |
| `cs`        | int64       | Caught stealing                                         |
| `bb`        | int64       | Walks                                                   |
| `so`        | int64       | Strikeouts                                              |
| `ba`        | float64     | Batting average                                         |
| `obp`       | float64     | On-base percentage                                      |
| `slg`       | float64     | Slugging percentage                                     |
| `ops`       | float64     | OPB + SLG                                               |
| `ops_plus`  | float64     | OPS adjusted to player's home park                      |
| `tb`        | int64       | Total bases                                             |
| `gdp`       | int64       | Double plays grounded into                              |
| `hbp`       | int64       | Hit by pitch                                            |
| `sh`        | int64       | Sacrifice hits                                          |
| `sf`        | int64       | Sacrifice flies                                         |
| `ibb`       | int64       | Intentional walks                                       |
| `season`    | object      | Season                                                  |
| `bats`      | object      | Player's batting side (right, left, unknown)            |

\* *An at-bat is when a player reaches base via a fielder's choice, hit or an error — not including catcher's interference — or when a batter is put out on a non-sacrifice. A plate appearance refers to each completed turn batting, regardless of the result.*

**Other current season player batting statistics:**
- Batting average, on-base and slugging percentage and walks, home runs and strikeouts by plate appearance via [Baseball Savant](https://bdfed.stitch.mlbinfra.com/bdfed/stats/player?&env=prod&season=2024&sportId=1&stats=season&group=hitting&gameType=R&offset=0&sortStat=plateAppearances&order=desc&teamId=119).
    - [JSON](https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_current_table.json)
    - [CSV](https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_current_table.csv)
    - [Parquet](https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_current_table.parquet)

**Season-by-season batting at the team level, 1958 to present:**
- How the team ranks or ranked in the league by season
    - [JSON](https://stilesdata.com/dodgers/data/batting/dodgers_team_batting_ranks_1958_present.json)
    - [CSV](https://stilesdata.com/dodgers/data/batting/dodgers_team_batting_ranks_1958_present.csv)
    - [Parquet](https://stilesdata.com/dodgers/data/batting/dodgers_team_batting_ranks_1958_present.parquet)

*Data structure coming soon*

- Team aggregates by season for major batting stats: hits, homers, strikeouts, etc.
    - [JSON](https://stilesdata.com/dodgers/data/batting/dodgers_team_batting_1958_present.json)
    - [CSV](https://stilesdata.com/dodgers/data/batting/dodgers_team_batting_1958_present.csv)
    - [Parquet](https://stilesdata.com/dodgers/data/batting/dodgers_team_batting_1958_present.parquet)

*Data structure coming soon*

#### xwOBA (current season)

Back end

- `scripts/15_fetch_xwoba.py` fetches rolling 100 plate appearance xwOBA series per batter from Baseball Savant
- Filters to a maintained allowlist of regular batters (`ALLOWED_BATTERS`) and normalizes names to match roster output
- Emits player names as "First Last"
- Writes outputs and uploads to S3
  - Current timeseries per allowed batter
    - [JSON](https://stilesdata.com/dodgers/data/batting/dodgers_xwoba_current.json)
    - [CSV](https://stilesdata.com/dodgers/data/batting/dodgers_xwoba_current.csv)
    - [Parquet](https://stilesdata.com/dodgers/data/batting/dodgers_xwoba_current.parquet)
  - League average xwOBA snapshot
    - [JSON](https://stilesdata.com/dodgers/data/batting/league_avg_xwoba.json)

Columns (primary)

| column_name        | description                                   |
|--------------------|-----------------------------------------------|
| `rn`               | Rolling window rank from most recent to oldest |
| `rn_fwd`           | Same as `rn` preserved for plotting            |
| `xwoba`            | Expected wOBA for the rolling window           |
| `player_name`      | Batter name in "First Last"                    |
| `player_id`        | Savant player id                               |
| `max_game_date`    | Last game date in the window (Pacific time)    |
| `league_avg_xwoba` | MLB average xwOBA used for comparison          |

Front end

- `assets/js/dashboard.js` reads `dodgers_xwoba_current.json` and renders a grid of small multiples on `index.markdown`
- Each panel plots `xwoba` over the last up to 100 plate appearances (x axis from 100 → 1)
- The title shows an up or down arrow colored against MLB average, and a dashed reference line marks the average; the label includes a halo for legibility

### Pitching

**Shohei Ohtani's pitches (current season):**
- [JSON](https://stilesdata.com/dodgers/data/pitching/shohei_ohtani_pitches.json)
- [CSV](https://stilesdata.com/dodgers/data/pitching/shohei_ohtani_pitches.csv)

**Data structure:**
*Each row represents a single pitch thrown by Shohei Ohtani*

| column_name     | column_description                   |
|-----------------|--------------------------------------|
| `x`             | Horizontal location of the pitch (feet) |
| `z`             | Vertical location of the pitch (feet) |
| `vel`           | Pitch velocity (mph)                 |
| `pitch_type_abbr` | Two-letter pitch type abbreviation (e.g., FF, ST) |
| `gd`            | Game date and timestamp              |
| `pid`           | Unique pitch identifier              |

**Shohei Ohtani's pitch mix (current season):**
- [JSON](https://stilesdata.com/dodgers/data/pitching/shohei_ohtani_pitch_mix.json)
- [CSV](https://stilesdata.com/dodgers/data/pitching/shohei_ohtani_pitch_mix.csv)

**Data structure:**
*Each row represents a pitch type in his arsenal*

| column_name | column_description          |
|-------------|-----------------------------|
| `pitchType` | Two-letter abbreviation     |
| `name`      | Full name of the pitch type |
| `percent`   | Usage percentage            |
| `count`     | Total number of pitches thrown |

**Current season pitching:**
- Team aggregates for major pitching stats: runs, ERA, etc.
    - [JSON](https://stilesdata.com/dodgers/data/pitching/dodgers_pitching_totals_current.json)
    - [CSV](https://stilesdata.com/dodgers/data/pitching/dodgers_pitching_totals_current.csv)
    - [Parquet](https://stilesdata.com/dodgers/data/pitching/dodgers_pitching_totals_current.parquet)

- Team's league ranking for major pitching stats: runs, ERA, etc.

    - [JSON](https://stilesdata.com/dodgers/data/pitching/dodgers_pitching_ranks_current.json)
    - [CSV](https://stilesdata.com/dodgers/data/pitching/dodgers_pitching_ranks_current.csv)
    - [Parquet](https://stilesdata.com/dodgers/data/pitching/dodgers_pitching_ranks_current.parquet)

*Data structure coming soon*

---

## Notes

This project, which started as a few scrapers, has grown into a detailed project and outgrown its original documentation. More to come soon. If you have questions in the meantime, [please let me know](mailto:mattstiles@gmail.com). 

## Contributions

Contributions, suggestions and enhancements are welcome! Please open an issue or submit a pull request if you have suggestions for improvement. 

## License

This project is open-sourced under the MIT License. See the LICENSE file for more details.

