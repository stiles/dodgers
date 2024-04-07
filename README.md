# LA Dodgers standings tracker

This repository maintains an automated workflow to fetch, process, and store the LA Dodgers' current standings along with historical performance data dating back to 1958. The data is sourced from Baseball Reference and consolidated into a unified dataset for analysis and visualization purposes.

## How It Works

The repository includes a Python script that performs the following operations:

1. **Fetch Current Year Data**: Downloads the current season's game-by-game standings for the LA Dodgers from Baseball Reference.
2. **Process Data**: Cleans and formats the fetched data for consistency with the historical dataset.
3. **Concatenate with Historic Data**: Merges the current season's data with a pre-existing dataset containing records from 1958 to the present.
4. **Save and Export Data**: Outputs the combined dataset in CSV, JSON, and Parquet formats.
5. **Upload to AWS S3**: Optionally uploads the JSON file to an AWS S3 bucket for further use or archiving.

## GitHub Action Workflow

The repository utilizes GitHub Actions to automate the execution of the script on a daily basis, ensuring the dataset remains up-to-date throughout the baseball season. The workflow includes the following steps:

1. **Set up Python Environment**: Prepares the runtime environment with the necessary Python version and dependencies.
2. **Checkout Repository**: Clones the repository's content to the GitHub Actions runner.
3. **Configure AWS Credentials**: Securely configures AWS access credentials stored in GitHub Secrets, enabling the script to upload files to an S3 bucket.
4. **Execute Script**: Runs the Python script to fetch the latest standings, process the data, and perform the exports and uploads as configured.

## Configuration and Usage

To utilize this repository for your own tracking or analysis, follow these steps:

1. **Fork the Repository**: Create a copy of this repository under your own GitHub account.
2. **Configure Secrets**: Add the following secrets to your repository settings for secure AWS S3 uploads (optional):
    - `YOUR_AWS_KEY`: Your AWS Access Key ID.
    - `YOUR_AWS_SECRET`: Your AWS Secret Access Key.
3. **Adjust the Script (Optional)**: Modify the Python script as necessary to fit your specific data processing or analysis needs.
4. **Monitor Actions**: Check the "Actions" tab in your GitHub repository to see the workflow executions and ensure data is being updated as expected.

## Data Storage and Access

The processed dataset is available in the `data/processed` directory within this repository. If configured, the latest dataset is also uploaded to the specified AWS S3 bucket.

## Contributions

Contributions, suggestions, and enhancements are welcome! Please open an issue or submit a pull request if you have suggestions for improvement.

## License

This project is open-sourced under the MIT License. See the LICENSE file for more details.

