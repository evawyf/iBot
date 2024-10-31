
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.utils import iswrapper
from threading import Thread, Lock
import random
import redis
import sys
import time
from datetime import datetime
import threading

class IBotView(EWrapper, EClient):
    def __init__(self, port=7497):
        EClient.__init__(self, self)
        
        # Core attributes
        self.port = int(port) if port else 7497
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

    def ib_connect(self, host='127.0.0.1', port=7497):
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
