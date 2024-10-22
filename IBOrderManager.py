from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.utils import iswrapper

from utils.contract import create_contract
from utils.order import create_limit_order, create_market_order

import time, threading

"""
IB API wrapper
"""
class IBOrderManager(EWrapper, EClient):
    def __init__(self, port, client_id, max_wait_time=10):
        EClient.__init__(self, self)
        self.nextOrderId = None
        self.task_name = "OrderManager"
        self.port = port
        self.client_id = client_id
        self.max_wait_time = max_wait_time

    def ib_connect(self):
        # Try to connect
        try:
            self.connect('127.0.0.1', self.port, self.client_id)
        except Exception as e:
            print(f"Error connecting: {e}")
            return None

        # Start the socket in a thread
        api_thread = threading.Thread(target=self.run, daemon=True)
        api_thread.start()

        # Wait for nextValidId with a timeout
        start_time = time.time()
        while self.nextOrderId is None and time.time() - start_time < self.max_wait_time:
            time.sleep(0.1)

        if self.nextOrderId is None:
            print("Timeout waiting for nextValidId. Please check your connection.")
            self.disconnect()
            return None

        print(f"Received nextValidId: {self.nextOrderId}")
        print("Connection established.")


    def ib_disconnect(self):
        print(f"Disconnecting client task [{self.task_name}] ...")
        self.disconnect()
        print(f"Client disconnected.")

    @iswrapper
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextOrderId = orderId
        print(f"The next valid order id is: {self.nextOrderId}")

    @iswrapper
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"OrderStatus. Id: {orderId}, Status: {status}, Filled: {filled}, Remaining: {remaining}, LastFillPrice: {lastFillPrice}")

    @iswrapper
    def openOrder(self, orderId, contract, order, orderState):
        print(f"OpenOrder. ID: {orderId}, {contract.symbol}, {contract.secType} @ {contract.exchange}: {order.action}, {order.orderType} {order.totalQuantity} @ ${order.lmtPrice}")

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
        # Create the contract based on the type
        contract = create_contract(symbol, contract_type)
        # Create the order and place it
        order = create_limit_order(action, quantity, price)
        self.placeOrder(self.nextOrderId, contract, order)
        self.nextOrderId += 1


    def place_market_order(self, symbol, contract_type, action, quantity):
        # Create the contract based on the type
        contract = create_contract(symbol, contract_type)
        # Create the order and place it
        order = create_market_order(action, quantity)
        self.placeOrder(self.nextOrderId, contract, order)  
        self.nextOrderId += 1


    def cancel_order_by_details(self, symbol, action, price):
        # Iterate through open orders to find a match
        for orderId in self.openOrders:
            order = self.openOrders[orderId]
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
        if hasattr(self, 'openOrders'):
            for orderId in list(self.openOrders.keys()):
                print(f"Cancelling order: ID {orderId}")
                self.cancelOrder(orderId)
            print("All open orders have been cancelled.")
        else:
            print("No open orders to cancel.")
            

    @iswrapper
    def openOrder(self, orderId, contract, order, orderState):
        # Call the parent class method
        super().openOrder(orderId, contract, order, orderState)
        
        # Initialize dictionaries if they don't exist
        if not hasattr(self, 'openOrders'):
            self.openOrders = {}
        if not hasattr(self, 'openContracts'):
            self.openContracts = {}
        
        # Store the order and contract information
        self.openOrders[orderId] = order
        self.openContracts[orderId] = contract
        
        # Print order details
        print(f"OpenOrder. ID: {orderId}, {contract.symbol}, {contract.secType} @ {contract.exchange}: {order.action}, {order.orderType} {order.totalQuantity} @ ${order.lmtPrice}")

    # Note: The openOrder function is called by the IB API when an order is placed or its status changes.
    # It keeps track of open orders and their associated contracts, which is used by cancelOrderByDetails.




# Usage example:
if __name__ == "__main__":

    PORT = 7497
    PRICE = 200

    app = IBOrderManager(PORT, 1)
    app.ib_connect()

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

    # Don't forget to disconnect when done
    # app.disconnect()

    app.place_limit_order("AAPL", "STK", "BUY", 1, 100)

    time.sleep(10)
    app.cancel_all_orders()

    # Disconnect
    app.ib_disconnect()
