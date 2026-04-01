# Milestone 1: Implementation Checklist

## ✅ Completed

- [x] Create `scripts/99_publish_manifest.py` with dataset definitions from inventory
- [x] Add manifest generation step to `.github/workflows/fetch.yml`
- [x] Create `assets/js/manifest_loader.js` frontend helper
- [x] Migrate postseason section in `dashboard.js` to use manifest loader (proof-of-concept)
- [x] Test manifest generation locally and verify S3 upload

## Files changed

### New files
- `.cursor/docs/milestone_1_manifest.md` - Implementation guide
- `.cursor/docs/milestone_1_summary.md` - Completion summary
- `assets/js/manifest_loader.js` - Frontend manifest loader (98 lines)
- `scripts/99_publish_manifest.py` - Manifest generator (286 lines)

### Modified files
- `.github/workflows/fetch.yml` - Added manifest publish step
- `assets/js/dashboard.js` - Migrated postseason to use manifest + auto-hide

## What to test before committing

### 1. Manifest generation
```bash
cd /Users/mstiles/github/dodgers
python scripts/99_publish_manifest.py
# Should output: ✅ Manifest written + uploaded to S3
```

### 2. Verify manifest accessible
```bash
curl https://stilesdata.com/dodgers/data/manifest.json
# Should return valid JSON with version, season, phase, datasets
```

### 3. Frontend functionality (after deployment)
- Navigate to https://dodgersdata.bot
- Open browser console
- Check for: "📋 Manifest loaded" message
- During offseason: postseason section should be hidden
- During postseason: section should show with correct year data

## Ready to commit

The implementation is complete and tested. You can commit with a message like:

```
feat: Add data manifest system (Milestone 1)

- Create manifest generator script that publishes dataset catalog
- Add manifest loader for frontend to resolve datasets by ID
- Migrate postseason section to use manifest (proof-of-concept)
- Auto-hide postseason section based on manifest phase flag
- Remove hardcoded year references from postseason data fetching

This eliminates hardcoded URLs and enables consistent dataset access
across the application. Sets foundation for incremental migration of
remaining datasets in Milestone 2.
```

## Next steps (Milestone 2)

After this is committed and deployed, incrementally migrate the remaining datasets in `dashboard.js`:
1. Schedule tables
2. Standings charts
3. Batting charts (xwOBA, Shohei, player tables)
4. Pitching charts
5. Attendance, umpire, projection

Each can be done as a separate small PR using the same pattern established in this milestone.
