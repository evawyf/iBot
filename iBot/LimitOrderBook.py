from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.ticktype import TickTypeEnum

class LimitOrderBook(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.bid_price = None
        self.bid_size = None
        self.data_received = False

    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == TickTypeEnum.BID:
            self.bid_price = price
            self.data_received = True
            print(f"Bid Price: {self.bid_price}")

    def tickSize(self, reqId, tickType, size):
        if tickType == TickTypeEnum.BID_SIZE:
            self.bid_size = size
            print(f"Bid Size: {self.bid_size}")

    def get_bid_price(self, symbol, secType="STK", exchange="SMART", currency="USD"):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = secType
        contract.exchange = exchange
        contract.currency = currency

        self.data_received = False
        self.reqMktData(1, contract, "", False, False, [])

    def start(self):
        self.connect("127.0.0.1", 7497, 0)  # Use 7496 for TWS, 7497 for IB Gateway
        self.run()

# Usage example
if __name__ == "__main__":
    import time
    
    app = LimitOrderBook()
    app.start()
    
    # Request bid price for Apple stock
    app.get_bid_price("AAPL")
    
    # Wait for data to be received
    timeout = 10
    start_time = time.time()
    while not app.data_received and time.time() - start_time < timeout:
        time.sleep(0.1)
    
    if app.data_received:
        print(f"Best Bid for AAPL: Price = {app.bid_price}, Size = {app.bid_size}")
    else:
        print("Timeout: No bid data received")
    
    app.disconnect()