from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.utils import iswrapper

from utils.ib_contract import create_contract
from utils.ib_order import create_limit_order, create_market_order

import time, threading
from datetime import datetime
import random

# Help to get OrderID as a 9 digit integer: 102214010
def formatted_time_as_int():
    now = datetime.now()
    return int(now.strftime("%m%d%H%M%S"))

"""
IB API wrapper
"""
class IBOrderManager(EWrapper, EClient):
    def __init__(self, port, max_wait_time=30, task_name="OrderManager"):
        EClient.__init__(self, self)
        self.nextOrderId = None
        self.port = port
        self.client_id = random.randint(1000, 1999)
        self.max_wait_time = max_wait_time
        self.connection_event = threading.Event()
        self.order_id_lock = threading.Lock()
        self.task_name = task_name
        self.openOrders = {}
        self.openContracts = {}

    def ib_connect(self):
        # Try to connect
        try:
            self.connect('127.0.0.1', self.port, self.client_id)
        except Exception as e:
            print(f"Error connecting: {e}")
            return False

        # Start the socket in a thread
        api_thread = threading.Thread(target=self.run, daemon=True)
        api_thread.start()

        # Wait for nextValidId with a timeout
        if not self.connection_event.wait(timeout=self.max_wait_time):
            print("Timeout waiting for nextValidId. Please check your connection.")
            self.disconnect()
            return False

        print(f"Received nextValidId: {self.nextOrderId}")
        print("Connection established.")
        return True

    def ib_disconnect(self):
        print(f"Disconnecting client task [{self.task_name}] ...")
        self.disconnect()
        print(f"Client disconnected.")

    @iswrapper
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        with self.order_id_lock:
            self.nextOrderId = orderId
        print(f"The next valid order id is: {self.nextOrderId}")
        self.connection_event.set()

    @iswrapper
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"OrderStatus. Id: {orderId}, Status: {status}, Filled: {filled}, Remaining: {remaining}, LastFillPrice: {lastFillPrice}")

    @iswrapper
    def openOrder(self, orderId, contract, order, orderState):
        # The openOrder function may be called multiple times for the same order
        # This can happen when the order status changes or when TWS is providing updates
        # It's normal behavior and not necessarily an error
        print(f"OpenOrder. ID: {orderId}, {contract.symbol}, {contract.secType} @ {contract.exchange}: {order.action}, {order.orderType} Qty: {order.totalQuantity} @ ${order.lmtPrice}")
        print(f"Order State: {orderState.status}")  # Print the order state to see why it might be called multiple times
        
        # We store open orders and their corresponding contracts in separate dictionaries
        # This allows us to:
        # 1. Keep track of all open orders
        # 2. Easily access order details and contract information for each open order
        # 3. Efficiently cancel orders or modify them if needed
        # 4. Provide a quick way to check if an order is still open
        self.openOrders[orderId] = order
        self.openContracts[orderId] = contract

    @iswrapper
    def execDetails(self, reqId, contract, execution):
        print(f"ExecDetails. ReqId: {reqId}, Symbol: {contract.symbol}, SecType: {contract.secType}, Currency: {contract.currency}, Execution: {execution.execId}, Time: {execution.time}, Account: {execution.acctNumber}, Exchange: {execution.exchange}, Side: {execution.side}, Shares: {execution.shares}, Price: {execution.price}")

    def verify_contract(self, contract):
        """
        Verify if the contract is valid using the TWS API.
        
        :param contract: The Contract object to verify
        :return: True if the contract is valid, False otherwise
        """
        contract_details = []
        
        def contract_details_handler(req_id, details):
            nonlocal contract_details
            contract_details.append(details)
        
        # Set up the event handler
        self.contractDetails = contract_details_handler
        
        # Request contract details
        req_id = self.reqContractDetails(contract)
        
        # Wait for the response (with a timeout mechanism)
        timeout = 5  # seconds
        start_time = time.time()
        while not contract_details and time.time() - start_time < timeout:
            self.run()
            time.sleep(0.1)
        
        # Clean up the event handler
        self.contractDetails = None
        
        # Check if we received any contract details
        if contract_details:
            print(f"Contract verified: {contract.symbol}")
            return True
        else:
            print(f"Invalid contract: {contract.symbol}")
            return False
        

    def place_limit_order(self, symbol, contract_type, action, quantity, price):
        with self.order_id_lock:
            if self.nextOrderId is None:
                print("Error: NextOrderId not received. Ensure connection is established.")
                return
            current_order_id = self.nextOrderId
            self.nextOrderId += 1

        # Create the contract based on the type
        contract = create_contract(symbol, contract_type)
        # Create the order and place it
        order = create_limit_order(action, quantity, price)
        self.placeOrder(current_order_id, contract, order)

    def place_market_order(self, symbol, contract_type, action, quantity):
        with self.order_id_lock:
            if self.nextOrderId is None:
                print("Error: NextOrderId not received. Ensure connection is established.")
                return
            current_order_id = self.nextOrderId
            self.nextOrderId += 1

        # Create the contract based on the type
        contract = create_contract(symbol, contract_type)
        # Create the order and place it
        order = create_market_order(action, quantity)
        self.placeOrder(current_order_id, contract, order)

    def cancel_order_by_details(self, symbol, action, price):
        # Iterate through open orders to find a match
        for orderId, order in self.openOrders.items():
            contract = self.openContracts[orderId]
            
            if (contract.symbol == symbol and 
                order.action == action and 
                order.lmtPrice == price):
                
                print(f"Cancelling order: ID {orderId}, {symbol} {action} @ {price}")
                self.cancelOrder(orderId)
                return True
        
        print(f"No matching order found for {symbol} {action} @ {price}")
        return False
    
    def cancel_all_orders(self):
        if self.openOrders:
            for orderId in list(self.openOrders.keys()):
                print(f"Cancelling order: ID {orderId}")
                self.cancelOrder(orderId)
            print("All open orders have been cancelled.")
        else:
            print("No open orders to cancel.")




# Usage example:
if __name__ == "__main__":

    PORT = 7497
    PRICE = 200

    app = IBOrderManager(PORT)
    if app.ib_connect():
        try:
            # Your IB tasks go here
            # For example:
            app.place_limit_order("MES", "FUT", "BUY", 1, PRICE)
            
            # Wait for 5 seconds (or adjust as needed)
            time.sleep(5)

            for i in range(1, 6):
                app.place_limit_order("MES", "FUT", "BUY", 1, PRICE + i)
                time.sleep(1)
            
            # Cancel the order
            app.cancel_order_by_details("MES", "BUY", PRICE)

            app.place_limit_order("AAPL", "STK", "BUY", 1, 100)

            time.sleep(5)


            print("Test MGC now")
            app.place_limit_order("MGC", "FUT", "BUY", 1, 100)  
            time.sleep(1)
            app.place_market_order("MGC", "FUT", "BUY", 1)
            time.sleep(1)
            app.place_limit_order("AAPL", "STK", "SELL", 1, 100)
            time.sleep(5)
            app.place_market_order("MGC", "FUT", "SELL", 1)
            time.sleep(1)
            
            app.cancel_all_orders()

        finally:
            # Disconnect
            app.ib_disconnect()
    else:
        print("Failed to connect to TWS.")
