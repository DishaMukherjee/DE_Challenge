import requests
import logging


def fetch_frequency_data(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch data. Status code: {response.status_code}")
            raise Exception(
                f"Bad response from API: {response.status_code}"
            )  # Add exception raising
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data: {str(e)}")
        raise
