from flask import Flask, request
import json
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.utils import iswrapper
from threading import Thread, Lock
from datetime import datetime
import sys
import time
import random
import redis
import os
import threading

from src.utils.ib_contract import create_contract
from src.utils.ib_order import create_order
from src.strategies.tv_signal_overlays_helper import reverse_position_quantity_adjustment_helper

"""
Main Flask app that receives requests from TradingView and places orders on IBKR

Usage: python iBotView.py <webhook_port> <port> <client_id>

Arguments:
    webhook_port: Port for webhook (defaults to 5678)
    port: IB Gateway port (defaults to 7497 for paper trading)
    client_id: Custom client ID (randomly generated if not provided)

Examples:
    python iBotView.py 5678                  # Paper Trading (port 7497)
    python iBotView.py 5678 7496             # Live Trading
    python iBotView.py 5678 7496 888         # Live Trading with custom client ID
"""

# Parse command line arguments
WEBHOOK_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5678
IB_PORT = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 7497
DEFAULT_QUANTITY = 1

app = Flask(__name__)

class IBotView(EWrapper, EClient):
    def __init__(self, port=IB_PORT):
        EClient.__init__(self, self)
        
        # Core attributes
        self.port = int(port) if port else IB_PORT
        self.client_id = random.randint(8000, 8999)
        self.task_name = "IBotView"
        self.is_connected = False
        
        # Order management
        self.nextOrderId = 0
        self.openOrders = {}
        self.order_records = {}
        self.order_id_lock = Lock()
        
        # Position tracking
        self.positions = {}
        self.openContracts = {}
        self.contractDetails = {}
        
        # Threading and synchronization
        self.lock = Lock()
        self.position_event = threading.Event()
        self.connection_event = threading.Event()
        self.last_keepalive = time.time()
        
        # Initialize Redis connection
        self.init_db()

    def init_db(self):
        """Initialize Redis database connection"""
        try:
            self.redis = redis.Redis(host='localhost', port=6379, db=0)
            self.redis.ping()
            
            # Initialize positions hash if it doesn't exist
            if not self.redis.exists('positions'):
                self.redis.hset('positions', 'init', '1')
                
        except redis.ConnectionError:
            print("Error: Could not connect to Redis. Please ensure Redis server is running.")
            sys.exit(1)

    def ib_connect(self, host='127.0.0.1', port=IB_PORT):
        """Establish connection to IB Gateway/TWS"""
        try:
            self.connect(host=host, port=port, clientId=self.client_id)
            
            # Start message processing thread
            thread = Thread(target=self.run)
            thread.start()
            
            # Wait for connection with timeout
            timeout = 10
            start_time = time.time()
            while not self.is_connected:
                if time.time() - start_time > timeout:
                    raise ConnectionError("Timeout: Could not connect to TWS/IB Gateway")
                time.sleep(0.1)
            
            # Request initial positions
            self.reqPositions()
            
        except Exception as e:
            print(f"Error connecting to TWS/IB Gateway: {e}")
            raise

    def ib_disconnect(self):
        """Disconnect from IB API"""
        print(f"Disconnecting client task [{self.task_name}] ...")
        self.disconnect()
        print("Client disconnected.")

    @iswrapper
    def nextValidId(self, orderId: int):
        """Callback when connection is established and next valid order ID is received"""
        super().nextValidId(orderId)
        with self.order_id_lock:
            self.nextOrderId = orderId
        print(f"Next valid order ID: {self.nextOrderId}")
        self.connection_event.set()
        self.is_connected = True

    @iswrapper
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        """Callback for order status updates"""
        print(f"OrderStatus. Id: {orderId}, Status: {status}, Filled: {filled}, Remaining: {remaining}, LastFillPrice: {lastFillPrice}")
        
        with self.lock:
            order_key = f"order:{orderId}"
            if self.redis.exists(order_key):
                order_data = self.redis.hgetall(order_key)
                order_data[b'status'] = status.encode()
                order_data[b'filled'] = str(filled).encode()
                order_data[b'avgFillPrice'] = str(avgFillPrice).encode()
                order_data[b'lastUpdate'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S").encode()
                self.redis.hset(order_key, mapping=order_data)

    @iswrapper
    def openOrder(self, orderId, contract, order, orderState):
        """Callback when order is opened"""
        print(f"OpenOrder. ID: {orderId}, {contract.symbol}, {contract.secType} @ {contract.exchange}: "
              f"{order.action}, {order.orderType} Qty: {order.totalQuantity} @ ${order.lmtPrice}")
        print(f"Order State: {orderState.status}")
        
        self.openOrders[orderId] = order
        self.openContracts[orderId] = contract

    @iswrapper
    def execDetails(self, reqId, contract, execution):
        """Callback for execution details"""
        print(f"ExecDetails. ReqId: {reqId}, Symbol: {contract.symbol}, SecType: {contract.secType}, "
              f"Currency: {contract.currency}, Execution: {execution.execId}, Time: {execution.time}, "
              f"Account: {execution.acctNumber}, Exchange: {execution.exchange}, Side: {execution.side}, "
              f"Shares: {execution.shares}, Price: {execution.price}")

    def connectionClosed(self):
        """Callback when connection is closed"""
        super().connectionClosed()
        self.is_connected = False

    def error(self, reqId, errorCode, errorString):
        """Callback for error messages"""
        super().error(reqId, errorCode, errorString)
        print(f"Error {errorCode}: {errorString}")

    def contractDetails(self, reqId: int, contractDetails):
        """Store contract details when received"""
        super().contractDetails(reqId, contractDetails)
        self.contractDetails[reqId] = contractDetails

    def contractDetailsEnd(self, reqId: int):
        """Called when all contract details have been received"""
        super().contractDetailsEnd(reqId)
        print(f"Contract details request completed for reqId: {reqId}")

    @iswrapper
    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Handle position updates"""
        if hasattr(self, 'positions'):
            symbol = contract.symbol
            self.positions[symbol] = position
            print(f"Position update received for {symbol}: {position}")
            return position
        return None

    def record_order(self, order_id, symbol, contract_type, action, order_type, quantity, price):
        """Record order details in Redis"""
        with self.lock:
            order_data = {
                'symbol': symbol,
                'contract_type': contract_type,
                'action': action,
                'order_type': order_type,
                'quantity': str(quantity),
                'price': str(price),
                'status': 'Submitted',
                'filled': '0',
                'avgFillPrice': '0',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'lastUpdate': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.redis.hset(f"order:{order_id}", mapping=order_data)

# Initialize IBKRClient
ibkr = IBotView(port=IB_PORT)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests from TradingView"""
    try:
        # Parse incoming JSON data
        data_str = request.data.decode('utf-8')
        print("Received data:", json.dumps(json.loads(data_str), indent=2))
        data = json.loads(data_str)
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return "Invalid JSON", 400

    # Validate required fields
    required_fields = ['ticker', 'action', 'contract', 'order', 'price', 'reason']
    for field in required_fields:
        if field not in data:
            return f"Missing required field: {field}", 400

    # Extract order parameters
    symbol = data.get('ticker')  # MES1!, MGC1!, AAPL
    contract_type = data.get('contract')  # STK, FUT
    exchange = data.get('exchange', 'SMART')  # SMART, CME, NYSE, etc
    
    # Handle futures contract symbols
    if contract_type == "FUT":
        symbol = symbol[:-2] if symbol[-1] == '!' and symbol[-2].isdigit() else symbol

    order_type = data.get('order')  # MKT, LMT
    action = data.get('action').upper()  # BUY, SELL
    reason = data.get('reason').lower()  # Open-Long, Open-Short, Close-Long, Close-Short
    
    try:
        price = float(data.get('price', 0))
        quantity = int(data.get('quantity', DEFAULT_QUANTITY))
    except ValueError as e:
        return f"Invalid price or quantity format: {str(e)}", 400

    # Adjust quantity based on current position 
    adjusted_quantity = reverse_position_quantity_adjustment_helper(ibkr.positions.get(symbol, 0), 
                                                                    symbol, action, quantity, reason)

    # Create contract and order objects
    contract = create_contract(symbol=symbol, contract_type=contract_type, exchange=exchange)
    order = create_order(order_type=order_type, action=action, totalQuantity=adjusted_quantity, price=price)

    try:
        # Place order on IBKR
        order_id = ibkr.nextOrderId
        ibkr.nextOrderId += 1
        
        try:
            ibkr.placeOrder(order_id, contract, order)
            ibkr.record_order(order_id, symbol, contract_type, action, order_type, adjusted_quantity, price)
        except Exception as e:
            print(f"Error placing order: {e}")
            return "Order placement failed", 400
        
        return "Order Executed", 200
        
    except ConnectionError as e:
        print(f"Connection error: {e}")
        return "Not connected to TWS/IB Gateway", 503
    except Exception as e:
        print(f"Error executing strategy: {e}")
        return "Strategy execution failed", 400
    

def start_ibkr():
    """Initialize and start IB connection with retry logic"""
    global ibkr
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            ibkr.ib_connect()
            return
        except ConnectionError as e:
            print(f"Failed to connect to TWS/IB Gateway: {e}")
            retry_count += 1
            
            if retry_count < max_retries:
                new_client_id = random.randint(8000, 8999)
                print(f"Attempting to reconnect with new client ID: {new_client_id}")
                ibkr = IBotView(port=IB_PORT)
                ibkr.client_id = new_client_id
            else:
                print("Max retries reached. Exiting.")
                sys.exit(1)


def reverse_position_quantity_adjustment_helper(current_position, symbol, action, quantity, reason):
    # Calculate adjusted quantity based on current position
    print(f"[Current position] [{symbol}]: {current_position}")

    reverse_position = reason.lower().startswith('open')
    print(f"[Reverse position] : {reverse_position}")
    if reverse_position == False:
        return quantity
    
    opposite_position = (current_position > 0 and action == "SELL") or (current_position < 0 and action == "BUY")
    print(f"[Opposite position] : {opposite_position}")
    if opposite_position:
        adjusted_quantity = abs(quantity) + abs(current_position)
        print(f"[Adjusted quantity] : {adjusted_quantity}")
    else:
        adjusted_quantity = quantity
        print(f"Same direction, no adjustment: {adjusted_quantity}")

    return adjusted_quantity


def start_flask():
    """Start Flask web server"""
    print("Please ensure ngrok is running and connected to this port: 5678")
    app.run(debug=True, port=WEBHOOK_PORT)



if __name__ == '__main__':
    # Start IBotView in a separate thread
    ibkr_thread = Thread(target=start_ibkr)
    ibkr_thread.start()

    # Wait for the connection to be established
    timeout = 30  # 30 seconds timeout
    start_time = time.time()
    while not ibkr.is_connected:
        if time.time() - start_time > timeout:
            print("Timeout: Could not connect to TWS/IB Gateway")
            sys.exit(1)
        time.sleep(0.1)

    # Start Flask app in the main thread
    start_flask()
