# Milestones 3 & 4 Checklist

## ✅ Completed

### Milestone 3: Season-phase automation
- [x] Create MLB API-based season phase detector
- [x] Update manifest generator to use real detector
- [x] Define phase→datasets mapping configuration
- [x] Create phase-aware script orchestrator
- [x] Update fetch.yml workflow to use orchestrator
- [x] Add workflow_dispatch phase override input
- [x] Test with offseason mode
- [x] Verify manifest reflects correct phase

### Milestone 4: Postseason hardening
- [x] Remove year hardcoding from postseason heading
- [x] Add dynamic year insertion via JavaScript
- [x] Use manifest season value for display

## Files changed

### New files (3 scripts + 1 doc)
- `scripts/season_phase.py` - Phase detector
- `scripts/phase_config.py` - Phase config
- `scripts/run_phase_scripts.py` - Orchestrator
- `.cursor/docs/milestones_3_4_summary.md` - Summary

### Modified files (5)
- `.github/workflows/fetch.yml` - Uses orchestrator
- `scripts/99_publish_manifest.py` - Real phase detection
- `index.markdown` - Generic postseason heading
- `assets/js/dashboard.js` - Dynamic year
- `data/standings/*` - Updated by test run (can exclude from commit)

## Testing performed

✅ Phase detection works (7 games found, regular_season detected)  
✅ Offseason mode runs only 7 scripts  
✅ Manifest correctly shows phase + postseason_active  
✅ Manual override supported via CLI  
✅ Workflow supports phase_override input

## Ready to commit

Ignore the `data/standings/*` changes (from test run) and `__pycache__`:

```bash
git add .github/workflows/fetch.yml
git add scripts/season_phase.py scripts/phase_config.py scripts/run_phase_scripts.py
git add scripts/99_publish_manifest.py
git add index.markdown assets/js/dashboard.js
git add .cursor/docs/milestones_3_4_summary.md
```

Or:
```bash
git add -A
git reset data/standings/*
git reset scripts/__pycache__
```

## Next deployment expectations

When this deploys:
1. First workflow run will detect phase (currently regular_season)
2. Orchestrator will run appropriate 16 scripts
3. Manifest will be published with real phase data
4. Frontend will show "Postseason" (hidden during regular season)
5. When postseason comes: section appears with "Postseason 2026"
6. When offseason: section hidden, only 7 scripts run

## Optional: .gitignore update

Consider adding to `.gitignore`:
```
scripts/__pycache__/
*.pyc
```
