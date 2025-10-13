#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers Historical Game-by-Game Data Fetcher, 1925-present

This script downloads the team's game-by-game data from Baseball Reference 
for all years from 1925 to the present and combines them into a comprehensive dataset.
"""

import os
import sys
import pandas as pd
import requests
from bs4 import BeautifulSoup
import boto3
from io import StringIO
import logging
import time
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
CURRENT_YEAR = datetime.now().year
START_YEAR = 1925
OUTPUT_DIR = "data/standings"
S3_BUCKET = "stilesdata.com"

# File paths
CSV_FILE = f"{OUTPUT_DIR}/dodgers_standings_1925_present.csv"
JSON_FILE = f"{OUTPUT_DIR}/dodgers_standings_1925_present.json"
PARQUET_FILE = f"{OUTPUT_DIR}/dodgers_standings_1925_present.parquet"

# S3 configuration
S3_KEY_CSV = "dodgers/data/standings/dodgers_standings_1925_present.csv"
S3_KEY_JSON = "dodgers/data/standings/dodgers_standings_1925_present.json"
S3_KEY_PARQUET = "dodgers/data/standings/dodgers_standings_1925_present.parquet"

# AWS session
session = boto3.Session(
    aws_access_key_id=os.getenv('MY_AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('MY_AWS_SECRET_ACCESS_KEY'),
    profile_name=os.getenv('MY_PERSONAL_PROFILE'),
)
s3 = session.resource('s3')


def fetch_year_data(year):
    """
    Fetch game-by-game data for a specific year from Baseball Reference.
    
    Args:
        year (int): The year to fetch data for
        
    Returns:
        pandas.DataFrame: Processed game data for the year
    """
    # Handle team name changes - Brooklyn Robins/Dodgers became LA Dodgers
    if year <= 1957:
        team_code = "BRO"  # Brooklyn Dodgers/Robins
    else:
        team_code = "LAD"  # Los Angeles Dodgers
    
    url = f"https://www.baseball-reference.com/teams/{team_code}/{year}-schedule-scores.shtml"
    
    try:
        logging.info(f"Fetching data for {year} from {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the schedule table
        tables = pd.read_html(StringIO(str(soup)))
        if not tables:
            logging.warning(f"No tables found for year {year}")
            return None
            
        # Get the first table (schedule/scores)
        src = tables[0]
        
        # Filter out header rows and preview games
        src = src.query("Tm != 'Tm' and Inn != 'Game Preview, and Matchups'").copy()
        
        if src.empty:
            logging.warning(f"No valid game data found for year {year}")
            return None
            
        # Clean up columns - handle variations in column structure across years
        src = src.dropna(how='all', axis=1)  # Remove completely empty columns
        
        # Drop problematic columns that exist in some years
        columns_to_drop = ['Streak', 'Orig. Scheduled']
        for col in columns_to_drop:
            if col in src.columns:
                src = src.drop(col, axis=1)
        
        # Standardize column names based on what's available
        column_mapping = {}
        for col in src.columns:
            if 'Unnamed' in str(col):
                col_pos = src.columns.get_loc(col)
                if col_pos == 2:
                    column_mapping[col] = 'home_away_indicator'
                elif col_pos == 4 or (col_pos == 4 and 'home_away' not in [column_mapping.get(c) for c in src.columns[:col_pos]]):
                    column_mapping[col] = 'home_away'
                    
        src = src.rename(columns=column_mapping)
        
        # Assign year
        src = src.assign(year=year)
        
        # Standardize column names and handle duplicates
        new_columns = []
        seen_columns = set()
        
        for col in src.columns:
            # Standardize the column name
            std_col = str(col).lower().replace("/", "_").replace("-", "_")
            
            # Handle specific cases to avoid duplicates
            if std_col == 'w_l':
                if 'result' not in seen_columns:
                    std_col = 'result'
                elif 'record' not in seen_columns:
                    std_col = 'record'
                else:
                    std_col = f'w_l_{len([c for c in seen_columns if c.startswith("w_l")])}'
            
            # Ensure uniqueness
            original_std_col = std_col
            counter = 1
            while std_col in seen_columns:
                std_col = f"{original_std_col}_{counter}"
                counter += 1
                
            new_columns.append(std_col)
            seen_columns.add(std_col)
            
        src.columns = new_columns
        
        # Map actual columns to standard names dynamically
        actual_columns = list(src.columns)
        standard_column_mapping = {}
        
        # Create a flexible mapping based on common patterns
        for i, col in enumerate(actual_columns):
            if col in ['gm#', 'gm']:
                standard_column_mapping[col] = 'gm'
            elif col == 'date':
                standard_column_mapping[col] = 'date'
            elif col in ['tm', 'team']:
                standard_column_mapping[col] = 'tm'
            elif col in ['home_away'] and 'home_away' not in standard_column_mapping.values():
                standard_column_mapping[col] = 'home_away'
            elif col in ['home_away_indicator'] and 'home_away' not in standard_column_mapping.values():
                standard_column_mapping[col] = 'home_away'
            elif col in ['opp', 'opponent']:
                standard_column_mapping[col] = 'opp'
            elif col in ['result'] or (col.startswith('w_l') and 'result' not in standard_column_mapping.values()):
                standard_column_mapping[col] = 'result'
            elif col in ['r', 'runs']:
                standard_column_mapping[col] = 'r'
            elif col in ['ra', 'runs_allowed']:
                standard_column_mapping[col] = 'ra'
            elif col in ['inn', 'innings']:
                standard_column_mapping[col] = 'inn'
            elif col in ['record'] or (col.startswith('w_l') and 'record' not in standard_column_mapping.values()):
                standard_column_mapping[col] = 'record'
            elif col == 'rank':
                standard_column_mapping[col] = 'rank'
            elif col == 'gb':
                standard_column_mapping[col] = 'gb'
            elif col == 'win':
                standard_column_mapping[col] = 'win'
            elif col == 'loss':
                standard_column_mapping[col] = 'loss'
            elif col == 'save':
                standard_column_mapping[col] = 'save'
            elif col == 'time':
                standard_column_mapping[col] = 'time'
            elif col in ['d_n', 'day_night']:
                standard_column_mapping[col] = 'day_night'
            elif col in ['attendance', 'att']:
                standard_column_mapping[col] = 'attendance'
            elif col in ['cli', 'leverage']:
                standard_column_mapping[col] = 'cli'
            elif col == 'year':
                standard_column_mapping[col] = 'year'
                
        # Apply the mapping
        src = src.rename(columns=standard_column_mapping)
        
        # Handle duplicate columns by keeping only the first occurrence
        if src.columns.duplicated().any():
            # Get unique columns while preserving order
            seen = set()
            unique_cols = []
            for col in src.columns:
                if col not in seen:
                    unique_cols.append(col)
                    seen.add(col)
                else:
                    unique_cols.append(f"{col}_dup")
            src.columns = unique_cols
            
        # Ensure we have minimum required columns
        required_columns = ['gm', 'date', 'year']
        missing_required = [col for col in required_columns if col not in src.columns]
        if missing_required:
            logging.warning(f"Missing required columns for year {year}: {missing_required}")
            return None
        
        # Basic data cleaning
        if 'gm' in src.columns:
            src["gm"] = pd.to_numeric(src["gm"], errors='coerce')
            
        if 'year' in src.columns:
            src["year"] = src["year"].astype(str)
            
        # Process date if available
        if 'date' in src.columns:
            try:
                # Split date if it contains weekday
                if src["date"].str.contains(", ").any():
                    src[["weekday", "date_clean"]] = src["date"].str.split(", ", expand=True)
                    src["date"] = src["date_clean"]
                    
                # Remove game number indicators
                src["date"] = src["date"].str.replace(r" \(\d+\)", "", regex=True)
                
                # Create full date
                src["game_date"] = pd.to_datetime(
                    src["date"] + ", " + src["year"], 
                    format="%b %d, %Y", 
                    errors='coerce'
                ).dt.strftime('%Y-%m-%d')
                
            except Exception as e:
                logging.warning(f"Date processing failed for year {year}: {e}")
                src["game_date"] = None
                
        # Clean home/away indicator
        if 'home_away' in src.columns:
            src.loc[src['home_away'] == "@", "home_away"] = "away"
            src.loc[src['home_away'].isna(), "home_away"] = "home"
            
        # Process games back if available
        if 'gb' in src.columns:
            try:
                src["gb"] = (
                    src["gb"].astype(str)
                    .str.replace("up ", "up", regex=False)
                    .str.replace("up", "+", regex=False)
                    .str.replace("Tied", "0", regex=False)
                )
                src["gb"] = src["gb"].apply(
                    lambda x: float(x) if str(x).startswith("+") else -float(x) if str(x) != '0' and str(x) != 'nan' else 0
                )
            except Exception as e:
                logging.warning(f"Games back processing failed for year {year}: {e}")
                
        # Convert numeric columns
        numeric_columns = ["r", "ra", "attendance", "rank"]
        for col in numeric_columns:
            if col in src.columns:
                src[col] = pd.to_numeric(src[col], errors='coerce').fillna(0).astype(int)
                
        # Process time if available
        if 'time' in src.columns:
            try:
                src["time"] = src["time"].astype(str) + ":00"
                src["time_minutes"] = pd.to_timedelta(src["time"], errors='coerce').dt.total_seconds() / 60
                src["time_minutes"] = src["time_minutes"].fillna(0).astype(int)
            except Exception as e:
                logging.warning(f"Time processing failed for year {year}: {e}")
                
        # Calculate wins and losses from record if available
        if 'record' in src.columns:
            try:
                record_split = src['record'].str.split('-', expand=True)
                if len(record_split.columns) >= 2:
                    src['wins'] = pd.to_numeric(record_split[0], errors='coerce').fillna(0).astype(int)
                    src['losses'] = pd.to_numeric(record_split[1], errors='coerce').fillna(0).astype(int)
                    src['win_pct'] = (src['wins'] / src['gm']).round(3)
            except Exception as e:
                logging.warning(f"Record processing failed for year {year}: {e}")
                
        # Select final columns
        final_columns = [
            "gm", "game_date", "home_away", "opp", "result", "r", "ra", 
            "record", "rank", "gb", "time", "time_minutes", "day_night", 
            "attendance", "year"
        ]
        
        # Add calculated columns if they exist
        if 'wins' in src.columns:
            final_columns.extend(["wins", "losses", "win_pct"])
            
        # Only include columns that exist
        available_columns = [col for col in final_columns if col in src.columns]
        
        if not available_columns:
            logging.warning(f"No available columns found for year {year}")
            return None
            
        try:
            src_df = src[available_columns].copy()
        except Exception as e:
            logging.error(f"Column selection failed for year {year}: {e}")
            raise
        
        # Remove rows with no game number (likely totals or headers)
        if 'gm' in src_df.columns:
            src_df = src_df.dropna(subset=['gm'])
            src_df = src_df[src_df['gm'] > 0]
        
        logging.info(f"Successfully processed {len(src_df)} games for year {year}")
        return src_df
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error fetching data for year {year}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error processing data for year {year}: {e}")
        return None


def fetch_all_historical_data(start_year=START_YEAR, end_year=CURRENT_YEAR, delay=1.0):
    """
    Fetch game-by-game data for all years from start_year to end_year.
    
    Args:
        start_year (int): First year to fetch (default: 1925)
        end_year (int): Last year to fetch (default: current year)
        delay (float): Delay between requests in seconds (default: 1.0)
        
    Returns:
        pandas.DataFrame: Combined data for all years
    """
    all_data = []
    failed_years = []
    
    for year in range(start_year, end_year + 1):
        try:
            year_data = fetch_year_data(year)
            if year_data is not None and not year_data.empty:
                all_data.append(year_data)
            else:
                failed_years.append(year)
                
            # Be respectful to Baseball Reference - add delay between requests
            time.sleep(delay)
            
        except Exception as e:
            logging.error(f"Failed to fetch data for year {year}: {e}")
            failed_years.append(year)
            continue
            
    if failed_years:
        logging.warning(f"Failed to fetch data for years: {failed_years}")
        
    if not all_data:
        logging.error("No data was successfully fetched for any year")
        return None
        
    # Combine all years
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values(['year', 'gm'], ascending=[False, True]).reset_index(drop=True)
    
    logging.info(f"Successfully combined data for {len(all_data)} years, total games: {len(combined_df)}")
    return combined_df


def save_data(df, base_path):
    """
    Save DataFrame to multiple formats (CSV, JSON, Parquet).
    
    Args:
        df (pandas.DataFrame): Data to save
        base_path (str): Base path without extension
    """
    try:
        # Save CSV
        csv_path = f"{base_path}.csv"
        df.to_csv(csv_path, index=False)
        logging.info(f"Saved CSV: {csv_path}")
        
        # Save JSON
        json_path = f"{base_path}.json"
        df.to_json(json_path, orient="records", indent=4)
        logging.info(f"Saved JSON: {json_path}")
        
        # Save Parquet
        parquet_path = f"{base_path}.parquet"
        df.to_parquet(parquet_path, index=False)
        logging.info(f"Saved Parquet: {parquet_path}")
        
        return csv_path, json_path, parquet_path
        
    except Exception as e:
        logging.error(f"Error saving data: {e}")
        raise


def upload_to_s3(local_files, s3_keys):
    """
    Upload files to S3.
    
    Args:
        local_files (list): List of local file paths
        s3_keys (list): List of corresponding S3 keys
    """
    try:
        for local_file, s3_key in zip(local_files, s3_keys):
            if os.path.exists(local_file):
                s3.Bucket(S3_BUCKET).upload_file(local_file, s3_key)
                logging.info(f"Uploaded {local_file} to s3://{S3_BUCKET}/{s3_key}")
            else:
                logging.warning(f"Local file not found: {local_file}")
                
    except Exception as e:
        logging.error(f"Error uploading to S3: {e}")
        raise


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch historical LA Dodgers game-by-game data from Baseball Reference"
    )
    parser.add_argument(
        "--start-year", 
        type=int, 
        default=START_YEAR,
        help=f"First year to fetch data for (default: {START_YEAR})"
    )
    parser.add_argument(
        "--end-year", 
        type=int, 
        default=CURRENT_YEAR,
        help=f"Last year to fetch data for (default: {CURRENT_YEAR})"
    )
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default=OUTPUT_DIR,
        help=f"Output directory for data files (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--no-s3", 
        action="store_true",
        help="Skip uploading to S3 even if credentials are available"
    )
    parser.add_argument(
        "--test-year", 
        type=int,
        help="Test mode: fetch data for a single year only"
    )
    parser.add_argument(
        "--delay", 
        type=float, 
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
    )
    
    return parser.parse_args()


def main():
    """
    Main function to fetch, process, and save historical Dodgers game data.
    """
    args = parse_arguments()
    
    try:
        # Use command line arguments
        output_dir = args.output_dir
        start_year = args.start_year
        end_year = args.end_year
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"Output directory: {output_dir}")
        
        # Test mode - single year
        if args.test_year:
            logging.info(f"Test mode: fetching data for year {args.test_year}")
            df = fetch_year_data(args.test_year)
            
            if df is not None and not df.empty:
                logging.info(f"✅ Successfully fetched {len(df)} games for {args.test_year}")
                logging.info(f"Columns: {list(df.columns)}")
                if 'game_date' in df.columns:
                    logging.info(f"Date range: {df['game_date'].min()} to {df['game_date'].max()}")
                
                # Save test data
                base_path = f"{output_dir}/dodgers_test_{args.test_year}"
                save_data(df, base_path)
            else:
                logging.error(f"❌ Failed to fetch data for {args.test_year}")
                sys.exit(1)
            return
        
        # Full historical fetch
        logging.info(f"Starting data fetch for years {start_year}-{end_year}")
        df = fetch_all_historical_data(start_year, end_year, args.delay)
        
        if df is None or df.empty:
            logging.error("No data was fetched. Exiting.")
            sys.exit(1)
            
        # Add some summary statistics
        logging.info(f"Total games fetched: {len(df)}")
        logging.info(f"Years covered: {df['year'].min()} to {df['year'].max()}")
        logging.info(f"Games per year range: {df.groupby('year').size().min()} to {df.groupby('year').size().max()}")
        
        # Save data locally
        base_path = f"{output_dir}/dodgers_standings_{start_year}_present"
        csv_file, json_file, parquet_file = save_data(df, base_path)
        
        # Upload to S3 if credentials are available and not disabled
        if not args.no_s3 and os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
            local_files = [csv_file, json_file, parquet_file]
            s3_keys = [S3_KEY_CSV, S3_KEY_JSON, S3_KEY_PARQUET]
            upload_to_s3(local_files, s3_keys)
        else:
            if args.no_s3:
                logging.info("S3 upload disabled by --no-s3 flag")
            else:
                logging.warning("AWS credentials not found. Skipping S3 upload.")
            
        logging.info("Script completed successfully!")
        
    except KeyboardInterrupt:
        logging.info("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

