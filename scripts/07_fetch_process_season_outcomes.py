#!/usr/bin/env python
# coding: utf-8

"""
LA Dodgers season outcomes
> This notebook downloads the team's past season outcomes table from [Baseball Reference](https://www.baseball-reference.com/teams/LAD/) and outputs the data to CSV, JSON and Parquet formats for later analysis and visualization.
"""

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Determine if running in a GitHub Actions environment
is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'

# AWS credentials and session initialization
aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
aws_region = "us-west-1"

# Conditional AWS session creation based on the environment
if is_github_actions:
    # In GitHub Actions, use environment variables directly
    session = boto3.Session(
        aws_access_key_id=aws_key_id,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
else:
    # Locally, use a specific profile
    session = boto3.Session(profile_name="haekeo", region_name=aws_region)

s3_resource = session.resource("s3")

# Base directory settings
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(base_dir, 'data', 'standings')
os.makedirs(data_dir, exist_ok=True)

year = pd.to_datetime("now").strftime("%Y")

"""
Fetch
"""


url = "https://www.baseball-reference.com/teams/LAD/"
try:
    history_df = pd.read_html(url)[0]
    logging.info("Data fetched successfully from Baseball Reference.")
except Exception as e:
    logging.error(f"Failed to fetch data: {e}")
    raise

# Data cleaning and preparation
history_df.columns = [col.lower().replace(" ", "_") for col in history_df.columns]
history_df = history_df.query("year > 1957")

history_df.columns = [
    "year",
    "team",
    "league",
    "games",
    "wins",
    "losses",
    "ties",
    "win_pct",
    "drop",
    "finish",
    "games_back",
    "playoffs",
    "runs",
    "runs_allowed",
    "attendance",
    "batter_age",
    "pitcher_age",
    "players_used",
    "pitchers_used",
    "top_player",
    "manager",
]

# Split, reuse playoffs column
history_df["playoff_record"] = (
    history_df["playoffs"].str.split("(", expand=True)[1].str.replace(")", "")
)
history_df["playoffs"] = (
    history_df["playoffs"].str.split("(", expand=True)[0].fillna("")
).str.strip()


# Results
history_df["games_back"] = history_df["games_back"].str.replace("--", "0").astype(float)
history_df["league_place"] = history_df["finish"].str.split(" of ", expand=True)[0]


# Just the columns we need
history_df = history_df.drop(
    [
        "team",
        "drop",
        "league",
        "pitchers_used",
        "players_used",
        "top_player",
        "manager",
        "playoff_record",
    ],
    axis=1,
)

logging.info("Dataframe prepared for export.")


""" 
EXPORT
"""

def save_dataframe(df, path_without_extension, formats):
    for file_format in formats:
        try:
            full_path = f"{path_without_extension}.{file_format}"
            if file_format == "csv":
                df.to_csv(full_path, index=False)
            elif file_format == "json":
                df.to_json(full_path, indent=4, orient="records", lines=False)
            elif file_format == "parquet":
                df.to_parquet(full_path, index=False)
            logging.info(f"Saved {file_format} format to {full_path}")
        except Exception as e:
            logging.error(f"Failed to save {file_format}: {e}")

def save_to_s3(df, base_path, s3_bucket, formats):
    for fmt in formats:
        try:
            buffer = BytesIO()
            if fmt == "csv":
                df.to_csv(buffer, index=False)
                content_type = "text/csv"
            elif fmt == "json":
                df.to_json(buffer, indent=4, orient="records", lines=False)
                content_type = "application/json"
            elif fmt == "parquet":
                df.to_parquet(buffer, index=False)
                content_type = "application/octet-stream"
            buffer.seek(0)
            s3_resource.Bucket(s3_bucket).put_object(Key=f"{base_path}.{fmt}", Body=buffer, ContentType=content_type)
            logging.info(f"Uploaded {fmt} to {s3_bucket}/{base_path}.{fmt}")
        except Exception as e:
            logging.error(f"Failed to upload {fmt} to S3: {e}")

# Saving files locally and to S3
file_path = os.path.join(data_dir, 'dodgers_season_outcomes')
formats = ["csv", "json", "parquet"]
save_dataframe(history_df, file_path, formats)
save_to_s3(history_df, "dodgers/data/standings/dodgers_season_outcomes", "stilesdata.com", formats)

file_path = os.path.join(data_dir, 'dodgers_season_outcomes')
formats = ["csv", "json", "parquet"]