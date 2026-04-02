# LA Dodgers team tracker

This repository feeds [Dodgers Data Bot](https://dodgersdata.bot), a statistical dashboard about the LA Dodgers' performance.

The code executes an automated workflow to fetch, process and store the team's current standings along with historical game-by-game records dating back to 1958. It also collects batting and pitching data, among other statistics, for the same period. 

These records are processed and used to bake out the site using the Jekyll static site generator, in concert with Github Pages, and D3.js for charts. 

The data is sourced from [Baseball Reference](https://www.baseball-reference.com/teams/LAD/), [Baseball Savant](https://baseballsavant.mlb.com/), and [MLB StatsAPI](https://statsapi.mlb.com/) and consolidated into unified datasets for analysis and visualization purposes only. The resulting site is a non-commercial fan project.

## Architecture

### Phase-aware data pipeline

The data pipeline automatically adapts to the current MLB season phase (regular season, postseason, or offseason):

- **Regular season**: Full daily data refresh including standings, batting, pitching, schedule, pitch data, and projections
- **Postseason**: Postseason-specific stats plus maintained roster and final regular season snapshots  
- **Offseason**: Minimal updates focusing on roster, transactions, news, and historical data refresh

The phase is automatically detected using MLB's official schedule API. Scripts are organized in `scripts/phase_config.py` and executed via `scripts/run_phase_scripts.py`.

### Manifest-driven data access

All datasets are tracked through a central `manifest.json` that provides:

- Dataset metadata (version, update timestamps, phase info)
- URLs for all data artifacts (JSON, CSV, Parquet)
- Season context (current year, postseason status)
- Automated cache invalidation via version hashing

The frontend loads data through `assets/js/manifest_loader.js`, which provides helper functions like `getDatasetUrl()` and `isPostseasonActive()` for consistent, phase-aware data access.

## Automated tweets

In addition to the data processing scripts, the repository contains scripts that generate and post daily updates to an account on Twitter, [@DodgersDataBot](https://x.com/DodgersDataBot).

- **Daily summaries**: The `scripts/23_post_daily_summaries.py` script fetches the latest team summary data and posts tweets about the team's overall performance, batting and pitching statistics. This is automated by the `.github/workflows/post_summaries.yml` workflow, which runs at different times throughout the day to provide timely updates.
- **Lineup and pitching matchup**: The `scripts/17_fetch_lineup.py` script fetches the daily starting lineup and tweets the pitching matchup once it's announced. This is automated by the `.github/workflows/tweet_lineup.yml` workflow.
- **News roundup**: The `scripts/24_fetch_news.py` script fetches the top Dodgers-related headlines from the LA Times, Dodgers Nation and MLB.com. It then formats these into a single tweet. This is automated by the `.github/workflows/post_news.yml` workflow, which runs every day at 1 p.m. PT.

## How it works

The repository includes numerous Python scripts that perform the following daily operations for team standings, pitching and batting, by season, including:

### Scripts:

**Core phase-aware pipeline scripts:**

- **Season phase detection:** `scripts/season_phase.py` - Automatically detects regular season, postseason, or offseason using MLB schedule API
- **Phase orchestration:** `scripts/run_phase_scripts.py` - Executes appropriate scripts based on detected phase
- **Phase configuration:** `scripts/phase_config.py` - Defines which datasets are updated in each phase
- **Manifest generation:** `scripts/99_publish_manifest.py` - Creates central manifest.json with all dataset URLs and metadata

**Regular season scripts (run multiple times daily):**

- **League standings (reference for rankings):** `scripts/00_fetch_league_standings.py`
- **Update Savant boxscores archive (discovers new games, fetches only new finals):** `scripts/02_update_boxscores_archive.py`
- **League ranks (scraped):** `scripts/03_scrape_league_ranks.py`
- **Latest and historical standings:** `scripts/04_fetch_process_standings.py`
- **Team batting (figures and league ranks):** `scripts/05_fetch_process_batting.py`
- **Team pitching (figures and league ranks):** `scripts/06_fetch_process_pitching.py`
- **Dashboard summary statistics:** `scripts/07_create_toplines_summary.py`
- **Run differential for current season (from Savant boxscores):** `scripts/09_build_wins_losses_from_boxscores.py`
- **Team schedule:** `scripts/13_fetch_process_schedule.py`
- **MLB batting (league-level tables):** `scripts/14_fetch_process_batting_mlb.py`
- **xwOBA rolling windows (current season):** `scripts/15_fetch_xwoba.py`
- **Shohei Ohtani season data:** `scripts/16_fetch_shohei.py`
- **Win projection model:** `scripts/18_generate_projection.py`
- **Roster:** `scripts/19_fetch_roster.py`
- **Game pitch-by-pitch:** `scripts/20_fetch_game_pitches.py`
- **Pitch summaries:** `scripts/21_summarize_pitch_data.py`

**Postseason scripts:**

- **Postseason statistics:** `scripts/28_fetch_postseason_stats.py`
- **Roster updates:** `scripts/19_fetch_roster.py`
- **Transactions:** `scripts/26_post_transactions.py`

**Offseason scripts (run weekly):**

- **Team post-season history:** `scripts/08_fetch_process_season_outcomes.py`
- **Past/present team batting performance:** `scripts/10_fetch_process_historic_batting_gamelogs.py`
- **Team attendance (all teams):** `scripts/11_fetch_process_attendance.py`
- **Past/present team pitching performance:** `scripts/12_fetch_process_historic_pitching_gamelogs.py`
- **Roster:** `scripts/19_fetch_roster.py`
- **Transactions:** `scripts/26_post_transactions.py`
- **News:** `scripts/24_fetch_news.py`
  
Separate tweet/automation scripts are documented in the sections below (lineups, daily summaries, news, etc.).
### What they do:

1. **Detect season phase**: Automatically determines whether MLB is in regular season, postseason, or offseason using the official schedule API
2. **Fetch phase-appropriate data**: Downloads current standings, batting, pitching, and other statistics based on the active phase
3. **Process data**: Cleans and formats the fetched data for consistency with historical datasets
4. **Concatenate with historic data**: Merges current season data with pre-existing datasets (1958-present for standings and batting)
5. **Generate aggregations**: Creates summary statistics, projections, and rolling metrics
6. **Save and export data**: Outputs datasets in CSV, JSON and Parquet formats
7. **Upload to AWS S3**: Uploads files to S3 bucket with appropriate cache headers
8. **Publish manifest**: Generates manifest.json with URLs, versions, and metadata for all datasets
9. **Build and deploy site**: Compiles Jekyll site and deploys to GitHub Pages

## GitHub Actions workflow

The repository uses GitHub Actions to automate the execution of the scripts, ensuring the datasets remain up-to-date throughout the baseball season. The key workflows include:

- **`fetch.yml`**: The main phase-aware data pipeline that runs multiple times daily during the season (March-October). Automatically detects the current season phase and executes the appropriate scripts for regular season, postseason, or offseason. Builds and deploys the Jekyll site to GitHub Pages.
- **`post_summaries.yml`**: Posts statistical summaries to Twitter at 8am, 10am, and 12pm PT.
- **`tweet_lineup.yml`**: Checks hourly for the day's lineup and posts the pitching matchup to Twitter once available.
- **`post_news.yml`**: Fetches and posts a news roundup to Twitter at 1pm PT.

The fetch workflow can be manually triggered with an optional phase override for testing or special circumstances.

## Configuration and usage

To utilize this repository for your own tracking or analysis on the Dodgers or another team, follow these steps:

1. **Fork the repository**: Create a copy of this repository under your own GitHub account.
2. **Configure secrets**: Add the following secrets to your repository settings for secure AWS S3 uploads (optional):
    - `AWS_ACCESS_KEY_ID`: Your AWS Access Key ID.
    - `AWS_SECRET_ACCESS_KEY`: Your AWS Secret Access Key.
3. **Adjust the scripts (Optional)**: Modify the Python scripts as necessary to fit your specific team, data processing or analysis needs.
4. **Monitor actions**: Check the "Actions" tab in your GitHub repository to see the workflow executions and ensure data is being updated as expected.

## Data storage and access

The processed datasets are uploaded to an AWS S3 bucket and tracked via a central manifest for versioned, cache-aware access.

### Manifest

**Current manifest (central data registry):**
- [JSON](https://stilesdata.com/dodgers/data/manifest.json)

The manifest provides:
- Current season phase (regular_season, postseason, offseason)
- Postseason status and active series info
- URLs and versions for all datasets
- Last update timestamps
- Season context (current year, team info)

Frontend code should use the manifest to discover dataset URLs rather than hardcoding paths.

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

**Game-by-game standings, 1958 to present (10,700+ rows):**

- [JSON](https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.json)
- [CSV](https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.csv)
- [Parquet](https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.parquet)

Historical archive (for year-over-year comparisons):
- [Parquet](https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_2025.parquet)

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
| `run_diff`      | int64           | Run differential (r - ra)            |
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

