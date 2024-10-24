from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from datetime import datetime, timedelta
import pandas as pd
import pytz
import threading
import time
from utils.ib_contract import create_contract
from utils.barsize_valid_check import barsize_valid_check
from utils.sqlite_helper import SQLiteHelper
from utils.data_cleaner import clean_data

class IBHistoricalDataCollector(EWrapper, EClient):
    def __init__(self, port, client_id, symbol, contract_type, frequency, duration):
        EClient.__init__(self, self)
        self.port = port
        self.client_id = client_id
        self.symbol = symbol
        self.contract = create_contract(symbol, contract_type)
        self.frequency = frequency
        self.duration = duration    
        self.data = []
        self.event = threading.Event()
        self.db_name = f"data/HistoricalData_{symbol}_{contract_type}_{frequency.replace(' ', '')}_{duration.replace(' ', '')}_{datetime.now().strftime('%Y%m%d')}.db"
        self.sqlite_helper = SQLiteHelper(self.db_name)

    def historicalData(self, reqId, bar):
        self.data.append([bar.date, self.symbol, bar.open, bar.high, bar.low, bar.close, bar.volume])
        self.sqlite_helper.queue_insert((bar.date, self.symbol, bar.open, bar.high, bar.low, bar.close, bar.volume))

    def historicalDataEnd(self, reqId, start, end):
        print(f"\nHistorical data retrieval completed. {start} - {end}")
        self.event.set()

    def error(self, reqId, errorCode, errorString):
        print(f"Error {errorCode}: {errorString}")

    def ib_connect(self):
        self.connect("127.0.0.1", self.port, self.client_id)
        threading.Thread(target=self.run, daemon=True).start()
        max_wait = 10
        while not self.isConnected() and max_wait > 0:
            time.sleep(1)
            max_wait -= 1
        return self.isConnected()

    def ib_disconnect(self):
        if self.isConnected():
            self.cancelHistoricalData(1)
            super().disconnect()
        self.sqlite_helper.close()

    def start(self):
        self.data = []
        self.event.clear()
        end_time = datetime.now(pytz.timezone('US/Eastern'))
        return self.request_data(self.contract, end_time.strftime("%Y%m%d-%H:%M:%S"), self.duration)

    def request_data(self, contract, end_time, duration):
        bar_size = barsize_valid_check(self.frequency)
        self.reqHistoricalData(1, contract, end_time, duration, bar_size, "TRADES", 1, 1, False, [])
        self.event.wait(timeout=60)
        if not self.data:
            return None
        df = pd.DataFrame(self.data, columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'])
        return df.set_index('date')

if __name__ == "__main__":
    app = IBHistoricalDataCollector(port=7497, client_id=9, symbol="MES", contract_type="FUT", frequency="1 min", duration="1 M")
    if app.ib_connect():
        try:
            df = app.start()
            if df is not None and not df.empty:
                print(df)
                df_cleaned = clean_data(df.reset_index())
                app.sqlite_helper.queue_insert(df_cleaned.to_dict('records'))
            else:
                print("Failed to retrieve historical data or data is empty.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            app.ib_disconnect()
    else:
        print("Failed to connect to TWS.")
