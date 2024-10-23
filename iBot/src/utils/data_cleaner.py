import pandas as pd

def clean_data(data):

    original_shape = data.shape
    # Convert timestamp to datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')

    # Remove rows with invalid timestamp
    data = data.dropna(subset=['timestamp'])
    removed_invalid_timestamp = original_shape[0] - data.shape[0]

    # Remove duplicate rows based on timestamp
    data = data.drop_duplicates(subset=['timestamp'])
    removed_duplicates = removed_invalid_timestamp - (original_shape[0] - data.shape[0])

    # Sort by timestamp
    data = data.sort_values('timestamp')

    # Set timestamp as index
    data.set_index('timestamp', inplace=True)

    # Print info about the cleaned dataset
    print(f"Dataset shape after cleaning: from {original_shape} to {data.shape}. Removed {removed_invalid_timestamp} invalid timestamps and {removed_duplicates} duplicates.")
    print(f"Date range: from {data.index.min()} to {data.index.max()}")