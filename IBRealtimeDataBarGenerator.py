from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.common import TickerId, TickAttrib
from ibapi.contract import ContractDetails

import threading, time, redis, sqlite3, queue
from datetime import datetime, timedelta
from utils.contract import create_contract
import pytz


class IBRealtimeDataBarGenerator(EWrapper, EClient):

    def __init__(self, port, client_id, symbol, contract_type, bar_frequency_seconds=60, use_redis=False):
        EClient.__init__(self, self)
        self.port = port
        self.client_id = client_id

        # Initialize contract
        self.symbol = symbol
        self.contract_type = contract_type
        self.contract = create_contract(symbol, contract_type)

        # Initialize current bar
        self.current_bar = {'open': None, 'high': None, 'low': None, 'close': None, 'volume': 0}
        self.bar_start_time = None
        self.bar_frequency = timedelta(seconds=bar_frequency_seconds)
        self.bar_frequency_str = f"{bar_frequency_seconds}s"
        self.db_name = f"data/MarketData_{self.symbol}_{self.bar_frequency_str}_{datetime.now().strftime('%Y%m%d')}.db"
        
        # Initialize Redis connection
        self.use_redis = use_redis
        if self.use_redis:
            print(f"Using Redis for market data storage: port=6379, db=0")
            self.redis_db = redis.Redis(host='localhost', port=6379, db=0)
        else:
            print(f"Not using Redis for market data storage")
        
        # Initialize SQLite
        print(f"Using SQLite for market data storage: {self.db_name}")
        self.sqlite_queue = queue.Queue()
        self.sqlite_thread = threading.Thread(target=self.sqlite_worker, daemon=True)
        self.sqlite_thread.start()

        # Initialize market status
        self.market_open = False
        self.contract_details_received = threading.Event()
        self.contract_details = None
        self.contract_details_end = threading.Event()

    def ib_connect(self):
        print("Attempting to connect to TWS...")
        if not hasattr(self, 'port') or not hasattr(self, 'client_id'):
            raise AttributeError("port and client_id must be set before calling ib_connect")
        self.connect("127.0.0.1", self.port, self.client_id)

        if not hasattr(self, 'contract_type'):
            raise AttributeError("contract_type must be set before calling ib_connect")

        # Start the socket in a thread
        api_thread = threading.Thread(target=self.run, daemon=True)
        api_thread.start()

        # Wait for connection
        time.sleep(1)  # Give it a second to connect

        if not self.isConnected():
            print("Failed to connect to TWS. Make sure it's running and allows API connections.")
            return

        print("Connected to TWS.")

        # Check if market is open
        if self.is_market_open():
            # Request market data
            print(f"Requesting market data for {self.symbol}...")
            self.reqMktData(1, self.contract, "", False, False, [])

            print(f"Fetching realtime data for {self.symbol} and generating {self.bar_frequency_str} bars. Press Ctrl+C to stop.")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Stopping data fetch...")
                self.ib_disconnect()
        else:
            print(f"Market is currently closed for {self.symbol}. No real-time data will be collected.")
            self.ib_disconnect()

    def ib_disconnect(self):
        super().disconnect()
        self.cancelMktData(1)
        self.sqlite_queue.put(("CLOSE", None))
        self.sqlite_thread.join()

    def sqlite_worker(self):
        with sqlite3.connect(self.db_name) as db:
            self.create_sqlite_table(db)
            
            while True:
                operation, args = self.sqlite_queue.get()
                
                if operation == "INSERT":
                    self.insert_data_to_sqlite(db, args)
                elif operation == "CLOSE":
                    break
                
                self.sqlite_queue.task_done()

    def create_sqlite_table(self, db):
        db.execute('''
        CREATE TABLE IF NOT EXISTS market_data (
            timestamp TEXT,
            symbol TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (timestamp, symbol)
        )
        ''')
        db.commit()

    def insert_data_to_sqlite(self, db, args):
        db.execute('''
        INSERT OR REPLACE INTO market_data 
        (timestamp, symbol, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', args)
        db.commit()

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        print(f"Error {errorCode}: {errorString}")

    def tickPrice(self, reqId: TickerId, tickType: TickAttrib, price: float, attrib: TickAttrib):
        if tickType == 4:  # Last price
            self.update_bar(price)

    def tickSize(self, reqId: TickerId, tickType: TickAttrib, size: int):
        if tickType == 8:  # Volume
            self.current_bar['volume'] += size

    def update_bar(self, price):
        current_time = datetime.now()

        if self.bar_start_time is None:
            self.bar_start_time = current_time.replace(second=0, microsecond=0)
            self.current_bar['open'] = price
            self.current_bar['high'] = price
            self.current_bar['low'] = price
            
        elif current_time >= self.bar_start_time + self.bar_frequency:
            # Complete the current bar
            self.current_bar['close'] = price
            self.add_bar_to_database(self.bar_start_time, self.current_bar)
            
            # Start a new bar
            self.bar_start_time = current_time.replace(second=0, microsecond=0)
            self.current_bar = {'open': price, 'high': price, 'low': price, 'close': price, 'volume': 0}
        else:
            self.current_bar['high'] = max(self.current_bar['high'], price)
            self.current_bar['low'] = min(self.current_bar['low'], price)

        self.current_bar['close'] = price

    def add_bar_to_database(self, timestamp, bar_data):
        # Store in Redis if enabled
        if self.use_redis:
            redis_key = f"market_data:{timestamp.isoformat()}"
            self.redis_db.hset(redis_key, mapping=bar_data)

        # Queue SQLite operation
        self.sqlite_queue.put(("INSERT", (timestamp.isoformat(), self.symbol, bar_data['open'], bar_data['high'], bar_data['low'], bar_data['close'], bar_data['volume'])))

        print(f"{self.bar_frequency_str} Bar - Time: {timestamp}, Symbol: {self.symbol}, Open: {bar_data['open']}, "
              f"High: {bar_data['high']}, Low: {bar_data['low']}, "
              f"Close: {bar_data['close']}, Volume: {bar_data['volume']}")

        # Check if the bar data is complete
        if None in bar_data.values():
            print(f"Warning: Incomplete bar data for {self.symbol} at {timestamp}")

        # Ensure volume is non-negative
        if bar_data['volume'] < 0:
            print(f"Warning: Negative volume ({bar_data['volume']}) for {self.symbol} at {timestamp}")
            bar_data['volume'] = 0

        # Check for price consistency
        if bar_data['low'] > bar_data['high'] or bar_data['open'] > bar_data['high'] or bar_data['open'] < bar_data['low'] or bar_data['close'] > bar_data['high'] or bar_data['close'] < bar_data['low']:
            print(f"Warning: Inconsistent price data for {self.symbol} at {timestamp}")

    def is_market_open(self):
        if self.contract_details is None:
            self.reqContractDetails(1, self.contract)
            self.contract_details_end.wait(timeout=10)
        
        if self.contract_details is None:
            print("Failed to retrieve contract details")
            return False

        now = datetime.now(pytz.timezone('US/Eastern'))
        trading_hours = self.contract_details.tradingHours
        sessions = trading_hours.split(';')
        
        for session in sessions:
            if '-' in session:
                start, end = session.split('-')
                start_time = datetime.strptime(start, "%Y%m%d:%H%M").replace(tzinfo=pytz.timezone('US/Eastern'))
                end_time = datetime.strptime(end, "%Y%m%d:%H%M").replace(tzinfo=pytz.timezone('US/Eastern'))
                
                if start_time <= now <= end_time:
                    return True
        
        return False

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        self.contract = contractDetails.contract
        self.contract_details_received.set()
        self.contract_details = contractDetails

    def contractDetailsEnd(self, reqId):
        self.contract_details_end.set()


if __name__ == "__main__":

    PORT = 7497
    CLIENT_ID = 0
    SYMBOL = "MES"
    CONTRACT_TYPE = "FUT"

    app = IBRealtimeDataBarGenerator(PORT, CLIENT_ID, SYMBOL, CONTRACT_TYPE, bar_frequency_seconds=60, use_redis=True)
    app.ib_connect()

    time.sleep(600)
    app.ib_disconnect()
