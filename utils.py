# utils.py
from datetime import datetime


def calculate_response_power(frequency):
    """Calculate the battery response power based on frequency."""
    return abs(frequency - 50) / 0.5 if abs(frequency - 50) < 0.5 else 1


def get_half_hour_interval(timestamp):
    """Get half-hour period for a given timestamp."""
    dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")  # Adjust format if needed
    return dt.replace(minute=0 if dt.minute < 30 else 30, second=0, microsecond=0)
