from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.ticktype import TickTypeEnum

class LimitOrderBookManager(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.bid_price = None
        self.ask_price = None
        self.last_price = None
        self.last_volume = None
        self.symbol = None

    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == TickTypeEnum.BID:
            self.bid_price = price
            print(f"{self.symbol} Bid Price: {self.bid_price}")
        elif tickType == TickTypeEnum.ASK:
            self.ask_price = price
            print(f"{self.symbol} Ask Price: {self.ask_price}")
        elif tickType == TickTypeEnum.LAST:
            self.last_price = price
            print(f"{self.symbol} Last Trade Price: {self.last_price}")

    def tickSize(self, reqId, tickType, size):
        if tickType == TickTypeEnum.LAST_SIZE:
            self.last_volume = size
            print(f"{self.symbol} Last Trade Volume: {self.last_volume}")

    def start_streaming(self, symbol, secType="STK", exchange="SMART", currency="USD"):
        self.symbol = symbol
        contract = Contract()
        contract.symbol = symbol
        contract.secType = secType
        contract.exchange = exchange
        contract.currency = currency

        # Request market data
        self.reqMktData(1, contract, "", False, False, [])

    def start(self):
        self.connect("127.0.0.1", 7497, 0)  # Use 7496 for TWS, 7497 for IB Gateway
        self.run()

    def stop(self):
        self.disconnect()

# Usage example
if __name__ == "__main__":
    import time
    
    manager = LimitOrderBookManager()
    
    # Start the client in a separate thread
    import threading
    api_thread = threading.Thread(target=manager.start, daemon=True)
    api_thread.start()
    
    # Wait for the connection to be established
    time.sleep(1)
    
    # Start streaming for Apple stock
    manager.start_streaming("AAPL")
    
    # Keep the main thread running to receive updates
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
    
    manager.stop()
