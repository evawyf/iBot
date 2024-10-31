from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from src.strategies.SignalProcessor import SignalProcessor
from src.strategies.ExampleStrategy import SimpleMovingAverageStrategy
import time, random

class TradingApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.client_id = random.randint(9000, 9999)
        self.signal_processor = SignalProcessor(self)
        
        # Initialize strategies
        symbols = ["MES", "MNQ", "MGC", "MBT"]  # Example symbols
        sma_strategy = SimpleMovingAverageStrategy(symbols)
        self.signal_processor.add_strategy(sma_strategy)

    def error(self, reqId, errorCode, errorString):
        print(f"Error {errorCode}: {errorString}")

    def nextValidId(self, orderId):
        """Called when connection is established"""
        super().nextValidId(orderId)
        self.start()

    def start(self):
        """Start the trading process"""
        print("Starting trading system...")
        
        # Request market data for all symbols
        for symbol in self.signal_processor.active_symbols:
            # Request real-time data
            contract = self.signal_processor._create_contract(symbol)
            self.reqMktData(1, contract, "", False, False, [])

    def tickPrice(self, reqId, tickType, price, attrib):
        """Handle price updates"""
        # Update strategy with new prices
        symbol = self.get_symbol_for_reqId(reqId)  # You'll need to implement this
        for strategy in self.signal_processor.strategies:
            if isinstance(strategy, SimpleMovingAverageStrategy):
                strategy.update_price(symbol, price)

        # Process signals
        self.signal_processor.process_signals()

def main():
    app = TradingApp()
    app.connect("127.0.0.1", 7497, 0)  # Adjust port as needed
    
    # Start the event loop
    while app.isConnected():
        app.run()
        time.sleep(0.1)

if __name__ == "__main__":
    main() 