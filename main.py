import logging
import requests
import csv
import time
import schedule
from process_data import process_frequency_data


# Define the API URL
url = (
    "https://data.elexon.co.uk/bmrs/api/v1/datasets/FREQ/stream?"
    "measurementDateTimeFrom=2024-01-01T00%3A00Z&"
    "measurementDateTimeTo=2024-01-01T01%3A00Z"
)

# Setup logging
logger = logging.getLogger("main")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")

# File handler
file_handler = logging.FileHandler("task_log.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Stream handler for console output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def save_to_csv(data, filename="average_power.csv"):
    """Saves the interval and average power data to a CSV file."""
    try:
        with open(filename, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Interval", "Average Power"])  # Write the header
            for interval, avg_power in data.items():
                writer.writerow([interval, avg_power])  # Write each row
        logger.info(f"Data successfully saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to save data to {filename}: {str(e)}")
        raise  # Ensure the exception is raised


def retry_fetch_data(url, retries=MAX_RETRIES):
    """Attempts to fetch data from the API with retries."""
    for attempt in range(retries):
        try:
            logger.info(f"Fetching data (Attempt {attempt + 1}/{retries})...")
            response = requests.get(url)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            data = response.json()
            if data:
                logger.info("Data fetched successfully.")
                return data
            else:
                raise ValueError("Empty response received from the API.")
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Error fetching data: {str(e)}")
            if attempt < retries - 1:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"Failed to fetch data after {retries} attempts.")
                raise  # Ensure the exception is raised


def job():
    """Job to fetch, process, and save data daily."""
    try:
        logger.info("Job has been triggered.")
        logger.info("Starting job...")
        data = retry_fetch_data(url)

        if not data:
            logger.error("No valid data fetched, job will be aborted.")
            return  # Abort the job if data is invalid

        average_power_per_half_hour = process_frequency_data(data)
        save_to_csv(average_power_per_half_hour)
        for interval, avg_power in average_power_per_half_hour.items():
            logger.info(f"Interval: {interval}, Average Power: {avg_power}")
    except Exception as e:
        logger.error(f"Error occurred during the job: {str(e)}")
        raise


# def run_scheduler_once():
#     """Schedule the job to run immediately for testing."""
#     job()  # Directly call the job for immediate testing
#     logger.info("Job has been triggered.")


def run_scheduler():
    """Schedule the job to run daily at 00:00."""
    schedule.every().day.at("00:00").do(job)
    logger.info("Job has been scheduled to run daily at 00:00.")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    # run_scheduler_once()
    run_scheduler()
