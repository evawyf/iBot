from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import BarData
from datetime import datetime, timedelta
import pandas as pd
import pytz, threading, time
import sqlite3
import queue
import sys
from utils.contract import create_contract
from utils.barsize_valid_check import barsize_valid_check
from utils.sqlite_helper import SQLiteHelper


class IBHistoricalDataCollector(EWrapper, EClient):
    def __init__(self, port, client_id, symbol, contract_type, frequency, duration):
        EClient.__init__(self, self)
        self.port = port
        self.client_id = client_id
        # Contract details
        self.symbol = symbol
        self.contract_type = contract_type
        self.contract = create_contract(symbol, contract_type)
        # Init historical data info
        self.frequency = frequency
        self.duration = duration    

        self.data = []
        self.event = threading.Event()

        self.db_name = f"data/HistoricalData_{self.symbol}_{self.contract_type}_{self.frequency.replace(' ', '')}_{datetime.now().strftime('%Y%m%d')}.db"
        print(f"Using SQLite for historical data storage: {self.db_name}")

        self.sqlite_helper = SQLiteHelper(self.db_name)

    def historicalData(self, reqId, bar):
        self.data.append([bar.date, self.symbol, bar.open, bar.high, bar.low, bar.close, bar.volume])
        self.sqlite_helper.queue_insert((
            bar.date, self.symbol, bar.open, bar.high, bar.low, bar.close, bar.volume
        ))

    def historicalDataEnd(self, reqId, start, end):
        print(f"\nHistorical data retrieval completed. {start} - {end}")
        self.event.set()

    def error(self, reqId, errorCode, errorString):
        print(f"Error {errorCode}: {errorString}")

    def ib_connect(self):
        print("Attempting to connect to TWS...")
        if not hasattr(self, 'port') or not hasattr(self, 'client_id'):
            raise AttributeError("port and client_id must be set before calling ib_connect")
        self.connect("127.0.0.1", self.port, self.client_id)

        # Start the socket in a thread
        api_thread = threading.Thread(target=self.run, daemon=True)
        api_thread.start()

        # Wait for connection
        max_wait = 10
        while not self.isConnected() and max_wait > 0:
            time.sleep(1)
            max_wait -= 1

        if not self.isConnected():
            print("Failed to connect to TWS. Make sure it's running and allows API connections.")
            return False

        print("Connected to TWS.")
        return True

    def ib_disconnect(self):
        if self.isConnected():
            self.cancelHistoricalData(1)
            print("Disconnecting from TWS...")
            super().disconnect()
        
        # Signal SQLite thread to close
        self.sqlite_helper.close()

    def start(self):
        """
        symbol:str - The symbol of the contract to retrieve historical data for.
        contract_type:str - The type of contract to retrieve historical data for.
        frequency:str - The frequency of the bars to retrieve. 
            Set the query duration up to one week, using a time unit
            of seconds, days or weeks. Valid values include any integer followed by a space
            and then S (seconds), D (days) or W (week). If no unit is specified, seconds is used.
        duration:str - The duration of the historical data to retrieve.
        """ 

        self.data = []  # Clear previous data
        self.event.clear()  # Reset the event

        # Request historical data
        print(f"Requesting historical data for {self.symbol}...")

        # Calculate end time (current time) in US/Eastern timezone and format it correctly
        end_time = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y%m%d-%H:%M:%S")

        # Check if the frequency is valid
        bar_size = barsize_valid_check(self.frequency)
        self.reqHistoricalData(
            reqId=1,
            contract=self.contract,
            endDateTime=end_time,
            durationStr=self.duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )

        print(f"Fetching historical data for {self.symbol} with {self.frequency} bars.")

        # Wait for data to be collected
        self.event.wait(timeout=60)  # Wait up to 60 seconds for data

        if not self.data:
            print("No data received within the timeout period.")
            return None

        return pd.DataFrame(self.data, columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
    
    def write_historical_data_to_sqlite(self, df):
        """
        Queue the task of writing historical data to SQLite database.
        
        :param df: pandas.DataFrame, The historical data
        """
        
        # Add the task to the SQLite queue
        self.sqlite_helper.queue_insert(df)

if __name__ == "__main__":
    symbol = "MES"
    contract_type = "FUT"
    frequency = "1 min"
    duration = "1 M"    

    app = IBHistoricalDataCollector(port=7497, client_id=1, symbol=symbol, contract_type=contract_type, frequency=frequency, duration=duration)
    if app.ib_connect():
        try:
            df = app.start()
            if df is not None and not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                print(df)
                app.write_historical_data_to_sqlite(df.reset_index())
            else:
                print("Failed to retrieve historical data or data is empty.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            app.ib_disconnect()
    else:
        print("Failed to connect to TWS.")

# Example usage:
# historical_data = get_historical_data("MES", "FUT", "1 day", "1 M")
# print(historical_data)
