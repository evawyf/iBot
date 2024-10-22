from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import BarData
from datetime import datetime, timedelta
import pandas as pd
import pytz, threading, time
import sqlite3
import queue
from utils.contract import create_contract
from utils.barsize_valid_check import barsize_valid_check


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

        self.sqlite_queue = queue.Queue()
        # Start SQLite worker thread
        self.sqlite_thread = threading.Thread(target=self.sqlite_worker, daemon=True)
        self.sqlite_thread.start()

    def historicalData(self, reqId, bar):
        self.data.append([bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume])

    def historicalDataEnd(self, reqId, start, end):
        print(f"Historical data retrieval completed. {start} - {end}")
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
        self.sqlite_queue.put(("CLOSE", None))
        self.sqlite_thread.join()  # Wait for SQLite thread to finish

    def get_historical_data(self):
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
        print(f"Requesting historical data for {self.symbol}...")  # Fixed: Use self.symbol instead of symbol

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

        print(f"Fetching historical data for {self.symbol} with {self.frequency} bars.")  # Fixed: Use self.symbol and self.frequency

        # Wait for data to be collected
        self.event.wait(timeout=60)  # Wait up to 60 seconds for data

        if not self.data:
            print("No data received within the timeout period.")
            return None

        return pd.DataFrame(self.data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    
    def sqlite_worker(self):
        """
        Worker function for handling SQLite operations in a separate thread.
        """
        with sqlite3.connect(self.db_name) as sqlite_db:
            self.create_sqlite_table(sqlite_db)
            
            while True:
                try:
                    operation, args = self.sqlite_queue.get()
                    if operation == "INSERT":
                        self.insert_data_to_sqlite(sqlite_db, args)
                    elif operation == "CLOSE":
                        break
                except Exception as e:
                    print(f"SQLite error: {e}")
                finally:
                    self.sqlite_queue.task_done()
    
    def create_sqlite_table(self, db):
        """
        Create the SQLite table for storing historical data if it doesn't exist.
        """
        cursor = db.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_data (
            date TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER
        )
        ''')
        db.commit()
    
    def insert_data_to_sqlite(self, db, args):
        """
        Insert historical data into the SQLite database.
        """
        db_name, df = args
        df.to_sql('historical_data', db, if_exists='replace', index=False)
        db.commit()
    
    def write_historical_data_to_sqlite(self, df):
        """
        Queue the task of writing historical data to SQLite database.
        
        :param df: pandas.DataFrame, The historical data
        """
        
        # Add the task to the SQLite queue
        self.sqlite_queue.put(("INSERT", (self.db_name, df)))
        
        print(f"Historical data for {self.symbol} {self.contract_type} with {self.frequency} frequency has been queued for writing to {self.db_name}")

if __name__ == "__main__":
    symbol = "MES"
    contract_type = "FUT"
    frequency = "1 min"
    duration = "1 M"    

    app = IBHistoricalDataCollector(port=7497, client_id=0, symbol=symbol, contract_type=contract_type, frequency=frequency, duration=duration)
    if app.ib_connect():
        try:
            df = app.get_historical_data()
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
