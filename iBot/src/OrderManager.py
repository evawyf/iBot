from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.utils import iswrapper

from ibapi.contract import Contract
from ibapi.order import Order

import time
import threading
from datetime import datetime
import random


class OrderManager(EWrapper, EClient):
    """IB API wrapper for managing orders"""
    
    def __init__(self, port, max_wait_time=30):
        EClient.__init__(self, self)
        self.nextOrderId = None
        self.port = port
        self.client_id = random.randint(2000, 2999)
        self.max_wait_time = max_wait_time
        self.connection_event = threading.Event()
        self.openOrders = {}
        self.openContracts = {}
        self.task_name = "OrderManager"
        self.positions = {}
        self.position_event = threading.Event()

        # Contract mapping
        self.contract_map = {
            "MES": "MESZ4",  # Micro E-mini S&P 500 June 2024
            "MGC": "MGCZ4",  # Micro Gold June 2024
            "MNQ": "MNQZ4",  # Micro E-mini Nasdaq-100 June 2024
            "MBT": "MBTX4",  # Micro Bitcoin June 2024
            "M2K": "M2KZ4",   # Micro Russell 2000 June 2024
            "MYM": "MYMZ4"   # Micro E-mini Dow June 2024 (fixed comment)
        }

        self.exchange_map = {
            # Micro Futures
            "MES": "CME",
            "MGC": "COMEX",
            "MNQ": "CME", 
            "MBT": "CME",
            "M2K": "CME",    # Added missing M2K
            "MYM": "CME",    # Added missing MYM

            # Stocks
            "AAPL": "NYSE",
            "JPM": "NYSE",
            "JNJ": "NYSE", 
            "V": "NYSE",
            "PG": "NYSE",
            "MSFT": "NASDAQ",
            "GOOGL": "NASDAQ",
            "AMZN": "NASDAQ",
            "FB": "NASDAQ",
            "TSLA": "NASDAQ"
        }

        self.tick_size = {
            "MES": 0.25,
            "MGC": 0.10,
            "MNQ": 0.25,
            "MBT": 5.00,
            "M2K": 0.10,   # Added missing M2K
            "MYM": 1.00    # Added missing MYM
        }

        # Try to connect
        try:
            self.connect('127.0.0.1', self.port, self.client_id)
        except Exception as e:
            print(f"Error connecting: {e}")
            raise

        # Start the socket in a thread
        api_thread = threading.Thread(target=self.run, daemon=True)
        api_thread.start()

        # Wait for connection and nextOrderId
        timeout = time.time() + max_wait_time
        while not self.nextOrderId and time.time() < timeout:
            time.sleep(0.1)
            
        if not self.nextOrderId:
            raise TimeoutError("Failed to receive nextOrderId within timeout period")

        print(f"Received nextValidId: {self.nextOrderId}")
        print("Connection established.")

    def ib_disconnect(self):
        """Disconnect from IB API"""
        print(f"Disconnecting client task [{self.task_name}] ...")
        self.disconnect()
        print("Client disconnected.")

    @iswrapper
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextOrderId = orderId
        print(f"The next valid order id is: {self.nextOrderId}")
        self.connection_event.set()

    """
    Place an order for either futures or stocks
    """
    def place_order(self, symbol, sec_type, order_type, action, quantity, price=None):
        if sec_type == "FUT":
            return self.place_futures_order(symbol, order_type, action, quantity, price)
        elif sec_type == "STK":
            return self.place_stock_order(symbol, order_type, action, quantity, price)
        else:
            raise ValueError(f"Invalid order type: {sec_type}")

    def place_futures_order(self, symbol, order_type, action, quantity, price=None):
        """
        Place an order for the front month futures contract
        """
        if not symbol or not order_type or not action or not quantity:
            raise ValueError("Missing required parameters")
            
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        if order_type == "LMT" and (price is None or price <= 0):
            raise ValueError("Valid price required for limit orders")
            
        # For futures contract, "MES1!" -> "MES" 
        symbol = symbol[:-2] if symbol[-1] == '!' and symbol[-2].isdigit() else symbol
        
        try:
            # Create futures contract
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "FUT"
            contract.exchange = self.get_exchange(symbol)
            contract.currency = "USD"
            contract.localSymbol = self.contract_map.get(symbol)
            
            if not contract.localSymbol:
                raise ValueError(f"No contract mapping found for symbol {symbol}")
            
            # Create the order
            order = self.create_order(symbol, order_type, action, quantity, price)
            
            # Place the order
            current_order_id = self.nextOrderId
            self.nextOrderId += 1
            
            print(f"Placing order for {contract.localSymbol}")
            self.placeOrder(current_order_id, contract, order)
            return current_order_id
            
        except Exception as e:
            print(f"Error placing futures order: {str(e)}")
            raise

    def place_stock_order(self, symbol, order_type, action, quantity, price=None):
        """
        Place an order for stocks
        """
        if not symbol or not order_type or not action or not quantity:
            raise ValueError("Missing required parameters")
            
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        if order_type == "LMT" and (price is None or price <= 0):
            raise ValueError("Valid price required for limit orders")
            
        try:
            # Create stock contract
            contract = self.create_contract(symbol, "STK")
            
            # Create the order
            order = self.create_order(symbol, order_type, action, quantity, price)
            
            # Place the order
            current_order_id = self.nextOrderId
            self.nextOrderId += 1
            
            print(f"Placing order for {contract.symbol}")
            self.placeOrder(current_order_id, contract, order)
            return current_order_id
            
        except Exception as e:
            print(f"Error placing stock order: {str(e)}")
            raise

    @iswrapper
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, 
                    permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
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

    def get_exchange(self, symbol):
        """
        Maps symbols to their most popular exchanges.
        """
        if not symbol:
            raise ValueError("Symbol is required")

        return self.exchange_map.get(symbol, "SMART")

    def create_contract(self, symbol, secType):
        if not symbol or not secType:
            raise ValueError("Symbol and secType are required")
            
        contract = Contract()
        if secType in ["FUT", "CONTFUT", "futures", "fut"]:
            contract.symbol = symbol[:-2] if symbol[-1] == '!' and symbol[-2].isdigit() else symbol
            contract.secType = "FUT"
            contract.exchange = self.get_exchange(symbol)
            contract.currency = "USD"
            contract.localSymbol = self.contract_map.get(symbol)
            
            if not contract.localSymbol:
                raise ValueError(f"No contract mapping found for symbol {symbol}")
                
            return contract
            
        elif secType in ["STK", "stock", "stk"]:
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = self.get_exchange(symbol)
            contract.currency = "USD"
            return contract
        
        else:
            raise ValueError(f"Invalid security type: {secType}")

    def create_order(self, symbol, order_type, action, totalQuantity=1, lmt_price=None):
        if not symbol or not order_type or not action or not totalQuantity:
            raise ValueError("Missing required parameters")
            
        if totalQuantity <= 0:
            raise ValueError("Total quantity must be positive")
            
        # for futures contract, "MES1!" -> "MES"
        symbol = symbol[:-2] if symbol[-1] == '!' and symbol[-2].isdigit() else symbol
    
        if action.upper() == "BUY":
            signal = 1
        elif action.upper() == "SELL":
            signal = -1
        else:
            raise ValueError(f"Invalid action {action}, should be BUY or SELL")

        order = Order()
        order.action = action
        order.totalQuantity = totalQuantity
        order.eTradeOnly = False
        order.firmQuoteOnly = False

        if order_type == "MKT":
            order.orderType = "MKT"
            print(f"[MKT Order] created with action: {order.action}, totalQuantity: {order.totalQuantity}, orderType: {order.orderType}")
        
        elif order_type == "LMT":
            if lmt_price is None or lmt_price <= 0:
                raise ValueError("Limit price must be positive")
                
            tick = self.tick_size.get(symbol, 1)
            if symbol not in self.tick_size:
                print("Warning: New symbol and tick size not supported, using default tick size of 1")
                
            price = round(lmt_price / tick + signal) * tick

            order.orderType = "LMT"
            order.lmtPrice = price
            print(f"[LMT Order] created with action: {order.action}, totalQuantity: {order.totalQuantity}, orderType: {order.orderType}, lmtPrice: {order.lmtPrice}")
        
        else:
            raise ValueError(f"Invalid order type: {order_type}")
        
        return order

    def cancel_order_by_details(self, symbol, action, price):
        """Cancel an order by matching its details"""
        if not symbol or not action or price is None:
            raise ValueError("Missing required parameters")
            
        if not self.openOrders:
            print("No open orders to cancel")
            return False
            
        for orderId, order in self.openOrders.items():
            contract = self.openContracts.get(orderId)
            if not contract:
                continue
                
            if (contract.symbol == symbol and 
                order.action == action and 
                order.lmtPrice == price):
                
                print(f"Cancelling order: ID {orderId}, {symbol} {action} @ {price}")
                self.cancelOrder(orderId)
                return True
        
        print(f"No matching order found for {symbol} {action} @ {price}")
        return False
    
    # TODO: Seems it can only cancel for current function order, not any order which still live in TWS
    def cancel_all_orders(self):
        """Cancel all open orders"""
        if self.openOrders:
            for orderId in list(self.openOrders.keys()):
                print(f"Cancelling order: ID {orderId}")
                self.cancelOrder(orderId)
            print("All open orders have been cancelled.")
        else:
            print("No open orders to cancel.")

    def cancel_order_by_id(self, order_id):
        """Cancel a specific unfilled order by order ID"""
        if order_id not in self.openOrders:
            print(f"No open order found with ID {order_id}")
            return False
            
        print(f"Cancelling order: ID {order_id}")
        self.cancelOrder(order_id)
        return True

    @iswrapper
    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Handle position updates"""
        if hasattr(self, 'positions'):
            symbol = contract.symbol
            self.positions[symbol] = position
            print(f"Position update received for {symbol}: {position}")
            self.position_event.set()
            return position
        return None

def main():
    """Main entry point for testing"""
    app = None
    try:
        app = OrderManager(port=7497)
        
        # Test different order types
        test_orders = [
            ("MES1!", "FUT", "LMT", "BUY", 1, 800.00567),
            ("MES2!", "FUT", "LMT", "BUY", 1, 700.0056756),
            ("MGC1!", "FUT", "LMT", "BUY", 1, 700.0045645),
            ("MNQ1!", "FUT", "LMT", "BUY", 1, 700.0023423),
            ("MBT1!", "FUT", "LMT", "BUY", 1, 700.0045645),
            ("AAPL", "STK", "LMT", "BUY", 1, 150.00), 
            ("GOOGL", "STK", "LMT", "BUY", 1, 153.00),
            ("AMZN", "STK", "LMT", "BUY", 1, 155.00)
        ]
        
        for symbol, sec_type, order_type, action, qty, price in test_orders:
            order_id = app.place_order(symbol, sec_type, order_type, action, qty, price)
            print(f"Placed {sec_type} {order_type} order {order_id}: {symbol} {action} {qty} @ {price}")
            time.sleep(1)
            
            # Test cancelling individual order
            if symbol == "MGC1!":
                app.cancel_order_by_id(order_id)
                print(f"Cancelled order {order_id}")
                time.sleep(1)

        time.sleep(5)  # Wait to see the order status
        app.cancel_all_orders()
        
    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise
    finally:
        if app:
            app.ib_disconnect()

if __name__ == "__main__":
    main()
