import pandas as pd
import numpy as np
import json
import os
import boto3 # Added for S3
from io import BytesIO # Added for S3
import logging # Added for logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the output directory and file name
output_dir = os.path.join("data", "standings")
output_file_name = "dodgers_wins_projection_timeseries.json"
local_output_file_path = os.path.join(output_dir, output_file_name)

# S3 Configuration
s3_bucket_name = "stilesdata.com"
s3_object_key = f"dodgers/data/standings/{output_file_name}"

# Ensure the output directory exists for local save
os.makedirs(output_dir, exist_ok=True)

# Initialize default output structure
output_data = {
    "games_played": 0,
    "current_wins": 0,
    "current_losses": 0,
    "timeseries": [],
    "message": "Data not yet processed."
}

def upload_json_to_s3(data_dict, bucket_name, object_key):
    """Uploads a python dictionary as a JSON object to S3."""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    session_params = {"region_name": "us-west-1"} # Default region

    if aws_access_key_id and aws_secret_access_key:
        session_params["aws_access_key_id"] = aws_access_key_id
        session_params["aws_secret_access_key"] = aws_secret_access_key
        logging.info("Using AWS credentials from environment variables for S3 upload.")
    else:
        profile_name = os.environ.get("AWS_PERSONAL_PROFILE", "haekeo")
        session_params["profile_name"] = profile_name
        logging.info(f"Using AWS profile '{profile_name}' for S3 upload.")
        
    try:
        session = boto3.Session(**session_params)
        s3_resource = session.resource("s3")
        
        json_buffer = BytesIO(json.dumps(data_dict, indent=4).encode('utf-8'))
        
        s3_resource.Bucket(bucket_name).put_object(
            Key=object_key, 
            Body=json_buffer, 
            ContentType="application/json"
        )
        logging.info(f"Successfully uploaded JSON to s3://{bucket_name}/{object_key}")
    except Exception as e:
        logging.error(f"Failed to upload JSON to S3 (s3://{bucket_name}/{object_key}): {e}")

logging.info(f"DEBUG: Initial output_data defined. Target local file: {local_output_file_path}, Target S3: s3://{s3_bucket_name}/{s3_object_key}")

try:
    # Load game-by-game results data
    local_source_data_path = os.path.join(output_dir, "dodgers_wins_losses_current.json")
    source_data_url = "https://stilesdata.com/dodgers/data/standings/dodgers_wins_losses_current.json"

    if not os.path.exists(local_source_data_path):
        logging.info(f"Local source file {local_source_data_path} not found. Attempting to fetch from URL: {source_data_url}")
        df = pd.read_json(source_data_url)
    else:
        logging.info(f"Loading data from local source file: {local_source_data_path}")
        df = pd.read_json(local_source_data_path)

    if df.empty:
        output_data["message"] = "Source data is empty. No projection possible."
        logging.warning(output_data["message"])
    else:
        if "gm" not in df.columns:
            raise ValueError("Column 'gm' (game number) not found in source data.")
        df = df.sort_values(by="gm").reset_index(drop=True)
        
        if 'win' not in df.columns:
            if 'result' not in df.columns:
                 raise ValueError("Column 'result' not found, cannot derive 'win'.")
            df["win"] = (df["result"] == "W").astype(int)

        if 'cumulative_wins' not in df.columns:
            df['cumulative_wins'] = df['win'].cumsum()
            
        games_played = len(df)
        current_wins = int(df["cumulative_wins"].iloc[-1]) if games_played > 0 else 0
        current_losses = games_played - current_wins

        output_data.update({
            "games_played": games_played,
            "current_wins": current_wins,
            "current_losses": current_losses,
            "timeseries": [] # Reset timeseries before populating
        })
        
        for index, row in df.iterrows():
            game_num = int(row["gm"])
            cum_wins = int(row["cumulative_wins"])
            output_data["timeseries"].append({
                "game_number": game_num,
                "mean_projected_wins": float(cum_wins),
                "lower_ci_wins": float(cum_wins),
                "upper_ci_wins": float(cum_wins)
            })

        remaining_games = 162 - games_played

        if games_played < 10:
            output_data["message"] = "Not enough games played for a meaningful projection (minimum 10 games required)."
            logging.info(output_data["message"])
        elif remaining_games <= 0:
            output_data["message"] = "Season complete. All 162 games have been played."
            logging.info(output_data["message"])
        else:
            past_outcomes = df["win"].values
            n_simulations = 10000
            boot_simulations_remaining = np.random.choice(past_outcomes, 
                                                          size=(n_simulations, remaining_games), 
                                                          replace=True)
            cumulative_boot_wins_for_remaining_part = np.cumsum(boot_simulations_remaining, axis=1)

            for i in range(remaining_games):
                game_num_overall = games_played + 1 + i
                projected_total_wins_at_game_sims = current_wins + cumulative_boot_wins_for_remaining_part[:, i]
                mean_wins = np.mean(projected_total_wins_at_game_sims)
                lower_ci = np.percentile(projected_total_wins_at_game_sims, 2.5)
                upper_ci = np.percentile(projected_total_wins_at_game_sims, 97.5)
                output_data["timeseries"].append({
                    "game_number": game_num_overall,
                    "mean_projected_wins": round(mean_wins, 1),
                    "lower_ci_wins": int(np.round(lower_ci)),
                    "upper_ci_wins": int(np.round(upper_ci))
                })
            
            output_data["message"] = f"Projection based on bootstrapping {games_played} past game outcomes for {remaining_games} remaining games."
            logging.info(f"Current record: {current_wins}-{current_losses} ({games_played} games)")
            final_mean = output_data['timeseries'][-1]['mean_projected_wins']
            final_lower = output_data['timeseries'][-1]['lower_ci_wins']
            final_upper = output_data['timeseries'][-1]['upper_ci_wins']
            logging.info(f"Projected final wins: {final_mean:.1f} (95% CI: {final_lower} - {final_upper})")

except FileNotFoundError:
    output_data["message"] = f"Error: Source data file not found. Checked local ({local_source_data_path}) and URL ({source_data_url})."
    logging.error(output_data["message"])
except pd.errors.EmptyDataError:
    output_data["message"] = "Error: Source data file is empty."
    logging.error(output_data["message"])
except ValueError as ve:
    output_data["message"] = f"ValueError during data processing: {ve}"
    logging.error(output_data["message"])
except Exception as e:
    output_data["message"] = f"An unexpected error occurred: {e}"
    logging.error(output_data["message"])
finally:
    try:
        with open(local_output_file_path, 'w') as f:
            json.dump(output_data, f, indent=4)
        logging.info(f"Local data saved to {local_output_file_path}")
    except Exception as e_local_save:
        logging.error(f"Failed to save data locally to {local_output_file_path}: {e_local_save}")

    # Attempt to upload to S3 regardless of previous outcomes (output_data will have relevant message)
    upload_json_to_s3(output_data, s3_bucket_name, s3_object_key)