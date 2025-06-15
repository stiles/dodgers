import os
import sys
import requests
import pandas as pd
import logging
from bs4 import BeautifulSoup
import json
import boto3
import re
import unicodedata
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Output config
output_dir = "data/roster"
jekyll_data_dir = "_data/roster"
csv_file = f"{output_dir}/dodgers_roster_current.csv"
json_file = f"{output_dir}/dodgers_roster_current.json"
s3_bucket = "stilesdata.com"
s3_key_csv = "dodgers/data/roster/dodgers_roster_current.csv"
s3_key_json = "dodgers/data/roster/dodgers_roster_current.json"

# AWS session (same logic as your other scripts)
is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
aws_region = "us-west-1"
if is_github_actions:
    session = boto3.Session(
        aws_access_key_id=aws_key_id,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
else:
    session = boto3.Session(profile_name="haekeo", region_name=aws_region)
s3 = session.resource('s3')

def sluggify(name):
    # Remove accents, lowercase, replace spaces with hyphens, remove non-alphanum except hyphens
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name = name.lower().replace(' ', '-')
    name = re.sub(r'[^a-z0-9\-]', '', name)
    return name

def parse_player_row(row, position_group):
    tds = row.find_all('td')
    # Player thumb and image
    player_thumb_td = tds[0]
    img_tag = player_thumb_td.find('img')
    thumb_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else None
    # Remove 'w_180,' for larger image
    if thumb_url:
        thumb_url = thumb_url.replace('w_180,', '')
    # Extract player_id from the URL (between /people/ and /headshot/)
    player_id = None
    if thumb_url:
        m = re.search(r'/people/(\d+)/headshot', thumb_url)
        if m:
            player_id = m.group(1)
    info_td = tds[1]
    name_tag = info_td.find('a')
    name = name_tag.text.strip() if name_tag else None
    player_url = name_tag['href'] if name_tag else None
    jersey = info_td.find('span', class_='jersey')
    jersey_number = jersey.text.strip() if jersey else None

    # Status
    status_minor = info_td.find('span', class_='status-minor')
    status_il = info_td.find('span', class_='status-il')
    status = None
    if status_minor:
        status = status_minor.text.strip().upper()
    elif status_il:
        status = status_il.text.strip().upper()
    else:
        status = "ACTIVE"

    # Flags
    is_minors = status == "MINORS"
    is_il = status.startswith("IL-")
    is_active_roster = not (is_minors or is_il)
    is_40_man = True

    # Other fields
    b_t = tds[2].text.strip() if len(tds) > 2 else None
    height = tds[3].text.strip() if len(tds) > 3 else None
    weight = tds[4].text.strip() if len(tds) > 4 else None
    dob = tds[5].text.strip() if len(tds) > 5 else None

    return {
        "player_id": player_id,
        "thumb_url": thumb_url,
        "name": name,
        "player_url": player_url,
        "jersey": jersey_number,
        "position_group": position_group,
        "bat_throw": b_t,
        "height": height,
        "weight": weight,
        "dob": dob,
        "status": status,
        "is_minors": is_minors,
        "is_il": is_il,
        "is_active_roster": is_active_roster,
        "is_40_man": is_40_man
    }

def main():
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(jekyll_data_dir, exist_ok=True)
    photo_dir = os.path.join(output_dir, "photos")
    os.makedirs(photo_dir, exist_ok=True)
    url = "https://www.mlb.com/dodgers/roster/40-man"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table', class_='roster__table')

    all_players = []
    for table in tables:
        # Get position group from thead
        thead = table.find('thead')
        if not thead:
            continue
        header_td = thead.find('td')
        position_group = header_td.text.strip().capitalize().replace("Two-way players", "Unicorns") if header_td else "Unknown"
        # Parse all rows
        tbody = table.find('tbody')
        for row in tbody.find_all('tr'):
            player = parse_player_row(row, position_group)
            # Download player photo if not already present, using slugified name
            name = player.get('name')
            thumb_url = player.get('thumb_url')
            if name and thumb_url:
                slug = sluggify(name)
                player['slug'] = slug
                photo_path = os.path.join(photo_dir, f"{slug}.jpg")
                if not os.path.exists(photo_path):
                    try:
                        resp = requests.get(thumb_url)
                        if resp.status_code == 200:
                            with open(photo_path, "wb") as f:
                                f.write(resp.content)
                            logging.info(f"Downloaded photo for {slug}")
                        else:
                            logging.warning(f"Failed to download photo for {slug} from {thumb_url}")
                    except Exception as e:
                        logging.warning(f"Error downloading photo for {slug}: {e}")
            all_players.append(player)

    df = pd.DataFrame(all_players)
    df.to_csv(csv_file, index=False)
    df.to_json(json_file, indent=2, orient="records")

    # Copy to Jekyll data dir
    shutil.copy(json_file, jekyll_data_dir)
    logging.info(f"Roster data copied to {jekyll_data_dir}")

    # Upload to S3
    s3.Bucket(s3_bucket).upload_file(csv_file, s3_key_csv)
    s3.Bucket(s3_bucket).upload_file(json_file, s3_key_json)
    logging.info("Roster data written and uploaded to S3.")

if __name__ == "__main__":
    main()