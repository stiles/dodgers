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
from datetime import datetime
from dateutil.relativedelta import relativedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Output config
output_dir = "data/roster"
jekyll_data_dir = "_data/roster"
csv_file = f"{output_dir}/dodgers_roster_current.csv"
json_file = f"{output_dir}/dodgers_roster_current.json"
transactions_csv_file = f"{output_dir}/dodgers_transactions_current.csv"
transactions_json_file = f"{output_dir}/dodgers_transactions_current.json"
transactions_archive_json_file = f"{output_dir}/dodgers_transactions_archive.json"
s3_bucket = "stilesdata.com"
s3_key_csv = "dodgers/data/roster/dodgers_roster_current.csv"
s3_key_json = "dodgers/data/roster/dodgers_roster_current.json"
s3_key_transactions_csv = "dodgers/data/roster/dodgers_transactions_current.csv"
s3_key_transactions_json = "dodgers/data/roster/dodgers_transactions_current.json"
s3_key_transactions_archive_json = "dodgers/data/roster/dodgers_transactions_archive.json"

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

def find_players_in_transaction(transaction, player_names):
    found_players = []
    for player in player_names:
        if re.search(r'\b' + re.escape(player) + r'\b', transaction):
            found_players.append(player)
    return found_players if found_players else None

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

def fetch_transactions():
    """
    Fetches team transactions for the current and previous 3 months,
    merges them with a historical archive, and saves the full archive
    as well as a separate file with the 100 most recent transactions.
    """
    logging.info("Fetching and archiving transactions...")

    # Determine the URLs to fetch (current month and previous 3)
    today = datetime.now()
    urls_to_fetch = []
    for i in range(4):
        target_date = today - relativedelta(months=i)
        year = target_date.year
        month = target_date.strftime('%m')
        urls_to_fetch.append(f'https://www.mlb.com/dodgers/roster/transactions/{year}/{month}')

    # Fetch new data
    new_transactions_list = []
    for url in urls_to_fetch:
        try:
            df_list = pd.read_html(url)
            if df_list:
                new_transactions_list.append(df_list[0])
                logging.info(f"Successfully fetched {url}")
        except Exception as e:
            logging.warning(f"Could not fetch or parse {url}. It might be a month with no transactions. Error: {e}")
            continue

    if not new_transactions_list:
        logging.info("No new transactions found in the last 4 months. Exiting transaction fetch.")
        return

    # Combine all newly fetched dataframes
    new_df = pd.concat(new_transactions_list, ignore_index=True)
    new_df.columns = new_df.columns.str.lower()
    new_df.dropna(subset=['date', 'transaction'], inplace=True)

    # Process new data
    new_df['transaction'] = new_df['transaction'].str.replace('Los Angeles Dodgers', 'Dodgers', regex=False)
    new_df['date'] = pd.to_datetime(new_df['date'], format='%m/%d/%y')

    positions = ["RHP", "LHP", "P", "C", "1B", "2B", "3B", "SS", "INF", "OF", "LF", "CF", "RF", "DH"]
    position_regex = r'(?:' + '|'.join(positions) + r')\s'
    name_regex = r"([A-Z][a-zA-Zà-úÀ-Ú\.\-']+(?:\s[A-Z][a-zA-Zà-úÀ-Ú\.\-']+)+)"
    full_regex = position_regex + name_regex

    def extract_names(transaction_text):
        names = re.findall(full_regex, transaction_text)
        return [name.strip().rstrip('.') for name in names] if names else None

    new_df['players'] = new_df['transaction'].apply(extract_names)

    # Load archive
    archive_df = pd.DataFrame()
    if os.path.exists(transactions_archive_json_file):
        archive_df = pd.read_json(transactions_archive_json_file)
        if not archive_df.empty:
            archive_df['date'] = pd.to_datetime(archive_df['date'])

    # Combine, de-duplicate, and sort
    combined_df = pd.concat([archive_df, new_df], ignore_index=True)
    combined_df.drop_duplicates(subset=['date', 'transaction'], keep='last', inplace=True)
    combined_df.sort_values(by='date', ascending=False, inplace=True)
    combined_df['date'] = combined_df['date'].dt.strftime('%Y-%m-%d')

    # Save full archive
    with open(transactions_archive_json_file, 'w', encoding='utf-8') as f:
        combined_df.to_json(f, indent=2, orient="records", force_ascii=False)
    logging.info(f"Full transaction archive saved to {transactions_archive_json_file}")
    s3.Bucket(s3_bucket).upload_file(transactions_archive_json_file, s3_key_transactions_archive_json)

    # Save current view (top 100)
    current_df = combined_df.head(100)
    current_df.to_csv(transactions_csv_file, index=False)
    with open(transactions_json_file, 'w', encoding='utf-8') as f:
        current_df.to_json(f, indent=2, orient="records", force_ascii=False)

    shutil.copy(transactions_json_file, jekyll_data_dir)
    logging.info(f"Top 100 transactions copied to {jekyll_data_dir}")

    s3.Bucket(s3_bucket).upload_file(transactions_csv_file, s3_key_transactions_csv)
    s3.Bucket(s3_bucket).upload_file(transactions_json_file, s3_key_transactions_json)
    logging.info("Current transactions data written and uploaded to S3.")

def main():
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(jekyll_data_dir, exist_ok=True)
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
            name = player.get('name')
            if name:
                player['slug'] = sluggify(name)
            all_players.append(player)

    df = pd.DataFrame(all_players)
    df.to_csv(csv_file, index=False)
    with open(json_file, 'w', encoding='utf-8') as f:
        df.to_json(f, indent=2, orient="records", force_ascii=False)

    # Copy to Jekyll data dir
    shutil.copy(json_file, jekyll_data_dir)
    logging.info(f"Roster data copied to {jekyll_data_dir}")

    # Upload to S3
    s3.Bucket(s3_bucket).upload_file(csv_file, s3_key_csv)
    s3.Bucket(s3_bucket).upload_file(json_file, s3_key_json)
    logging.info("Roster data written and uploaded to S3.")

    fetch_transactions()

if __name__ == "__main__":
    main()