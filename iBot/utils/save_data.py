import pandas as pd
import datetime

def save_historical_data(df, contract):
        # Check if there's a 'date' or 'datetime' column
        date_column = next((col for col in df.columns if col.lower() in ['date', 'datetime']), None)
        
        if date_column:
            # Convert the column to datetime and format it as a string
            df['date'] = pd.to_datetime(df[date_column]).dt.strftime('%Y-%m-%d %H:%M:%S')
            # Remove the original date column if it's different from 'date'
            if date_column != 'date':
                df = df.drop(columns=[date_column])
            print(f"Created 'date' column from '{date_column}' column.")
        else:
            print("Warning: No date or datetime column found. Unable to create 'date' column.")
        
        # Display the first few rows to verify the date column
        print(df.head())
        
        # Save the historical data to a CSV file
        if df is not None and not df.empty:
            
            current_date = df['date'].iloc[0].strftime("%y%m%d") if 'date' in df.columns else datetime.datetime.now().strftime("%y%m%d")
            csv_filename = f"{contract.symbol}_{contract.secType}_historical_data_{current_date}.csv"
            df.to_csv(csv_filename, index=False)
            print(f"Historical data saved to {csv_filename}")
        else:
            print("No data to save.")
        
        return df