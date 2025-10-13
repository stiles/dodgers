# LA Dodgers Historical Game Data Fetcher

This script fetches historical game-by-game data for the LA Dodgers (and Brooklyn Dodgers/Robins) from Baseball Reference for the years 1925 to present.

## Features

- **Complete Historical Coverage**: Fetches data from 1925 to the current year
- **Team Name Handling**: Automatically handles the transition from Brooklyn Dodgers/Robins (BRO) to Los Angeles Dodgers (LAD) in 1958
- **Robust Error Handling**: Gracefully handles network errors, missing data, and parsing issues
- **Multiple Output Formats**: Saves data in CSV, JSON, and Parquet formats
- **S3 Integration**: Optional upload to AWS S3
- **Command Line Interface**: Flexible options for different use cases
- **Test Mode**: Test with a single year before running full historical fetch

## Installation

Ensure you have the required Python packages:

```bash
pip install pandas requests beautifulsoup4 boto3 lxml html5lib
```

## Usage

### Basic Usage

Fetch all historical data from 1925 to present:

```bash
python 29_fetch_historical_standings.py
```

### Command Line Options

```bash
python 29_fetch_historical_standings.py [OPTIONS]
```

**Options:**

- `--start-year YEAR`: First year to fetch data for (default: 1925)
- `--end-year YEAR`: Last year to fetch data for (default: current year)
- `--output-dir DIR`: Output directory for data files (default: data/standings)
- `--no-s3`: Skip uploading to S3 even if credentials are available
- `--test-year YEAR`: Test mode - fetch data for a single year only
- `--delay SECONDS`: Delay between requests in seconds (default: 1.0)

### Examples

**Test with a single year:**
```bash
python 29_fetch_historical_standings.py --test-year 2024
```

**Fetch data for a specific range:**
```bash
python 29_fetch_historical_standings.py --start-year 1955 --end-year 1965
```

**Fetch recent data only:**
```bash
python 29_fetch_historical_standings.py --start-year 2020
```

**Save to custom directory without S3 upload:**
```bash
python 29_fetch_historical_standings.py --output-dir /path/to/custom/dir --no-s3
```

**Use faster requests (be respectful to Baseball Reference):**
```bash
python 29_fetch_historical_standings.py --delay 0.5
```

## Output Data

The script generates three files in the specified output directory:

1. **CSV**: `dodgers_standings_YYYY_present.csv`
2. **JSON**: `dodgers_standings_YYYY_present.json`
3. **Parquet**: `dodgers_standings_YYYY_present.parquet`

### Data Columns

The output includes the following columns (when available):

- `gm`: Game number
- `game_date`: Date of the game (YYYY-MM-DD format)
- `home_away`: Whether the game was home or away
- `opp`: Opponent team
- `result`: Game result (W/L)
- `r`: Runs scored by Dodgers
- `ra`: Runs allowed by Dodgers
- `record`: Team record (wins-losses)
- `rank`: Team ranking in division/league
- `gb`: Games back from first place
- `time`: Game duration
- `time_minutes`: Game duration in minutes
- `day_night`: Day or night game
- `attendance`: Game attendance
- `year`: Season year
- `wins`: Cumulative wins (calculated)
- `losses`: Cumulative losses (calculated)
- `win_pct`: Win percentage (calculated)

## S3 Upload

If AWS credentials are available as environment variables, the script will automatically upload the generated files to S3:

```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
```

**S3 Configuration:**
- Bucket: `stilesdata.com`
- Path: `dodgers/data/standings/`

Use `--no-s3` flag to disable S3 upload.

## Error Handling

The script includes robust error handling:

- **Network Issues**: Retries and continues with next year
- **Parsing Errors**: Logs warnings and continues
- **Missing Data**: Handles years with no data gracefully
- **Column Variations**: Adapts to different table structures across years

Failed years are logged at the end for review.

## Rate Limiting

The script includes a 1-second delay between requests by default to be respectful to Baseball Reference's servers. You can adjust this with the `--delay` parameter, but please be considerate.

## Historical Context

- **1925-1957**: Brooklyn Dodgers/Robins (team code: BRO)
- **1958-present**: Los Angeles Dodgers (team code: LAD)

The script automatically handles this transition and fetches data from the appropriate Baseball Reference URLs.

## Troubleshooting

**Common Issues:**

1. **Network timeouts**: Try increasing the delay between requests
2. **Missing years**: Some early years may not have complete data on Baseball Reference
3. **Column mismatches**: The script adapts to different table structures, but some very old years may have issues

**Logging:**

The script provides detailed logging. Check the console output for:
- Progress updates
- Error messages
- Summary statistics
- Failed years

## Testing

Use the test mode to verify functionality before running the full historical fetch:

```bash
python 29_fetch_historical_standings.py --test-year 2024
```

Or use the separate test script:

```bash
python test_historical_fetch.py
```

## Performance

- **Full historical fetch (1925-2025)**: ~100 years × 1 second delay = ~2 minutes
- **Recent years only (2020-2025)**: ~6 seconds
- **Single year test**: ~1-2 seconds

The script is designed to be respectful to Baseball Reference while being efficient for your data needs.
