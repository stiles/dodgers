# Dodgers Data Bot improvements

Planning document for upcoming feature additions and refactoring.

## 1. Shohei stats section enhancements

**Current state:**
- Section exists but is commented out (lines 482-489 in `index.markdown`)
- `scripts/16_fetch_shohei.py` fetches HR and SB cumulative timeseries
- `scripts/25_fetch_shohei_pitches.py` exists for pitch data
- No integration of pitching stats with batting stats

**Goals:**
- Reactivate Shohei stats section
- Since he's no longer stealing bases, shift focus to two-way player performance
- Show batting stats alongside pitching performance
- Display pitch repertoire/velocity data

**Tasks:**
- [ ] Review and update `scripts/16_fetch_shohei.py` to fetch current season stats
- [ ] Enhance `scripts/25_fetch_shohei_pitches.py` for comprehensive pitching metrics
- [ ] Create unified Shohei dataset combining batting and pitching
- [ ] Design visualization showing both batting (HR, BA, OPS) and pitching (ERA, K/9, pitch types)
- [ ] Update `assets/js/dashboard.js` to render the new Shohei section
- [ ] Uncomment and refactor Shohei section in `index.markdown`

**Data sources needed:**
- Batting: HR, BA, OBP, SLG, RBI (from MLB BDFed API)
- Pitching: W-L, ERA, IP, K, WHIP (from MLB Stats API)
- Pitch mix: Types, velocities, usage % (from Baseball Savant)

---

## 2. Enhanced team hitting cards

**Current state:**
- Team hitting cards display basic stats from `site.data.season_summary_latest`
- Located at lines 412-426 in `index.markdown`
- Categories: batting average, home runs per game, stolen bases, etc.

**Goals:**
- Add xBA (expected batting average), OBP, SLG to team hitting cards
- Include league rankings for each metric
- Maintain consistent visual design with existing cards

**Tasks:**
- [ ] Modify `scripts/07_create_toplines_summary.py` to include xBA, OBP, SLG
- [ ] Fetch league rankings from MLB.com or scrape from `scripts/03_scrape_league_ranks.py`
- [ ] Add new metrics to `season_summary_latest.json` output
- [ ] Update card rendering to display league rank (e.g., "2nd in MLB" or "12/30")
- [ ] Test responsive design for additional cards

**Data sources:**
- xBA: Baseball Savant
- OBP/SLG: MLB Stats API or BDFed API
- Rankings: `scripts/03_scrape_league_ranks.py` or MLB.com

---

## 3. Move inline CSS to main stylesheet

**Current state:**
- Lines 596-671 of `index.markdown` contain media query CSS
- Handles responsive layout for schedule tables
- Should be in `assets/css/style.css` for maintainability

**Goals:**
- Extract CSS from `index.markdown`
- Move to `assets/css/style.css`
- Ensure no visual regressions

**Tasks:**
- [ ] Copy CSS block from `index.markdown` lines 596-671
- [ ] Paste into `assets/css/style.css` with appropriate organization/comments
- [ ] Remove `<style>` block from `index.markdown`
- [ ] Test schedule section layout on mobile and desktop
- [ ] Verify no other inline styles exist in `index.markdown`

**Note:** The CSS handles:
- Mobile-specific layout (max-width: 767px)
- Desktop schedule tables (min-width: 901px)
- Tablet breakpoint (max-width: 900px)

---

## 4. Add pitcher performance tables

**Current state:**
- Batting tables exist (lines 442-475 in `index.markdown`)
- Show BA, OBP, SLG, BB/PA, HR/PA, SO/PA
- Use color-coded cells for performance visualization
- No equivalent for pitchers

**Goals:**
- Create pitcher performance tables similar to batting tables
- Display ERA, WHIP, K/9, BB/9, K/BB ratio, FIP
- Include league rankings where applicable
- Maintain visual consistency with batting tables

**Tasks:**
- [ ] Create new script or enhance `scripts/06_fetch_process_pitching.py` to fetch individual pitcher stats
- [ ] Generate pitcher stats dataset similar to `dodgers_player_batting_current_table`
- [ ] Output `dodgers_player_pitching_current_table` in CSV/JSON/Parquet
- [ ] Add pitcher table section to `index.markdown` after team pitching section
- [ ] Update `assets/js/dashboard.js` to render pitcher tables with color-coding
- [ ] Define color scale thresholds for pitching metrics (lower ERA = darker green, etc.)

**Data sources:**
- Individual pitcher stats: MLB Stats API or BDFed API
- Advanced metrics (FIP, xFIP): Baseball Savant or FanGraphs
- League averages for comparison

**Metrics to include:**

| Metric | Description | Good/bad direction |
|--------|-------------|-------------------|
| ERA | Earned run average | Lower is better |
| WHIP | Walks + hits per IP | Lower is better |
| K/9 | Strikeouts per 9 IP | Higher is better |
| BB/9 | Walks per 9 IP | Lower is better |
| K/BB | Strikeout-to-walk ratio | Higher is better |
| IP | Innings pitched | Context |
| W-L | Win-loss record | Context |

---

## 5. Remove "Eephus" pitches from worst calls display

**Current state:**
- `scripts/21_summarize_pitch_data.py` generates umpire worst calls
- Includes all pitch types in "worst calls of season" ranking
- Eephus pitches (very slow, 40-60 mph) can appear as "bad calls" but are edge cases
- Frontend displays worst calls without filtering

**Goals:**
- Keep Eephus pitches in data/CSV for analysis
- Filter them out in frontend display of "Worst calls of the season"
- Maintain data integrity while improving user experience

**Tasks:**
- [ ] Review `scripts/21_summarize_pitch_data.py` to understand worst calls logic
- [ ] Verify Eephus pitches are labeled as `pitch_type: "Eephus"` or similar
- [ ] Update `assets/js/dashboard.js` to filter Eephus pitches when rendering worst calls
- [ ] Add filter condition: `if (pitch.pitch_type !== "Eephus")`
- [ ] Test with current data to ensure Eephus pitches are excluded
- [ ] Document filter logic in code comments

**Technical approach:**
- Backend: No changes to `scripts/21_summarize_pitch_data.py`
- Frontend: Add filter in dashboard.js before rendering worst calls section
- Keeps data complete for potential analysis

---

## Data flow architecture notes

### Current pipeline
1. Scripts fetch from MLB Stats API, Baseball Savant, Baseball Reference
2. Data processed and saved locally in `data/` directory
3. Files uploaded to S3 bucket (`stilesdata.com/dodgers/data/`)
4. `manifest.json` tracks all dataset URLs and versions
5. Jekyll site built with data from `_data/` directory
6. Frontend JavaScript loads additional data from S3 via manifest

### Key files to understand
- `scripts/phase_config.py` - Defines which scripts run in each season phase
- `scripts/run_phase_scripts.py` - Orchestrates pipeline execution
- `scripts/99_publish_manifest.py` - Generates manifest.json
- `assets/js/manifest_loader.js` - Helper functions for loading datasets
- `assets/js/dashboard.js` - Main visualization logic (4358 lines)

### Data formats
- Primary: JSON for frontend consumption
- CSV: Human-readable, Excel-compatible
- Parquet: Efficient storage for large datasets

---

## Testing checklist

Before deploying changes:
- [ ] Test on mobile (< 767px width)
- [ ] Test on tablet (768-900px)
- [ ] Test on desktop (> 900px)
- [ ] Verify all charts render correctly
- [ ] Check console for JavaScript errors
- [ ] Validate data freshness via manifest.json
- [ ] Confirm S3 uploads successful
- [ ] Review GitHub Actions workflow logs
- [ ] Check Twitter bot posts are still functioning

---

## Questions to resolve

1. **Shohei section**: What metrics are most important to highlight? Should we show game-by-game trends or season totals?

2. **Pitcher tables**: Should we filter by minimum innings pitched (e.g., only pitchers with 10+ IP)?

3. **Team hitting cards**: Should league rank be displayed as ordinal (2nd) or fraction (2/30)?

4. **Eephus filter**: Are there other pitch types to exclude? (Intentional balls, etc.)

5. **CSS organization**: Should we create separate CSS files for different components (tables, cards, charts)?

---

## Future enhancements (beyond current scope)

- Add playoff probability model
- Historical comparison tool (compare to past championship teams)
- Player injury tracking and impact analysis
- Opponent scouting reports
- Game-by-game predictions
- Social media sentiment tracking
- Interactive pitch location heatmaps
- Bullpen usage and rest days analysis
