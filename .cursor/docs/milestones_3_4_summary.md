# Milestones 3 & 4 Implementation Summary

**Status**: ✅ COMPLETED

**Date**: April 1, 2026

## What we accomplished

Implemented season-phase automation and postseason hardening, eliminating the need for commenting/uncommenting scripts in workflows and removing all year hardcoding from the postseason section.

## Milestone 3: Season-phase detector + workflow orchestration

### New files created

1. **`scripts/season_phase.py`** (140 lines)
   - Queries MLB StatsAPI schedule endpoints
   - Detects phase: `regular_season`, `postseason`, or `offseason`
   - Looks 7 days ahead for upcoming games
   - Returns `(phase, postseason_active, season_year)` tuple

2. **`scripts/phase_config.py`** (110 lines)
   - Defines which scripts run in each phase
   - **Regular season**: 16 scripts (full pipeline)
   - **Postseason**: 5 scripts (postseason stats + roster/transactions)
   - **Offseason**: 7 scripts (roster, transactions, news, historical updates)
   - Provides `get_scripts_for_phase()` helper

3. **`scripts/run_phase_scripts.py`** (100 lines)
   - Phase-aware script orchestrator
   - Detects phase and runs appropriate scripts
   - Supports manual phase override via CLI arg
   - Comprehensive logging and error handling
   - Returns exit code 1 if any script fails

### Modified files

1. **`scripts/99_publish_manifest.py`**
   - Replaced date-based heuristic with real phase detector
   - Now imports `season_phase.detect_season_phase()`
   - Manifest reflects actual MLB schedule status

2. **`.github/workflows/fetch.yml`**
   - Replaced 20+ lines of commented scripts with single orchestrator call
   - Added `workflow_dispatch` input for manual phase override
   - Updated cron comment to clarify phase-based behavior

## Milestone 4: Postseason hardening

### Modified files

1. **`index.markdown`**
   - Removed hardcoded "Postseason 2025" heading
   - Changed to generic "Postseason" with id `#postseason-header`
   - Year now inserted dynamically by JavaScript

2. **`assets/js/dashboard.js`**
   - Imports `getCurrentSeason()` from manifest loader
   - Dynamically updates heading: `Postseason ${season}`
   - Year changes automatically based on manifest

## Key improvements

### 1. No more commented scripts
**Before:**
```yaml
- name: Run scripts
  run: |
    # python scripts/00_fetch_league_standings.py
    # python scripts/02_update_boxscores_archive.py
    # ...20 more commented lines...
    python scripts/19_fetch_roster.py
    # ...more comments...
```

**After:**
```yaml
- name: Run phase-aware data pipeline
  run: python scripts/run_phase_scripts.py
```

### 2. Real-time phase detection
**Before:** Simple date heuristic (month-based)  
**After:** Queries MLB StatsAPI for actual Dodgers schedule

### 3. Phase-appropriate execution
- **Regular season** (detected now): Runs 16 scripts
- **Postseason**: Runs 5 focused scripts
- **Offseason**: Runs 7 minimal scripts

### 4. No year hardcoding
- Postseason heading updates automatically
- Postseason dataset URLs resolve via manifest (already done in M1)
- Season year comes from phase detector, not `datetime.now().year`

## Testing results

✅ **Phase detection (current)**:
```
Phase: regular_season
Postseason Active: False
Season Year: 2026
Found 7 regular season games in next 7 days
```

✅ **Offseason mode test** (manual override):
```
Scripts to run: 7
✅ Successful: 7
❌ Failed: 0
```

✅ **Manifest generation**:
```json
{
  "version": "1.0",
  "phase": "regular_season",
  "postseason_active": false,
  "season": "2026"
}
```

## Workflow manual override

GitHub Actions now supports manual phase override:

1. Go to Actions → fetch workflow
2. Click "Run workflow"
3. Select override phase (or leave empty for auto-detect)
4. Pipeline runs appropriate scripts for that phase

Useful for:
- Testing offseason behavior during regular season
- Force-running postseason scripts during development
- Debugging phase-specific issues

## Files changed summary

### New
- `scripts/season_phase.py` - Phase detector
- `scripts/phase_config.py` - Phase→scripts mapping
- `scripts/run_phase_scripts.py` - Orchestrator

### Modified
- `scripts/99_publish_manifest.py` - Uses real detector
- `.github/workflows/fetch.yml` - Phase-aware execution
- `index.markdown` - Generic postseason heading
- `assets/js/dashboard.js` - Dynamic year insertion

## Next steps (future milestones)

With season phases now automated, future work can focus on:

1. **Dataset migrations**: Move standings/batting/pitching off Baseball Reference (Milestone 5)
2. **Better schedules**: Adjust cron based on detected phase
   - Regular season: 4x daily
   - Postseason: 2x daily
   - Offseason: Weekly
3. **Phase-specific tests**: Add CI tests that verify correct scripts run in each phase

## Commit message suggestion

```
feat: Add season-phase automation (Milestones 3 & 4)

- Create MLB API-based phase detector querying real schedule
- Define phase→datasets mapping (regular/postseason/offseason)
- Add orchestrator that runs appropriate scripts per phase
- Update workflow to use phase-aware runner (no more comments!)
- Remove year hardcoding from postseason section
- Add manual phase override for workflow_dispatch

The pipeline now automatically adjusts which scripts run based
on actual Dodgers schedule. No more commenting/uncommenting
scripts when the season ends or postseason begins.
```
