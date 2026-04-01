# ABS Challenge Tracking Plan

## Overview

MLB's Automated Balls & Strikes (ABS) challenge system is documented in the StatsAPI v1.1 feed. Teams can challenge ball/strike calls, and the system provides tracking at both the game level and individual pitch level.

## Data Discovered in Feed (Game 831803)

### Game-level tracking
Location: `gameData.absChallenges`

```json
{
  "hasChallenges": true,
  "away": {
    "usedSuccessful": 0,
    "usedFailed": 0,
    "remaining": 2
  },
  "home": {
    "usedSuccessful": 1,
    "usedFailed": 1,
    "remaining": 1
  }
}
```

### Pitch-level tracking
Location: `liveData.plays.allPlays[].playEvents[]` (when challenge occurs)

```json
{
  "details": {
    "hasReview": true,
    "call": {"code": "B", "description": "Ball"},
    // ... full pitch tracking data
  },
  "reviewDetails": {
    "isOverturned": false,
    "inProgress": false,
    "reviewType": "MJ",
    "challengeTeamId": 135
  }
}
```

## Implementation Plan

### Phase 1: Detection & Display

**Goal:** Show when ABS is enabled and display challenge counts

**Changes needed:**
1. Add ABS detection in game initialization
   - Check `gameData.absChallenges.hasChallenges`
   - Only process if `true`

2. Display challenge counts in scoreboard
   - Show remaining challenges per team
   - Format: `⚾ LAD 4 (H:1 E:0) [🤖 2]` where `[🤖 2]` = 2 remaining challenges
   - Alternative: `⚾ LAD 4 ⚖️1/2` (used 1 of 2 challenges)

3. Include in pre-game information
   - If ABS enabled, note: "🤖 ABS Challenge System Active (2 per team)"

**Code locations:**
- Detection: `fetch_live()` or game initialization (cli.py ~line 230)
- Display: `fmt_scoreboard()` (cli.py ~line 277)
- Pre-game: `print_game_summary()` (cli.py ~line 206)

### Phase 2: Challenge Event Display

**Goal:** Highlight when challenges occur during play-by-play

**Changes needed:**
1. Detect challenge in play events
   - Check `playEvent.reviewDetails` exists
   - Extract `isOverturned`, `reviewType`, `challengeTeamId`

2. Format challenge notifications
   - **Success (overturned):** `🤖⚡ ABS CHALLENGE by SD: Ball → Strike (OVERTURNED)`
   - **Failed (upheld):** `🤖 ABS Challenge by SD: Call stands - Ball (Challenge Lost)`
   - **In progress:** `🤖 ABS Challenge in progress...`

3. Update challenge counts live
   - Decrement `remaining` when challenge occurs
   - Increment `usedSuccessful` or `usedFailed` based on outcome

**Code locations:**
- Event detection: `process_play()` or pitch event handling (cli.py ~line 419)
- Display: Integrate with play description output (cli.py ~line 593)
- Count tracking: Maintain state in game stream context

### Phase 3: Historical Tracking

**Goal:** Show challenge history and statistics

**Changes needed:**
1. Track all challenges in a list
   ```python
   challenges = [
       {
           "inning": 5,
           "half": "top",
           "team": "SD", 
           "call": "Ball",
           "overturned": False,
           "batter": "Ryan Fitzgerald",
           "count": "1-0"
       }
   ]
   ```

2. Display on demand
   - `--verbose` mode: show all challenges with play context
   - Inning summaries: note if challenges occurred
   - End of game: show challenge summary stats

3. Include in `--dump` output
   - Full challenge log with timestamps
   - Success/failure rates per team

**Code locations:**
- Storage: Add to game state object
- Display: Add helper function `fmt_challenge_summary()`
- Dump: Integrate with existing `--dump` logic (cli.py ~line 901)

## Display Formats (Prioritized)

### Minimal (Default)
```
▲5  🤖 ABS Challenge by SD: Call stands - Ball
▲5  Ryan Fitzgerald pops out to second baseman Jake Cronenworth. (2-1, 4p)
────────────────────────────────────────────────
🏟️  ▲ Top 5
     ⚾ LAD  4  (H: 8 E:0) [🤖:2]
     ⚾ SD   0  (H: 2 E:0) [🤖:1]
```

### Verbose
```
▲5  🤖 ABS CHALLENGE (SD)
     Pitch: 89.9 mph Slider, called Ball
     Location: pX=-1.00, pZ=2.75 (zone 11)
     Result: Call STANDS (Challenge Lost)
     Remaining: SD 1, LAD 2
▲5  Ryan Fitzgerald pops out to second baseman Jake Cronenworth. (2-1, 4p)
```

### Scoreboard Variants

**Option A - Compact emoji:**
```
⚾ LAD  4  (H: 8 E:0) 🤖:2
⚾ SD   0  (H: 2 E:0) 🤖:1
```

**Option B - Success/Fail tracking:**
```
⚾ LAD  4  (H: 8 E:0) ⚖️:2 (0✓/0✗)
⚾ SD   0  (H: 2 E:0) ⚖️:1 (0✓/1✗)
```

**Option C - Minimal indicator:**
```
⚾ LAD  4  (H: 8 E:0) C:2
⚾ SD   0  (H: 2 E:0) C:1
```

## Edge Cases to Handle

1. **Game without ABS enabled**
   - `hasChallenges: false` or field missing
   - Don't show any ABS UI elements

2. **Challenge in progress**
   - `reviewDetails.inProgress: true`
   - Show waiting indicator, update when resolved

3. **No challenges remaining**
   - `remaining: 0`
   - Mark team as out of challenges: `🤖:0 ⛔`

4. **Multiple game types**
   - Spring Training (type "S") - likely testing ground
   - Regular season (type "R") - depends on MLB rollout
   - Check `gameData.game.type` for context

5. **Historical games**
   - ABS may not have existed in older games
   - Gracefully handle missing fields

## Configuration Options

Add to `~/.utilityman/config.toml`:

```toml
[abs]
enabled = true              # Show ABS data when available
show_in_scoreboard = true   # Include challenge count in scoreboard
verbose_challenges = false  # Show detailed challenge info
emoji = "🤖"                # Emoji for ABS challenges
```

## Testing Strategy

1. **Live games with ABS**
   - Monitor Spring Training 2026 games
   - Test with known gamePk: 831803

2. **Historical games without ABS**
   - Test 2025 regular season games
   - Ensure no errors when field missing

3. **Mock scenarios**
   - Challenge overturned (success)
   - Challenge upheld (failure)
   - Multiple challenges in one inning
   - Team runs out of challenges

## Technical Notes

- **Review type:** "MJ" appears to be the code for ABS challenges
- **Challenge team:** Use `challengeTeamId` to map to home/away
- **Pitch data:** Full Statcast data available for challenged pitches
- **State management:** Need to track challenges separately from feed since counts update asynchronously

## Rollout Approach

**Phase 1 (Quick Win):** Detection only
- Check if ABS enabled, print note in pre-game
- "🤖 ABS Challenge System Active"
- 1-2 hour implementation

**Phase 2 (Core Feature):** Challenge events
- Display when challenges occur
- Show outcome (overturned/upheld)
- Update challenge counts
- 3-4 hour implementation

**Phase 3 (Polish):** Integration
- Add to scoreboard display
- Verbose mode details
- Historical tracking
- 2-3 hour implementation

## Open Questions

1. **Challenge refresh rules?**
   - Do teams get additional challenges later in game?
   - Check for any `refresh` or `replenishment` fields

2. **Exact overturned call format?**
   - Need example where `isOverturned: true`
   - What's the updated call in `details`?

3. **reviewType codes?**
   - "MJ" = ABS challenge
   - What other review types exist?
   - Need to distinguish from manager challenges

4. **Regular season deployment?**
   - Is ABS in 2026 regular season?
   - Only certain ballparks?
   - Check `gameData.venue` for ABS-enabled parks
