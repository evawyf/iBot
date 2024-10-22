import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from statsmodels.tsa.arima.model import ARIMA
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

def supertrend_ai(data, atr_period=10, factor_range=(1, 5), factor_step=0.5, perf_alpha=10, model='kmeans', **kwargs):
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
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    if model == 'kmeans':
        # K-means clustering
        kmeans = KMeans(n_clusters=3, random_state=42)
        clusters = kmeans.fit_predict(X_scaled)
        best_cluster = np.argmax([np.mean(perf) for perf in performances])
        best_factors = factors[clusters == best_cluster]
        best_factor = np.mean(best_factors)
        
    elif model == 'dbscan':
        # DBSCAN clustering
        dbscan = DBSCAN(eps=0.5, min_samples=3)
        clusters = dbscan.fit_predict(X_scaled)
        cluster_performances = [np.mean(X[clusters == i]) for i in set(clusters) if i != -1]
        best_cluster = list(set(clusters))[np.argmax(cluster_performances)]
        best_factors = factors[clusters == best_cluster]
        best_factor = np.mean(best_factors)
        
    elif model == 'randomforest':
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
        
        best_factor = rf_model.predict(X_rf)
        
    elif model == 'arima':
        # ARIMA model
        best_performance_index = np.argmax(performances, axis=0)
        arima_model = ARIMA(best_performance_index, order=(1,1,1))
        arima_results = arima_model.fit()
        best_factor = factors[arima_results.forecast(steps=1)[0]]
        
    elif model == 'lstm':
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
        
        best_factor = lstm_model.predict(X_lstm)
        
    else:
        raise ValueError("Invalid model specified. Choose from 'kmeans', 'dbscan', 'randomforest', 'arima', or 'lstm'.")
    
    # Recalculate SuperTrend with best factor(s)
    supertrend = pd.Series(index=data.index, dtype=float)
    trend = pd.Series(index=data.index, dtype=int)
    
    for i in range(1, len(data.index)):
        factor = best_factor[i] if isinstance(best_factor, np.ndarray) else best_factor
        upper = (high[i] + low[i]) / 2 + factor * atr[i]
        lower = (high[i] + low[i]) / 2 - factor * atr[i]
        
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
        'BestFactor': best_factor if isinstance(best_factor, np.ndarray) else pd.Series(best_factor, index=data.index)
    })

# Usage examples:
# st_data_kmeans = supertrend_ai(data, model='kmeans')
# st_data_dbscan = supertrend_ai(data, model='dbscan')
# st_data_rf = supertrend_ai(data, model='randomforest')
# st_data_arima = supertrend_ai(data, model='arima')
# st_data_lstm = supertrend_ai(data, model='lstm')