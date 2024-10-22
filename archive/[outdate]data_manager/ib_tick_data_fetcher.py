from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import TickerId, TickAttrib, TickAttribLast
import threading
import time
from datetime import datetime
from utils.contract import create_future_contract

class IBTickDataFetcher(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.contract = None

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        print(f"Error {errorCode}: {errorString}")

    def tickPrice(self, reqId: TickerId, tickType: TickAttrib, price: float, attrib: TickAttrib):
        print(f"Tick Price. Ticker Id: {reqId}, Type: {tickType}, Price: {price}, Time: {datetime.now()}")

    def tickSize(self, reqId: TickerId, tickType: TickAttrib, size: int):
        print(f"Tick Size. Ticker Id: {reqId}, Type: {tickType}, Size: {size}, Time: {datetime.now()}")

def fetch_mes_realtime_data(symbol):
    app = IBTickDataFetcher()
    
    print("Attempting to connect to TWS...")
    app.connect("127.0.0.1", 7497, clientId=0)

    # Create MES contract
    contract = create_future_contract(symbol)

    # Start the socket in a thread
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()

    # Wait for connection
    time.sleep(1)  # Give it a second to connect

    if not app.isConnected():
        print("Failed to connect to TWS. Make sure it's running and allows API connections.")
        return

    print("Connected to TWS.")

    # Request market data
    print("Requesting market data for MES...")
    app.reqMktData(1, contract, "", False, False, [])

    print("Fetching realtime data for MES. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping data fetch...")
    finally:
        app.cancelMktData(1)
        app.disconnect()
        print("Disconnected from TWS.")

if __name__ == "__main__":
    fetch_mes_realtime_data()
