from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.utils import iswrapper

from utils.ib_contract import create_contract
from ibapi.contract import Contract
from utils.ib_order import create_limit_order, create_market_order

import time
import threading
from datetime import datetime
import random

def formatted_time_as_int():
    """Help to get OrderID as a 9 digit integer: 102214010"""
    now = datetime.now()
    return int(now.strftime("%m%d%H%M%S"))

class IBOrderManager(EWrapper, EClient):
    """IB API wrapper for managing orders"""
    
    def __init__(self, port, max_wait_time=30):
        EClient.__init__(self, self)
        self.nextOrderId = None
        self.port = port
        self.client_id = random.randint(2000, 2999)
        self.max_wait_time = max_wait_time
        self.connection_event = threading.Event()
        self.order_id_lock = threading.Lock()
        self.openOrders = {}
        self.openContracts = {}
        self.task_name = "OrderManager"
        self.positions = {}
        self.position_event = threading.Event()

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
        # if not self.connection_event.wait(timeout=self.max_wait_time):
        #     print("Timeout waiting for nextValidId. Please check your connection.")
        #     self.disconnect()
        #     return None

        print(f"Received nextValidId: {self.nextOrderId}")
        print("Connection established.")

    def ib_disconnect(self):
        """Disconnect from IB API"""
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
        print(f"OpenOrder. ID: {orderId}, {contract.symbol}, {contract.secType} @ {contract.exchange}: {order.action}, {order.orderType} Qty: {order.totalQuantity} @ ${order.lmtPrice}")
        print(f"Order State: {orderState.status}")
        
        self.openOrders[orderId] = order
        self.openContracts[orderId] = contract

    @iswrapper
    def execDetails(self, reqId, contract, execution):
        print(f"ExecDetails. ReqId: {reqId}, Symbol: {contract.symbol}, SecType: {contract.secType}, Currency: {contract.currency}, "
              f"Execution: {execution.execId}, Time: {execution.time}, Account: {execution.acctNumber}, Exchange: {execution.exchange}, "
              f"Side: {execution.side}, Shares: {execution.shares}, Price: {execution.price}")

    def verify_contract(self, contract):
        """Verify if the contract is valid using the TWS API."""
        contract_details = []
        
        def contract_details_handler(req_id, details):
            nonlocal contract_details
            contract_details.append(details)
        
        self.contractDetails = contract_details_handler
        req_id = self.reqContractDetails(contract)
        
        timeout = 5  # seconds
        start_time = time.time()
        while not contract_details and time.time() - start_time < timeout:
            self.run()
            time.sleep(0.1)
        
        self.contractDetails = None
        
        if contract_details:
            print(f"Contract verified: {contract.symbol}")
            return True
        
        print(f"Invalid contract: {contract.symbol}")
        return False

    def place_limit_order(self, symbol, contract_type, action, quantity, price):
        """Place a limit order"""
        with self.order_id_lock:
            if self.nextOrderId is None:
                print("Error: NextOrderId not received. Ensure connection is established.")
                return
            current_order_id = self.nextOrderId
            self.nextOrderId += 1

        contract = create_contract(symbol, contract_type)
        order = create_limit_order(action, quantity, price)
        self.placeOrder(current_order_id, contract, order)

    def place_market_order(self, symbol, contract_type, action, quantity):
        """Place a market order"""
        with self.order_id_lock:
            if self.nextOrderId is None:
                print("Error: NextOrderId not received. Ensure connection is established.")
                return
            current_order_id = self.nextOrderId
            self.nextOrderId += 1

        contract = create_contract(symbol, contract_type)
        order = create_market_order(action, quantity)
        self.placeOrder(current_order_id, contract, order)

    def cancel_order_by_details(self, symbol, action, price):
        """Cancel an order by matching its details"""
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
        """Cancel all open orders"""
        if self.openOrders:
            for orderId in list(self.openOrders.keys()):
                print(f"Cancelling order: ID {orderId}")
                self.cancelOrder(orderId)
            print("All open orders have been cancelled.")
        else:
            print("No open orders to cancel.")

    @iswrapper
    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Handle position updates"""
        if hasattr(self, 'positions'):
            symbol = contract.symbol
            self.positions[symbol] = position
            print(f"Position update received for {symbol}: {position}")
            return position
        return None

    # def request_positions(self):
    #     """Request positions from IB"""
    #     self.position_event.clear()
    #     self.reqPositions()
    #     if not self.position_event.wait(timeout=self.max_wait_time):
    #         print("Timeout waiting for positions")
    #     return self.positions

def main():
    """Main entry point for testing"""
    app = IBOrderManager(port=7497)
    PRICE = 200

    try:
        # positions = app.request_positions()
        print(f">>>>>> Positions ALL: {app.positions}")
        
        app.place_limit_order("MES", "FUT", "BUY", 1, PRICE)
        time.sleep(5)

        for i in range(1, 6):            
            app.place_limit_order("MES", "FUT", "BUY", 1, 100)
            position = app.positions.get("MES", 0)
            print(f">>>>> Position MES: {position}")
            time.sleep(5)

        print("Test MGC now")
        app.place_limit_order("MGC", "FUT", "BUY", 1, 100)  
        time.sleep(1)
        app.place_market_order("MGC", "FUT", "BUY", 1)
        position = app.positions.get("MGC", 0)
        print(f">>>>> Position MGC: {position}")
        time.sleep(1)
        app.place_limit_order("AAPL", "STK", "SELL", 1, 100)
        time.sleep(5)
        app.place_market_order("MGC", "FUT", "SELL", 1)
        time.sleep(1)
        
        app.cancel_all_orders()

    finally:
        app.ib_disconnect()

if __name__ == "__main__":
    main()
