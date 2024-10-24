import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from statsmodels.tsa.arima.model import ARIMA
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import os
import sqlite3

def supertrend_ai(data, atr_period=10, factor_range=(1, 5), factor_step=0.5, perf_alpha=10, **kwargs):
    high, low, close = data['high'], data['low'], data['close']
    
    # Calculate ATR
    tr = pd.concat([high - low, 
                    abs(high - close.shift(1)), 
                    abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(window=atr_period).mean()
    
    # Generate factors
    factors = np.arange(factor_range[0], factor_range[1] + factor_step, factor_step)
    
    # Calculate SuperTrend for each factor
    supertrends = []
    performances = []
    
    for factor in factors:
        upper = (high + low) / 2 + factor * atr
        lower = (high + low) / 2 - factor * atr
        
        supertrend = pd.Series(index=data.index, dtype=float)
        trend = pd.Series(index=data.index, dtype=int)
        
        for i in range(1, len(data.index)):
            if close[i] > upper[i-1]:
                supertrend[i] = lower[i]
                trend[i] = 1
            elif close[i] < lower[i-1]:
                supertrend[i] = upper[i]
                trend[i] = 0
            else:
                supertrend[i] = supertrend[i-1]
                trend[i] = trend[i-1]
                
                if (supertrend[i] < upper[i]) and (close[i] > supertrend[i-1]):
                    supertrend[i] = lower[i]
                    trend[i] = 1
                elif (supertrend[i] > lower[i]) and (close[i] < supertrend[i-1]):
                    supertrend[i] = upper[i]
                    trend[i] = 0
        
        # Calculate performance
        diff = np.sign(close.shift(1) - supertrend)
        perf = (close.diff() * diff).ewm(alpha=2/(perf_alpha+1), adjust=False).mean()
        
        supertrends.append(supertrend)
        performances.append(perf)
    
    # Prepare data for ML models
    X = np.array(performances).T
    
    # Handle NaN values
    X = np.nan_to_num(X, nan=np.nanmean(X))  # Replace NaN with mean of non-NaN values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # K-means clustering
    kmeans = KMeans(n_clusters=3, random_state=42)
    kmeans_clusters = kmeans.fit_predict(X_scaled)
    cluster_performances = [np.mean(X_scaled[kmeans_clusters == i]) for i in range(3)]
    kmeans_best_cluster = np.argmax(cluster_performances)
    kmeans_best_factors = factors[np.where(kmeans_clusters == kmeans_best_cluster)[0] % len(factors)]
    kmeans_best_factor = np.mean(kmeans_best_factors) if len(kmeans_best_factors) > 0 else np.mean(factors)
    
    # DBSCAN clustering
    dbscan = DBSCAN(eps=0.5, min_samples=3)
    dbscan_clusters = dbscan.fit_predict(X_scaled)
    dbscan_cluster_performances = [np.mean(X[dbscan_clusters == i]) for i in set(dbscan_clusters) if i != -1]
    if dbscan_cluster_performances:
        dbscan_best_cluster = list(set(dbscan_clusters))[np.argmax(dbscan_cluster_performances)]
        dbscan_best_factors = factors[dbscan_clusters == dbscan_best_cluster]
        dbscan_best_factor = np.mean(dbscan_best_factors) if len(dbscan_best_factors) > 0 else np.mean(factors)
    else:
        dbscan_best_factor = np.mean(factors)
    
    # Random Forest Regressor
    X_rf = pd.DataFrame({
        'open': data['open'],
        'high': data['high'],
        'low': data['low'],
        'close': data['close'],
        'volume': data['volume'],
        'atr': atr
    })
    y_rf = pd.Series(factors[np.argmax(performances, axis=0)]).reindex(X_rf.index)
    
    X_train, X_test, y_train, y_test = train_test_split(X_rf, y_rf, test_size=0.2, random_state=42)
    
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    
    rf_best_factor = rf_model.predict(X_rf)
    
    # ARIMA model
    best_performance_index = np.argmax(performances, axis=0)
    arima_model = ARIMA(best_performance_index, order=(1,1,1))
    arima_results = arima_model.fit()
    arima_best_factor = factors[int(arima_results.forecast(steps=1)[0])]
    
    # LSTM model
    X_lstm = np.array([data['open'], data['high'], data['low'], data['close'], data['volume'], atr]).T
    y_lstm = np.array(factors[np.argmax(performances, axis=0)])
    
    X_lstm = X_lstm.reshape((X_lstm.shape[0], 1, X_lstm.shape[1]))
    
    lstm_model = Sequential([
        LSTM(50, activation='relu', input_shape=(1, X_lstm.shape[2])),
        Dense(1)
    ])
    lstm_model.compile(optimizer='adam', loss='mse')
    lstm_model.fit(X_lstm, y_lstm, epochs=50, batch_size=32, verbose=0)
    
    lstm_best_factor = lstm_model.predict(X_lstm).flatten()
    
    # Combine all model factors
    all_factors = np.column_stack((
        np.full(len(data), kmeans_best_factor),
        np.full(len(data), dbscan_best_factor),
        rf_best_factor,
        np.full(len(data), arima_best_factor),
        lstm_best_factor
    ))
    
    # Use the median of all model factors as the final best factor
    best_factor = np.median(all_factors, axis=1)
    
    # Recalculate SuperTrend with best factor
    supertrend = pd.Series(index=data.index, dtype=float)
    trend = pd.Series(index=data.index, dtype=int)
    
    for i in range(1, len(data.index)):
        upper = (high[i] + low[i]) / 2 + best_factor[i] * atr[i]
        lower = (high[i] + low[i]) / 2 - best_factor[i] * atr[i]
        
        if close[i] > upper:
            supertrend[i] = lower
            trend[i] = 1
        elif close[i] < lower:
            supertrend[i] = upper
            trend[i] = 0
        else:
            supertrend[i] = supertrend[i-1]
            trend[i] = trend[i-1]
            
            if (supertrend[i] < upper) and (close[i] > supertrend[i-1]):
                supertrend[i] = lower
                trend[i] = 1
            elif (supertrend[i] > lower) and (close[i] < supertrend[i-1]):
                supertrend[i] = upper
                trend[i] = 0
    
    return pd.DataFrame({
        'SuperTrend': supertrend,
        'Trend': trend,
        'BestFactor': best_factor
    })

def backtest(data, st_data, contract_size=1):
    """
    Backtest the SuperTrend strategy
    
    :param data: DataFrame with OHLC data
    :param st_data: DataFrame with SuperTrend data
    :param contract_size: Number of contracts to trade (1 or 2)
    :return: DataFrame with backtest results
    """
    
    # Initialize variables
    position = 0
    entry_price = 0
    trades = []
    
    for i in range(1, len(data)):
        if st_data['Trend'][i] == 1 and st_data['Trend'][i-1] == 0:  # Buy signal
            if position <= 0:
                entry_price = data['close'][i]
                position = contract_size
                trades.append({
                    'entry_date': data.index[i],
                    'entry_price': entry_price,
                    'position': position
                })
        elif st_data['Trend'][i] == 0 and st_data['Trend'][i-1] == 1:  # Sell signal
            if position >= 0:
                exit_price = data['close'][i]
                if position > 0:
                    profit = (exit_price - entry_price) * position
                    trades[-1]['exit_date'] = data.index[i]
                    trades[-1]['exit_price'] = exit_price
                    trades[-1]['profit'] = profit
                position = -contract_size
                entry_price = exit_price
                trades.append({
                    'entry_date': data.index[i],
                    'entry_price': entry_price,
                    'position': position
                })
    
    # Close any open position at the end
    if position != 0:
        exit_price = data['close'][-1]
        profit = (exit_price - entry_price) * position
        trades[-1]['exit_date'] = data.index[-1]
        trades[-1]['exit_price'] = exit_price
        trades[-1]['profit'] = profit
    
    # Create a DataFrame from the trades list
    trades_df = pd.DataFrame(trades)
    
    # Calculate cumulative profit and other statistics
    trades_df['cumulative_profit'] = trades_df['profit'].cumsum()
    total_profit = trades_df['profit'].sum()
    win_rate = (trades_df['profit'] > 0).mean()
    
    print(f"Total Profit: ${total_profit:.2f}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Number of Trades: {len(trades_df)}")
    
    return trades_df

if __name__ == "__main__":
    # Example usage
    import sqlite3
    import pandas as pd

    # Connect to the SQLite database
    conn = sqlite3.connect('data/HistoricalData_MES_FUT_1min_20241022.db')

    # Read data from the database
    query = "SELECT * FROM historical_data"
    data = pd.read_sql_query(query, conn)

    # Close the database connection
    conn.close()

    # Print the column names to verify the structure
    print("Columns in the loaded data:", data.columns)

    # Ensure the column names match what's expected by supertrend_ai
    data = data.rename(columns={
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Open': 'open',
        'Volume': 'volume'
    })

    # Make sure 'date' is set as the index if it's not already
    if 'date' in data.columns:
        data.set_index('date', inplace=True)

    # Run SuperTrend AI with combined models
    st_data_combined = supertrend_ai(data)

    # Print results
    print("Combined SuperTrend AI Results:")
    print(st_data_combined.tail())

    # Run backtest
    print("\nBacktest Results (1 contract):")
    backtest_results_1 = backtest(data, st_data_combined, contract_size=1)
    
    print("\nBacktest Results (2 contracts):")
    backtest_results_2 = backtest(data, st_data_combined, contract_size=2)

    # You can further analyze the backtest results here
    # For example, plot the cumulative profit over time
    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 6))
    plt.plot(backtest_results_1['entry_date'], backtest_results_1['cumulative_profit'], label='1 Contract')
    plt.plot(backtest_results_2['entry_date'], backtest_results_2['cumulative_profit'], label='2 Contracts')
    plt.title('Cumulative Profit Over Time')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Profit ($)')
    plt.legend()
    plt.show()
