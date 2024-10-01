import unittest
from unittest.mock import patch, MagicMock
from fetch_data import fetch_frequency_data
import requests
from main import job, run_scheduler
from utils import calculate_response_power, get_half_hour_interval
from process_data import process_frequency_data
from datetime import datetime


class TestFetchDataFunctions(unittest.TestCase):
    @patch("fetch_data.requests.get")
    def test_fetch_frequency_data_success(self, mock_get):
        """Test successful data fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test_data"}
        mock_get.return_value = mock_response

        url = "http://example.com/api"
        result = fetch_frequency_data(url)
        self.assertEqual(result, {"data": "test_data"})

    @patch("fetch_data.requests.get")
    def test_fetch_frequency_data_failure_status(self, mock_get):
        """Test data fetch with non-200 status code."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        url = "http://example.com/api"
        with self.assertRaises(Exception) as context:
            fetch_frequency_data(url)
        self.assertIn("Bad response from API: 404", str(context.exception))

    @patch("fetch_data.requests.get")
    def test_fetch_frequency_data_exception(self, mock_get):
        """Test data fetch when a RequestException occurs."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        url = "http://example.com/api"
        with self.assertRaises(requests.exceptions.RequestException):
            fetch_frequency_data(url)


class TestMainFunctions(unittest.TestCase):
    @patch("main.csv.writer")
    @patch("main.open")
    def test_save_to_csv_success(self, mock_open, mock_csv_writer):
        """Test saving data to CSV successfully."""
        from main import save_to_csv

        data = {datetime(2023, 10, 2, 12, 0): 0.4}
        save_to_csv(data)
        mock_open.assert_called_once_with("average_power.csv", mode="w", newline="")
        mock_csv_writer.assert_called()

    @patch("main.logger")
    @patch("main.open", side_effect=Exception("File error"))
    def test_save_to_csv_failure(self, mock_open, mock_logger):
        """Test exception handling when saving to CSV fails."""
        from main import save_to_csv

        data = {datetime(2023, 10, 2, 12, 0): 0.4}
        with self.assertRaises(Exception) as context:
            save_to_csv(data)
        self.assertIn("File error", str(context.exception))
        mock_logger.error.assert_called_with(
            "Failed to save data to average_power.csv: File error"
        )

    @patch("main.requests.get")
    def test_retry_fetch_data_success(self, mock_get):
        """Test retry_fetch_data succeeds on first attempt."""
        from main import retry_fetch_data

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test_data"}
        mock_get.return_value = mock_response

        url = "http://example.com/api"
        result = retry_fetch_data(url)
        self.assertEqual(result, {"data": "test_data"})
        self.assertEqual(mock_get.call_count, 1)

    @patch("main.requests.get")
    def test_retry_fetch_data_retry(self, mock_get):
        """Test retry_fetch_data retries after failure."""
        from main import retry_fetch_data, RETRY_DELAY

        mock_get.side_effect = [
            requests.exceptions.RequestException("Error"),
            MagicMock(status_code=200, json=lambda: {"data": "test_data"}),
        ]

        url = "http://example.com/api"
        with patch("main.time.sleep") as mock_sleep:
            result = retry_fetch_data(url)
            self.assertEqual(result, {"data": "test_data"})
            self.assertEqual(mock_get.call_count, 2)
            mock_sleep.assert_called_once_with(RETRY_DELAY)

    @patch("main.retry_fetch_data", return_value=None)
    @patch("main.logger")
    def test_job_no_data(self, mock_logger, mock_retry_fetch):
        """Test job when no data is fetched."""
        from main import job

        job()
        mock_logger.error.assert_called_with(
            "No valid data fetched, job will be aborted."
        )


class TestMain(unittest.TestCase):
    @patch("main.time.sleep", side_effect=KeyboardInterrupt)
    @patch("main.schedule.run_pending")
    @patch("main.schedule.every")
    def test_scheduling(self, mock_every, mock_run_pending, mock_sleep):
        """Test if the job is scheduled correctly."""
        print("Running the scheduling test...")
        try:
            run_scheduler()
        except KeyboardInterrupt:
            pass
        print("Verifying the scheduling setup...")
        mock_every.assert_called_once()
        mock_every.return_value.day.at.assert_called_once_with("00:00")
        mock_every.return_value.day.at.return_value.do.assert_called_once_with(job)
        mock_run_pending.assert_called()


class TestUtils(unittest.TestCase):
    def test_calculate_response_power_within_range(self):
        """Test calculate_response_power with frequencies within 0.5 Hz of 50 Hz."""
        self.assertEqual(calculate_response_power(50.0), 0.0)
        self.assertAlmostEqual(calculate_response_power(49.8), 0.4, places=6)
        self.assertAlmostEqual(calculate_response_power(50.2), 0.4, places=6)

    def test_calculate_response_power_outside_range(self):
        """Test calculate_response_power with frequencies outside 0.5 Hz of 50 Hz."""
        self.assertEqual(calculate_response_power(49.4), 1.0)
        self.assertEqual(calculate_response_power(50.6), 1.0)

    def test_get_half_hour_interval(self):
        """Test get_half_hour_interval function."""
        timestamp = "2023-10-02T12:15:00Z"
        expected_interval = datetime(2023, 10, 2, 12, 0, 0)
        self.assertEqual(get_half_hour_interval(timestamp), expected_interval)

        timestamp = "2023-10-02T12:45:00Z"
        expected_interval = datetime(2023, 10, 2, 12, 30, 0)
        self.assertEqual(get_half_hour_interval(timestamp), expected_interval)

        timestamp = "2023-10-02T12:30:00Z"
        expected_interval = datetime(2023, 10, 2, 12, 30, 0)
        self.assertEqual(get_half_hour_interval(timestamp), expected_interval)

    def test_get_half_hour_interval_invalid_format(self):
        """Test get_half_hour_interval with invalid timestamp format."""
        timestamp = "2023-10-02 12:30:00"
        with self.assertRaises(ValueError):
            get_half_hour_interval(timestamp)


class TestProcessDataFunctions(unittest.TestCase):
    def test_process_frequency_data(self):
        """Test processing frequency data."""
        data = [
            {"measurementTime": "2023-10-02T12:15:00Z", "frequency": 49.8},
            {"measurementTime": "2023-10-02T12:45:00Z", "frequency": 50.2},
            {"measurementTime": "2023-10-02T13:05:00Z", "frequency": 50.1},
        ]
        expected_result = {
            datetime(2023, 10, 2, 12, 0): 0.4,
            datetime(2023, 10, 2, 12, 30): 0.4,
            datetime(2023, 10, 2, 13, 0): 0.2,
        }
        result = process_frequency_data(data)
        # Compare keys first
        self.assertEqual(set(result.keys()), set(expected_result.keys()))
        # Now compare values using assertAlmostEqual
        for key in result:
            self.assertAlmostEqual(result[key], expected_result[key], places=6)


if __name__ == "__main__":
    unittest.main()
