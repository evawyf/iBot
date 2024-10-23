import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt
from mplfinance.original_flavor import candlestick_ohlc
import matplotlib.dates as mdates

def clean_data(data):
    # Convert timestamp to datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')

    # Remove rows with invalid timestamp
    data = data.dropna(subset=['timestamp'])

    # Remove duplicate rows based on timestamp
    data = data.drop_duplicates(subset=['timestamp'])

    # Sort by timestamp
    data = data.sort_values('timestamp')

    # Set timestamp as index
    data.set_index('timestamp', inplace=True)

    # Print info about the cleaned dataset
    print(f"Dataset shape after cleaning: {data.shape}")
    print(f"Date range: from {data.index.min()} to {data.index.max()}")

    return data


def supertrend(data, period=10, multiplier=3):
    # Extract high, low, and close prices from the input data
    high = data['high']
    low = data['low']
    close = data['close']

    # Calculate True Range (TR)
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate Average True Range (ATR)
    atr = tr.ewm(com=period, min_periods=period).mean()

    # Calculate basic upper and lower bands
    hl2 = (high + low) / 2
    final_upperband = hl2 + (multiplier * atr)
    final_lowerband = hl2 - (multiplier * atr)

    # Initialize SuperTrend Series
    supertrend = pd.Series(index=data.index, dtype=float)
    direction = pd.Series(index=data.index, dtype=int)

    # Calculate SuperTrend
    for i in range(period, len(data)):
        if close.iloc[i] > final_upperband.iloc[i-1]:
            supertrend.iloc[i] = final_lowerband.iloc[i]
            direction.iloc[i] = 1
        elif close.iloc[i] < final_lowerband.iloc[i-1]:
            supertrend.iloc[i] = final_upperband.iloc[i]
            direction.iloc[i] = -1
        else:
            supertrend.iloc[i] = supertrend.iloc[i-1]
            direction.iloc[i] = direction.iloc[i-1]

            if (direction.iloc[i] == 1) and (final_lowerband.iloc[i] < supertrend.iloc[i]):
                supertrend.iloc[i] = final_lowerband.iloc[i]
            elif (direction.iloc[i] == -1) and (final_upperband.iloc[i] > supertrend.iloc[i]):
                supertrend.iloc[i] = final_upperband.iloc[i]

    # Create DataFrame with SuperTrend data
    st_data = pd.DataFrame(index=data.index)
    st_data['supertrend'] = supertrend
    st_data['direction'] = direction

    return st_data

if __name__ == "__main__":
    # Connect to the SQLite database
    conn = sqlite3.connect('data/HistoricalData_MES_FUT_1min_20241022.db')

    # Read data from the database
    query = "SELECT * FROM historical_data"
    data = pd.read_sql_query(query, conn)

    # Close the database connection
    conn.close()

    # Clean the data
    data = clean_data(data)

    # Calculate SuperTrend
    st_data = supertrend(data)

    # Merge SuperTrend data with original data
    result = pd.concat([data, st_data], axis=1)

    # Print the first and last few rows of the result
    print("First few rows of the result:")
    print(result.head())
    print("\nLast few rows of the result:")
    print(result.tail())

    # Optional: Save the result to a CSV file
    # result.to_csv('supertrend_result.csv')

    # Calculate basic statistics of the SuperTrend indicator
    print("\nBasic statistics of the SuperTrend indicator:")
    print(st_data.describe())

    # Count the number of trend changes
    trend_changes = (st_data['direction'] != st_data['direction'].shift(1)).sum()
    print(f"\nNumber of trend changes: {trend_changes}")

    # Calculate the average duration of a trend
    avg_trend_duration = len(st_data) / trend_changes
    print(f"Average trend duration: {avg_trend_duration:.2f} periods")

    # Create a plot
    fig, ax = plt.subplots(figsize=(20,10))

    # Prepare data for candlestick chart (last 10 bars)
    ohlc = data[['open', 'high', 'low', 'close']].tail(10).reset_index()
    ohlc['timestamp'] = mdates.date2num(ohlc['timestamp'])

    # Plot candlestick chart
    candlestick_ohlc(ax, ohlc.values, width=0.6, colorup='green', colordown='red', alpha=0.8)

    # Plot SuperTrend (last 10 bars)
    ax.plot(ohlc['timestamp'], st_data['supertrend'].tail(10), label='SuperTrend', color='blue', linewidth=2)

    # Customize the plot
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Price', fontsize=12)
    ax.set_title('SuperTrend Indicator with Price Action (Last 10 Bars)', fontsize=16)
    ax.legend(fontsize=10)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    # Rotate and align the tick labels so they look better
    plt.gcf().autofmt_xdate()

    # Adjust y-axis
    y_min = min(ohlc['low'].min(), st_data['supertrend'].tail(10).min())
    y_max = max(ohlc['high'].max(), st_data['supertrend'].tail(10).max())
    y_range = y_max - y_min
    ax.set_ylim(y_min - 0.05 * y_range, y_max + 0.05 * y_range)

    # Add grid
    ax.grid(True, linestyle='--', alpha=0.6)

    # Adjust layout and show the plot
    plt.tight_layout()
    plt.show()