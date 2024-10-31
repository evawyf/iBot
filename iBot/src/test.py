from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import time
from datetime import datetime

class TestApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.order_placed = False
        self.contract_details = []
        self.contract_ready = False
        self.nextOrderId = None
        
    def error(self, reqId, errorCode, errorString):
        print(f'Error {errorCode}: {errorString}')
        
    def nextValidId(self, orderId):
        print("Connected to TWS/IB Gateway!")
        self.nextOrderId = orderId
        self.get_contract_details()
        
    def contractDetails(self, reqId, contractDetails):
        # Store contract details
        self.contract_details.append(contractDetails)
        
    def contractDetailsEnd(self, reqId):
        # Called when all contract details are received
        if self.contract_details:
            # Sort by expiration and get front month
            self.contract_details.sort(key=lambda x: datetime.strptime(x.contractMonth, '%Y%m'))
            front_contract = self.contract_details[0].contract
            print(f"Using front month contract: {front_contract.localSymbol}")
            self.contract_ready = True
            self.start_trading(front_contract)
            
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, 
                   permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f'Order Status - OrderId: {orderId}, Status: {status}, Filled: {filled}')
        if status == "Filled":
            self.order_placed = True
            
    def get_contract_details(self):
        # Create contract object for MES futures
        contract = Contract()
        contract.symbol = "MES"
        contract.secType = "FUT"
        contract.exchange = "CME"
        contract.currency = "USD"
        
        print("Requesting contract details...")
        self.reqContractDetails(1, contract)
            
    def start_trading(self, contract):
        if self.nextOrderId is None:
            print("Error: NextOrderId not received")
            return
            
        # Create market order
        order = Order()
        order.action = "BUY"
        order.totalQuantity = 1
        order.orderType = "MKT"
        order.eTradeOnly = False
        order.firmQuoteOnly = False
        
        print(f"Placing order with ID {self.nextOrderId}...")
        self.placeOrder(self.nextOrderId, contract, order)
        self.nextOrderId += 1

def main():
    app = TestApp()
    app.connect("127.0.0.1", 7497, 0)
    
    # Run the client
    app.run()
    
    # Wait for order to be placed
    timeout = 10  # 10 seconds timeout
    start_time = time.time()
    while not app.order_placed and time.time() - start_time < timeout:
        time.sleep(0.1)
        
    if app.order_placed:
        print("Order successfully placed and filled")
    else:
        print("Order placement timed out or failed")
    
    app.disconnect()

if __name__ == "__main__":
    main()
