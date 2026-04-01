# Milestone 1: Add a manifest (implementation guide)

**Goal**: One consistent way to locate datasets. No data source changes yet.

## What we're building

A single JSON file committed to the repo that maps dataset IDs to URLs and metadata. Both Jekyll and `dashboard.js` will use this manifest instead of hardcoding paths.

## Manifest schema

Location: `data/manifest.json` (published to S3 and committed to repo)

```json
{
  "version": "1.0",
  "last_updated": "2026-02-05T15:30:00-08:00",
  "season": "2025",
  "phase": "offseason",
  "postseason_active": false,
  "datasets": [
    {
      "id": "standings_1958_present",
      "version": "v1",
      "url": "https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.json",
      "content_type": "application/json",
      "last_updated": "2026-02-05T15:30:00-08:00",
      "schema_version": "1.0",
      "description": "Game-by-game standings 1958-present",
      "cadence": "regular_season_daily",
      "source": "baseball_reference_scrape"
    }
  ]
}
```

### Top-level fields

- `version`: Manifest format version (start with `"1.0"`)
- `last_updated`: ISO timestamp when manifest was last published
- `season`: Current MLB season year (string)
- `phase`: One of `"regular_season"`, `"postseason"`, `"offseason"`
- `postseason_active`: Boolean flag for homepage postseason section visibility

### Dataset entry fields

- `id`: Stable identifier (e.g. `"standings_1958_present"`, `"postseason_players_current"`)
- `version`: Dataset schema version (e.g. `"v1"`, `"v2"`)
- `url`: Full URL where the dataset is hosted
- `content_type`: MIME type
- `last_updated`: ISO timestamp when this dataset was last refreshed
- `schema_version`: Optional reference to a schema doc
- `description`: Human-readable description
- `cadence`: When this dataset updates (e.g. `"regular_season_daily"`, `"postseason_only"`, `"offseason_monthly"`)
- `source`: Where the data originates (e.g. `"mlb_statsapi"`, `"baseball_savant"`, `"baseball_reference_scrape"`)

## Implementation tasks

### Task 1.1: Create manifest generator script

Create `scripts/99_publish_manifest.py`:

```python
#!/usr/bin/env python
"""
Generate and publish the data manifest.
This script reads metadata from existing outputs and consolidates into manifest.json.
"""
import os
import json
import boto3
from datetime import datetime, timezone
import pytz

# Configuration
OUTPUT_FILE = "data/manifest.json"
S3_BUCKET = "stilesdata.com"
S3_KEY = "dodgers/data/manifest.json"

def get_pacific_time():
    """Return current Pacific time as ISO string."""
    pacific = pytz.timezone('US/Pacific')
    return datetime.now(pacific).isoformat()

def detect_season_phase():
    """
    Detect current season phase.
    TODO: implement actual MLB schedule check via StatsAPI.
    For now, return a sensible default based on date.
    """
    now = datetime.now()
    month = now.month
    
    # Simple heuristic (will be replaced with API check)
    if month in [11, 12, 1, 2]:
        return "offseason"
    elif month == 10:
        return "postseason"
    else:
        return "regular_season"

def build_manifest():
    """Build the manifest structure."""
    phase = detect_season_phase()
    season = str(datetime.now().year)
    
    manifest = {
        "version": "1.0",
        "last_updated": get_pacific_time(),
        "season": season,
        "phase": phase,
        "postseason_active": phase == "postseason",
        "datasets": []
    }
    
    # Dataset definitions (migrated from inventory)
    # For v1, we're just wrapping existing URLs
    datasets = [
        {
            "id": "standings_1958_present",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Game-by-game standings 1958-present",
            "cadence": "regular_season_daily",
            "source": "baseball_reference_scrape"
        },
        {
            "id": "standings_1958_present_optimized",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present_optimized.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Optimized standings (year, gm, win_pct, gb only)",
            "cadence": "regular_season_daily",
            "source": "baseball_reference_scrape"
        },
        {
            "id": "wins_losses_current",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/dodgers_wins_losses_current.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Current season wins/losses/run differential",
            "cadence": "regular_season_daily",
            "source": "baseball_savant"
        },
        {
            "id": "schedule_current",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/dodgers_schedule.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Last 10 games and next 10 games",
            "cadence": "regular_season_daily",
            "source": "baseball_reference_scrape"
        },
        {
            "id": "all_teams_standings_current",
            "version": "v1",
            "url": f"https://stilesdata.com/dodgers/data/standings/all_teams_standings_metrics_{season}.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Current year standings for all MLB teams",
            "cadence": "regular_season_daily",
            "source": "mlb_statsapi"
        },
        {
            "id": "mlb_team_attendance",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/mlb_team_attendance.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "MLB attendance by team",
            "cadence": "regular_season_weekly",
            "source": "baseball_reference_scrape"
        },
        {
            "id": "player_batting_current",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_current_table.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Current season player batting stats",
            "cadence": "regular_season_daily",
            "source": "mlb_bdfed"
        },
        {
            "id": "xwoba_current",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/batting/dodgers_xwoba_current.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Rolling 100 PA xwOBA per player",
            "cadence": "regular_season_daily",
            "source": "baseball_savant"
        },
        {
            "id": "shohei_home_runs",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/batting/shohei_home_runs_cumulative_timeseries_combined.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Shohei Ohtani cumulative home runs",
            "cadence": "regular_season_daily",
            "source": "mlb_bdfed"
        },
        {
            "id": "shohei_stolen_bases",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/batting/shohei_stolen_bases_cumulative_timeseries_combined.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Shohei Ohtani cumulative stolen bases",
            "cadence": "regular_season_daily",
            "source": "mlb_bdfed"
        },
        {
            "id": "historic_batting_gamelogs",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/batting/archive/dodgers_historic_batting_gamelogs.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Historical batting game logs",
            "cadence": "regular_season_daily",
            "source": "baseball_reference_scrape"
        },
        {
            "id": "historic_pitching_gamelogs",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/pitching/dodgers_historic_pitching_gamelogs_1958-present.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Historical pitching game logs",
            "cadence": "regular_season_daily",
            "source": "baseball_reference_scrape"
        },
        {
            "id": "shohei_pitch_mix",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/pitching/shohei_ohtani_pitch_mix.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Shohei Ohtani pitch type distribution",
            "cadence": "regular_season_daily",
            "source": "baseball_savant"
        },
        {
            "id": "shohei_pitches",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/pitching/shohei_ohtani_pitches.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Shohei Ohtani pitch-by-pitch data",
            "cadence": "regular_season_daily",
            "source": "baseball_savant"
        },
        {
            "id": "umpire_summary",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/summary/umpire_summary.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Umpire scorecard summary",
            "cadence": "regular_season_daily",
            "source": "baseball_savant"
        },
        {
            "id": "postseason_players_current",
            "version": "v1",
            "url": f"https://stilesdata.com/dodgers/data/postseason/dodgers_postseason_stats_{season}.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Current postseason player stats",
            "cadence": "postseason_only",
            "source": "mlb_statsapi"
        },
        {
            "id": "postseason_series_current",
            "version": "v1",
            "url": f"https://stilesdata.com/dodgers/data/postseason/dodgers_postseason_series_{season}.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Current postseason series journey",
            "cadence": "postseason_only",
            "source": "mlb_statsapi"
        },
        {
            "id": "wins_projection",
            "version": "v1",
            "url": "https://stilesdata.com/dodgers/data/standings/dodgers_wins_projection_timeseries.json",
            "content_type": "application/json",
            "last_updated": get_pacific_time(),
            "description": "Projected final wins (simulation)",
            "cadence": "regular_season_daily",
            "source": "derived"
        }
    ]
    
    manifest["datasets"] = datasets
    return manifest

def main():
    """Generate and publish manifest."""
    manifest = build_manifest()
    
    # Write locally
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"✅ Manifest written to {OUTPUT_FILE}")
    
    # Upload to S3
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    if is_github_actions:
        session = boto3.Session(
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name="us-west-1"
        )
    else:
        session = boto3.Session(profile_name="haekeo", region_name="us-west-1")
    
    s3 = session.resource('s3')
    s3.Bucket(S3_BUCKET).upload_file(OUTPUT_FILE, S3_KEY, ExtraArgs={'ContentType': 'application/json'})
    print(f"✅ Manifest uploaded to s3://{S3_BUCKET}/{S3_KEY}")

if __name__ == "__main__":
    main()
```

### Task 1.2: Add manifest generation to fetch workflow

Update `.github/workflows/fetch.yml` to run the manifest script after all datasets are published:

```yaml
- name: Publish manifest
  run: python scripts/99_publish_manifest.py
```

Place this step **after** all other data scripts but **before** the Jekyll build, so the manifest is available at build time.

### Task 1.3: Create frontend manifest loader

Create `assets/js/manifest_loader.js`:

```javascript
/**
 * Manifest loader for consistent dataset access
 */

let manifestCache = null;

/**
 * Fetch and cache the manifest
 * @returns {Promise<Object>} The manifest object
 */
export async function getManifest() {
  if (manifestCache) {
    return manifestCache;
  }
  
  const manifestUrl = 'https://stilesdata.com/dodgers/data/manifest.json';
  
  try {
    const response = await fetch(manifestUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch manifest: ${response.status}`);
    }
    manifestCache = await response.json();
    console.log(`📋 Manifest loaded (v${manifestCache.version}, phase: ${manifestCache.phase})`);
    return manifestCache;
  } catch (error) {
    console.error('❌ Failed to load manifest:', error);
    throw error;
  }
}

/**
 * Get a dataset URL by ID
 * @param {string} datasetId - The dataset identifier
 * @returns {Promise<string>} The dataset URL
 */
export async function getDatasetUrl(datasetId) {
  const manifest = await getManifest();
  const dataset = manifest.datasets.find(d => d.id === datasetId);
  
  if (!dataset) {
    throw new Error(`Dataset not found: ${datasetId}`);
  }
  
  return dataset.url;
}

/**
 * Fetch a dataset by ID
 * @param {string} datasetId - The dataset identifier
 * @returns {Promise<Object>} The parsed JSON dataset
 */
export async function fetchDataset(datasetId) {
  const url = await getDatasetUrl(datasetId);
  
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch dataset ${datasetId}: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`❌ Failed to load dataset ${datasetId}:`, error);
    throw error;
  }
}

/**
 * Check if postseason section should be visible
 * @returns {Promise<boolean>}
 */
export async function isPostseasonActive() {
  const manifest = await getManifest();
  return manifest.postseason_active === true;
}
```

### Task 1.4: Update one consumer as proof-of-concept

Update the postseason section in `assets/js/dashboard.js` to use the manifest loader:

**Before:**
```javascript
const postseasonStatsUrl = 'https://stilesdata.com/dodgers/data/postseason/dodgers_postseason_stats_2025.json';
const postseasonSeriesUrl = 'https://stilesdata.com/dodgers/data/postseason/dodgers_postseason_series_2025.json';
```

**After:**
```javascript
import { fetchDataset, isPostseasonActive } from './manifest_loader.js';

// Check if postseason section should be shown
const showPostseason = await isPostseasonActive();
if (!showPostseason) {
  document.querySelector('.postseason-stats-section').style.display = 'none';
} else {
  const postseasonStats = await fetchDataset('postseason_players_current');
  const postseasonSeries = await fetchDataset('postseason_series_current');
  // ... rest of postseason rendering
}
```

## Testing checklist

- [ ] Run `python scripts/99_publish_manifest.py` locally
- [ ] Verify `data/manifest.json` is created
- [ ] Check manifest structure matches schema
- [ ] Verify manifest uploads to S3
- [ ] Test manifest fetch from `https://stilesdata.com/dodgers/data/manifest.json`
- [ ] Test manifest loader in browser console
- [ ] Verify postseason section hides when `postseason_active: false`
- [ ] Commit manifest generator script
- [ ] Update workflow to run manifest publisher

## Success criteria

- ✅ Manifest publishes successfully to S3 after each pipeline run
- ✅ Frontend can load and parse the manifest
- ✅ At least one dataset consumer (postseason section) successfully migrated to use manifest
- ✅ No hardcoded year references in the migrated consumer

## Next step

Once this milestone is complete, we can incrementally migrate the rest of `dashboard.js` to use `fetchDataset()` instead of hardcoded URLs (Milestone 2).
