# process_data.py
from utils import calculate_response_power, get_half_hour_interval


def process_frequency_data(data):
    """Process the raw frequency data to calculate per half-hour average power."""

    # Assuming `data` is a list of frequency entries with 'measurementTime' and 'frequency'
    power_responses = [
        (entry["measurementTime"], calculate_response_power(entry["frequency"]))
        for entry in data  # Iterate directly over the list
    ]

    # Group by half-hour intervals
    half_hour_aggregates = {}
    for measurement_time, power in power_responses:
        half_hour_interval = get_half_hour_interval(measurement_time)
        if half_hour_interval not in half_hour_aggregates:
            half_hour_aggregates[half_hour_interval] = []
        half_hour_aggregates[half_hour_interval].append(power)

    # Calculate average power for each half-hour interval
    average_power_per_half_hour = {
        interval: sum(powers) / len(powers)
        for interval, powers in half_hour_aggregates.items()
    }

    return average_power_per_half_hour
