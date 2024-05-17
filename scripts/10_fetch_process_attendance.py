#!/usr/bin/env python
# coding: utf-8

# # MLB attendance figures by location
# > This notebook visusalizes team home stadium attendance statistics using data from [Baseball Reference](https://www.baseball-reference.com/leagues/AL/2024-misc.shtml) and [Esri](https://hub.arcgis.com/datasets/f60004d3037e42ad93cb03b9590cafec_0/about).

# ---

#!/usr/bin/env python
# coding: utf-8

import os
import boto3
import logging
import datetime
import pandas as pd
import geopandas as gpd
from io import BytesIO

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
base_dir = os.getcwd()
data_dir = os.path.join(base_dir, 'data', 'standings')
os.makedirs(data_dir, exist_ok=True)

profile_name = os.environ.get("AWS_PERSONAL_PROFILE")
today = datetime.date.today()
year = today.year

"""
FETCH: MLB ATTENDANCE
"""

src_dfs = []

leagues = ['AL', 'NL']
for league in leagues:
    url = f'https://www.baseball-reference.com/leagues/{league}/2024-misc.shtml'
    src = (pd.read_html(url)[0])[['Tm', 'Attendance', 'Attend/G']].assign(league=league)
    src_dfs.append(src)

df = pd.concat(src_dfs).rename(columns={'Tm':'team', 'Attendance':'attendance', 'Attend/G':'attend_game'}).sort_values('attend_game', ascending=False).reset_index(drop=True)

"""
GEOGRAPHY: MLB STADIUMS
"""

gdf = gpd.read_file('https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Major_League_Baseball_Stadiums/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson')
gdf.columns = gdf.columns.str.lower()

gdf.loc[gdf["team"] == "Cleveland Indians", "team"] = 'Cleveland Guardians'
gdf.loc[gdf["league"] == "National", "league"] = 'NL'
gdf.loc[gdf["league"] == "American", "league"] = 'AL'
gdf.loc[gdf["team"] == "Houston Astros", "league"] = 'AL'
gdf.loc[gdf["team"] == "Oakland Athletics", "name"] = 'Oakland Coliseum'
gdf.loc[gdf["team"] == "Baltimore Orioles", "name"] = 'Camden Yards'


"""
MERGE GEO/VALUES
"""
merged = pd.merge(df, gdf.drop(columns=['geometry']), on=['team', 'league'])


# Function to save DataFrame to S3 as JSON
def save_to_s3(df, s3_path, s3_bucket):
    try:
        buffer = BytesIO()
        df.to_json(buffer, orient="records", lines=False)
        buffer.seek(0)
        s3_resource.Bucket(s3_bucket).put_object(Key=s3_path, Body=buffer, ContentType="application/json")
        logging.info(f"Uploaded JSON to {s3_bucket}/{s3_path}")
    except Exception as e:
        logging.error(f"Failed to upload JSON to S3: {e}")

# Saving DataFrame to S3
s3_path = "dodgers/data/standings/mlb_team_attendance.json"
save_to_s3(merged, s3_path, "stilesdata.com")
