from flask import Flask, request
import json
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

from threading import Thread, Lock
from src.utils.ib_contract import create_contract
from src.utils.ib_order import create_order

import sys
import time
import random
from datetime import datetime
import redis
import os

"""
Main Flask app, receives requests from TradingView and places orders on IBKR

Usage: python iBotView.py <webhook_port> <port> <client_id> 
Note: <webhook_port> defaults to 5678 if not provided, as this is required for webhook to work, otherwise it will run on default port 5000 which will not work. 

Example: 
    python iBotView.py 5678                     # Paper Trading 7497, default client_id=999  
    python iBotView.py 5678 7496                # Live Trading, default client_id=999
    python iBotView.py 5678 7496 888            # Live Trading, custom client_id
    python iBotView.py 5678 LiveTrading 888     # Live Trading, custom client_id

"""

IB_PORT = 7497
WEBHOOK_PORT = 5678

app = Flask(__name__)

class IBotView(EWrapper, EClient):
    def __init__(self, port=IB_PORT):
        EClient.__init__(self, self)
        self.positions = {}
        self.port = int(port) if port else IB_PORT
        self.client_id = random.randint(8000, 8999)
        self.nextOrderId = 0
        self.is_connected = False
        self.order_records = {}
        self.lock = Lock()
        self.last_keepalive = time.time()
        self.init_db()

    def init_db(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)

    def ib_connect(self, host='127.0.0.1', port=IB_PORT):
        self.connect(host=host, port=port, clientId=self.client_id)
        thread = Thread(target=self.run)
        thread.start()
        
        # Wait for connection to be established
        timeout = 10  # 10 seconds timeout
        start_time = time.time()
        while not self.is_connected:
            if time.time() - start_time > timeout:
                raise ConnectionError("Timeout: Could not connect to TWS/IB Gateway")
            time.sleep(0.1)

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextOrderId = orderId
        self.is_connected = True

    def connectionClosed(self):
        super().connectionClosed()
        self.is_connected = False

    def error(self, reqId, errorCode, errorString):
        super().error(reqId, errorCode, errorString)
        print(f"Error {errorCode}: {errorString}")

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        with self.lock:
            order_key = f"order:{orderId}"
            if self.redis.exists(order_key):
                order_data = self.redis.hgetall(order_key)
                order_data[b'status'] = status.encode()
                order_data[b'filled'] = str(filled).encode()
                order_data[b'avgFillPrice'] = str(avgFillPrice).encode()
                order_data[b'lastUpdate'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S").encode()
                self.redis.hset(order_key, mapping=order_data)

    def record_order(self, order_id, symbol, contract_type, action, order_type, quantity, price):
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

    def keep_alive(self):
        current_time = time.time()
        if current_time - self.last_keepalive > 30:  # Send keepalive every 30 seconds
            self.reqCurrentTime()
            self.last_keepalive = current_time

    def currentTime(self, time:int):
        super().currentTime(time)
        print(f"Current time from server: {time}")

    def get_current_position(self, symbol):
        orders = self.redis.keys("order:*")
        position = 0
        for order_key in orders:
            order_data = self.redis.hgetall(order_key)
            if order_data[b'symbol'].decode() == symbol and float(order_data[b'filled']) > 0:
                if order_data[b'action'].decode() == 'BUY':
                    position += int(float(order_data[b'filled']))
                else:
                    position -= int(float(order_data[b'filled']))
        return position

    # For any confirmation, just open position (or reverse position)
    def strategy_simply_reverse(self, symbol, contract_type, exchange, action, order_type, price, quantity):
        if not self.is_connected:
            self.ib_connect()  # Attempt to reconnect if not connected

        self.keep_alive()

        # Get current position from filled orders
        current_position = self.get_current_position(symbol)
        print(f"Current position for {symbol}: {current_position}")

        if quantity == 0 or quantity < 0 or quantity is None: 
            quantity = 1

        if (action == 'BUY' and current_position >= 0) or (action == 'SELL' and current_position <= 0):
            order_quantity = quantity
        elif (action == 'BUY' and current_position <= 0) or (action == 'SELL' and current_position >= 0):
            order_quantity = abs(current_position) + quantity
        else:
            raise ValueError(f"Invalid action: {action} with current position: {current_position}")
        
        print(f"After adjustment, order quantity: {order_quantity}.")

        # Create contract
        try:
            contract = create_contract(symbol=symbol, contract_type=contract_type, exchange=exchange)
        except Exception as e:
            print(f"Error creating contract: {e}")
            return "Contract creation failed", 400
        
        try:
            order = create_order(order_type=order_type, action=action, totalQuantity=order_quantity, price=price) 
        except Exception as e:
            print(f"Error creating order: {e}")
            return "Order creation failed", 400

        # Place order on IBKR
        order_id = self.nextOrderId
        self.nextOrderId += 1
        try:
            self.placeOrder(order_id, contract, order)
            self.record_order(order_id, symbol, contract_type, action, order_type, order_quantity, price)
        except Exception as e:
            print(f"Error placing order: {e}")
            return "Order placement failed", 400
        
        # Update the position for the symbol based on filled orders
        self.positions[symbol] = self.get_current_position(symbol)
        return "Order Executed", 200
        
# Determine the port based on the argument passed
if len(sys.argv) > 2 and (sys.argv[2] in ['7496', 'LiveTrading', 'Live', 'LIVE']):
    port = 7496
else:
    port = IB_PORT

# Initialize IBKRClient 
ibkr = IBotView(port=port)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Decode the bytes to a string before using json.dumps
        data_str = request.data.decode('utf-8')
        print("Received data:", json.dumps(json.loads(data_str), indent=2))
        data = json.loads(data_str)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return "Invalid JSON", 400

    """
    The data format should be like this:
    {
        "ticker": "{{ticker}}",
        "action": "BUY",
        "contract": "FUT",
        "order": "MKT",
        "price": "{{close}}", 
        "reason": "Open-Long",
        "quantity": "1"
    }
    """

    symbol = data.get('ticker', None) # MES, MGC, AAPL
    contract_type = data.get('contract', None) # STK, FUT 
    exchange = data.get('exchange', None) # SMART, CME, NYSE, etc

    order_type = data.get('order', None) # MKT, LMT, (TODO: STP, TRAIL, FIXED, PARKED
    action = data.get('action', None) # BUY, SELL
    price = float(data.get('price', 0))
    quantity = int(float(data.get('quantity', "0")))

    reason = data.get('reason', None) # Open-Long, Open-Short, Close-Long, Close-Short

    try:
        result, status_code = ibkr.strategy_simply_reverse(symbol, contract_type, exchange, action, order_type, price, quantity)
        return result, status_code
    except ConnectionError as e:
        print(f"Connection error: {e}")
        return "Not connected to TWS/IB Gateway", 503
    except Exception as e:
        print(f"Error executing strategy: {e}")
        return "Strategy execution failed", 400

def start_ibkr():
    global ibkr
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            ibkr.ib_connect()  # Connect to TWS paper trading on a separate thread
            return  # If connection successful, exit the function
        except ConnectionError as e:
            print(f"Failed to connect to TWS/IB Gateway: {e}")
            retry_count += 1
            if retry_count < max_retries:
                new_client_id = random.randint(8000, 8999)
                print(f"Attempting to reconnect with new client ID: {new_client_id}")
                ibkr = IBotView(port=ibkr.port)
                ibkr.client_id = new_client_id
            else:
                print("Max retries reached. Exiting.")
                sys.exit(1)

def start_flask():
    print("Please ensure ngrok is running and connected to this port: 5678")
    app.run(debug=True, port=5678)

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


