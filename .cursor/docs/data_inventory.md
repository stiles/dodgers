# Milestone 0: data inventory (what is consumed, where it comes from)

Scope: datasets referenced by `index.markdown` and `assets/js/dashboard.js`.

## Build-time (Jekyll `site.data.*`)

| Dataset | Consumer | Producer | Source | Storage | Notes |
|---|---|---|---|---|---|
| `site.data.season_summary_latest` | `index.markdown` stat cards + headline | `scripts/07_create_toplines_summary.py` | Mixed: derived from standings + other datasets | Repo `_data/season_summary_latest.*` (and also published to `data/standings/season_summary_latest.*` / S3 depending on script) | Primary “above the fold” summary. |
| `site.data.standings.all_teams_standings_metrics_<year>.json` (dynamic key, with 2024 fallback) | `index.markdown` division standings tables | `scripts/00_fetch_league_standings.py` | MLB StatsAPI (`statsapi.mlb.com/api/v1/standings`) | Repo `_data/standings/all_teams_standings_metrics_<year>.json` and also `data/standings/...` + S3 | Good example of “dual write” (Jekyll + S3). |

## Runtime (dashboard JS fetch)

`assets/js/dashboard.js` currently fetches from S3 website URLs (`https://stilesdata.com/dodgers/data/...`) and in a few places tries a local `/data/...` fallback.

| Dataset URL/path (current) | Consumer | Producer script(s) | Likely source | Storage | Notes |
|---|---|---|---|---|---|
| `dodgers/data/standings/dodgers_standings_1958_present_optimized.json` | standings “GB” chart + misc | `scripts/04_fetch_process_standings.py` | Baseball Reference scrape + historic archive parquet | S3 + generated under `data/standings/` | This is in the “must migrate off Baseball Reference for new updates” set. |
| `dodgers/data/standings/dodgers_standings_1958_present.json` | cumulative wins historical compare | `scripts/04_fetch_process_standings.py` | Baseball Reference scrape + archive | S3 + `data/standings/` | Same as above. |
| `dodgers/data/standings/dodgers_wins_losses_current.json` | run differential chart | `scripts/09_build_wins_losses_from_boxscores.py` | Baseball Savant boxscores archive | S3 + `data/standings/` | Used for current-season run diff/wins-losses visuals. |
| `dodgers/data/standings/dodgers_wins_projection_timeseries.json` | wins projection chart | `scripts/18_generate_projection.py` | Derived (simulation) | S3 + `data/standings/` | Currently fetched by dashboard; may be seasonal-only. |
| `dodgers/data/standings/dodgers_schedule.json` | “Last 10 / Next 10” schedule tables | `scripts/13_fetch_process_schedule.py` | Baseball Reference scrape | S3 + `data/standings/` | Good early migration candidate to MLB StatsAPI. |
| `dodgers/data/standings/all_teams_standings_metrics_<year>.json` | standings tables (JS) | `scripts/00_fetch_league_standings.py` | MLB StatsAPI | S3 + `data/standings/` + `_data/standings/` | JS uses `currentYear` interpolation. |
| `dodgers/data/standings/mlb_team_attendance.json` | attendance tables | `scripts/11_fetch_process_attendance.py` | (Likely) Baseball Reference scrape (verify) | S3 + `data/standings/` | Dashboard references `.../standings/mlb_team_attendance.json`. |
| `dodgers/data/batting/archive/dodgers_historic_batting_gamelogs.json` | batting historical charts | `scripts/10_fetch_process_historic_batting_gamelogs.py` | Baseball Reference scrape + archive | S3 + `data/batting/archive/` | Historical dataset used for trend charts. |
| `dodgers/data/batting/dodgers_player_batting_current_table.json` | “Player hitting” tables | `scripts/14_fetch_process_batting_mlb.py` | MLB (bdfed stitch endpoint) | S3 + `data/batting/` | Current-season, API-driven already (good). |
| `dodgers/data/batting/dodgers_xwoba_current.json` | xwOBA small multiples | `scripts/15_fetch_xwoba.py` | Baseball Savant | S3 + `data/batting/` | Statcast-only; keep Savant. |
| `dodgers/data/batting/shohei_home_runs_cumulative_timeseries_combined.json` | Shohei “50-50 trend” | `scripts/16_fetch_shohei.py` | MLB (bdfed stitch endpoint) | S3 + `data/batting/` | Could later be normalized into a generic “player milestones” dataset. |
| `dodgers/data/batting/shohei_stolen_bases_cumulative_timeseries_combined.json` | Shohei “50-50 trend” | `scripts/16_fetch_shohei.py` | MLB (bdfed stitch endpoint) | S3 + `data/batting/` | Same as above. |
| `dodgers/data/pitching/dodgers_historic_pitching_gamelogs_1958-present.json` | pitching historical charts | `scripts/12_fetch_process_historic_pitching_gamelogs.py` | Baseball Reference scrape + archive | S3 + `data/pitching/` | Historical dataset used for trend charts. |
| `dodgers/data/pitching/shohei_ohtani_pitch_mix.json` | Shohei pitch mix | `scripts/25_fetch_shohei_pitches.py` | Baseball Savant | S3 + `data/pitching/` | Statcast-only; keep Savant. |
| `dodgers/data/pitching/shohei_ohtani_pitches.json` | Shohei pitch chart | `scripts/25_fetch_shohei_pitches.py` | Baseball Savant | S3 + `data/pitching/` | Statcast-only; keep Savant. |
| `dodgers/data/summary/umpire_summary.json` | umpire scorecard | `scripts/21_summarize_pitch_data.py` | Derived from Savant gamefeeds (`scripts/20_fetch_game_pitches.py`) | S3 + `data/summary/` | Downstream “summary” dataset.
| `dodgers/data/postseason/dodgers_postseason_stats_2025.json` | postseason player cards | `scripts/28_fetch_postseason_stats.py` | MLB StatsAPI (`people/<id>/stats...gameType=P`) | S3 + `data/postseason/` | Currently year-hardcoded in both JS and content.
| `dodgers/data/postseason/dodgers_postseason_series_2025.json` | playoff journey | `scripts/28_fetch_postseason_stats.py` (and referenced by `scripts/07_create_toplines_summary.py`) | MLB StatsAPI postseason schedule | S3 + `data/postseason/` | Also year-hardcoded.

## Key gaps this inventory highlights

- “Core season tables” still scraping Baseball Reference for new updates:
  - standings (`scripts/04_fetch_process_standings.py`)
  - schedule (`scripts/13_fetch_process_schedule.py`)
  - historic batting/pitching gamelogs (`scripts/10_...`, `scripts/12_...`) for ongoing refresh
- Frontend uses a mix of:
  - build-time `_data` (`site.data.*`)
  - runtime S3 fetches hardcoded in `assets/js/dashboard.js`

## Next milestone tie-in

Milestone 1 will introduce a repo-published manifest and switch `assets/js/dashboard.js` to resolve all these datasets via dataset IDs rather than hardcoding URLs.
