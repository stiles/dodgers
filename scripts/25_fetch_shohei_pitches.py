import re
import json
import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
import boto3

# --- File Paths ---
output_dir = "notebooks/data/pitching"
os.makedirs(output_dir, exist_ok=True)

pitches_csv_path = os.path.join(output_dir, "shohei_ohtani_pitches.csv")
pitches_json_path = os.path.join(output_dir, "shohei_ohtani_pitches.json")
pitch_mix_csv_path = os.path.join(output_dir, "shohei_ohtani_pitch_mix.csv")
pitch_mix_json_path = os.path.join(output_dir, "shohei_ohtani_pitch_mix.json")

# --- S3 Configuration ---
s3_bucket = "stilesdata.com"
s3_prefix = "dodgers/data/pitching"
s3_key_pitches_csv = f"{s3_prefix}/shohei_ohtani_pitches.csv"
s3_key_pitches_json = f"{s3_prefix}/shohei_ohtani_pitches.json"
s3_key_pitch_mix_csv = f"{s3_prefix}/shohei_ohtani_pitch_mix.csv"
s3_key_pitch_mix_json = f"{s3_prefix}/shohei_ohtani_pitch_mix.json"

# --- AWS Session ---
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

# Fetch page content
url = "https://baseballsavant.mlb.com/savant-player/shohei-ohtani-660271?stats=statcast-r-pitching-mlb&playerType=pitcher"
html = requests.get(url).text
soup = BeautifulSoup(html, "html.parser")

# Locate the JS script with the data
script = next(tag for tag in soup.find_all("script") if "statcastPitches" in tag.text)
script_text = script.text

# --- Extract statcastPitches block ---
pitches_match = re.search(r"statcastPitches\s*:\s*(\{.*?\})\s*,\s*pitchBreakdown", script_text, re.DOTALL)
if not pitches_match:
    print("Could not find statcastPitches data.")
    exit()

pitches_raw = pitches_match.group(1).replace("'", '"').replace("undefined", "null")
statcast_pitches = json.loads(pitches_raw)

# Flatten and convert to DataFrame
all_pitches = []
for pitch_type, pitches in statcast_pitches.items():
    for pitch in pitches:
        pitch["pitch_type_abbr"] = pitch_type
        all_pitches.append(pitch)

pitches_df = pd.DataFrame(all_pitches)
print(f"Columns in fetched data: {pitches_df.columns.tolist()}")

# --- Extract pitchBreakdown block ---
breakdown_match = re.search(r"pitchBreakdown\s*:\s*(\[[^\]]+\])", script_text)
if breakdown_match:
    breakdown_raw = breakdown_match.group(1).replace("'", '"')
    pitch_distribution = json.loads(breakdown_raw)
    distribution_df = pd.DataFrame(pitch_distribution)

    # Save pitch mix data (overwrite)
    distribution_df.to_csv(pitch_mix_csv_path, index=False)
    distribution_df.to_json(pitch_mix_json_path, orient="records", indent=4)
    print("\nPitch Mix DataFrame:")
    print(distribution_df[["pitchType", "name", "percent", "count"]])
    # Upload to S3
    s3.Bucket(s3_bucket).upload_file(pitch_mix_csv_path, s3_key_pitch_mix_csv)
    s3.Bucket(s3_bucket).upload_file(pitch_mix_json_path, s3_key_pitch_mix_json)
    print("Pitch mix data uploaded to S3.")


# --- Process and save historical pitches ---
if not pitches_df.empty:
    if os.path.exists(pitches_csv_path):
        existing_pitches_df = pd.read_csv(pitches_csv_path)
        combined_df = pd.concat([existing_pitches_df, pitches_df])
    else:
        combined_df = pitches_df

    # Deduplicate based on a unique pitch ID
    if 'pid' in combined_df.columns:
        combined_df.drop_duplicates(subset=['pid'], keep='last', inplace=True)
        print(f"\nDe-duplicated and saving {len(combined_df)} total pitches ...")
    else:
        print("\nWarning: Could not find 'pid' for de-duplication. Saving all fetched pitches.")

    # Save combined data
    combined_df.to_csv(pitches_csv_path, index=False)
    combined_df.to_json(pitches_json_path, orient="records", indent=4)

    print("\nSample of latest pitches:")
    print(pitches_df[["gd", "pitch_type_abbr", "vel", "x", "z"]].head())

    # Upload to S3
    s3.Bucket(s3_bucket).upload_file(pitches_csv_path, s3_key_pitches_csv)
    s3.Bucket(s3_bucket).upload_file(pitches_json_path, s3_key_pitches_json)
    print("Historical pitch data uploaded to S3.")
else:
    print("\nNo new pitches found to process.")