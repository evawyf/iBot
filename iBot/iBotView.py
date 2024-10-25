from flask import Flask, request
import json
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

from threading import Thread
from src.utils.ib_contract import create_contract
from src.utils.ib_order import create_order

import sys
import time
import random
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
    def __init__(self, default_quantity=1, port=IB_PORT, client_id=888):
        EClient.__init__(self, self)
        self.default_quantity = default_quantity
        self.positions = {}
        self.port = int(port) if port else 7497
        self.client_id = client_id
        self.nextOrderId = 0
        self.is_connected = False

    def ib_connect(self):
        self.connect(host='127.0.0.1', port=self.port, clientId=self.client_id)
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

    # For any confirmation, just open position (or reverse position)
    def strategy_simply_reverse(self, symbol, contract_type, action, order_type, price, current_position, desired_position):
        if not self.is_connected:
            raise ConnectionError("Not connected to TWS/IB Gateway")

        if desired_position == 0: 
            desired_position = self.default_quantity

        if current_position == 0: 
            quantity = desired_position
        elif desired_position > current_position > 0 and action == 'BUY':
            quantity = desired_position - current_position
        elif desired_position < current_position < 0 and action == 'SELL':
            quantity = abs(desired_position - current_position)
        else:
            raise ValueError(f"Invalid action: {action}, current position: {current_position}, desired position: {desired_position}")       
        
        # Create contract
        try:
            contract = create_contract(symbol=symbol, contract_type=contract_type)
        except Exception as e:
            print(f"Error creating contract: {e}")
            return "Contract creation failed", 400
        
        try:
            order = create_order(order_type=order_type, action=action, totalQuantity=quantity, price=price) 
        except Exception as e:
            print(f"Error creating order: {e}")
            return "Order creation failed", 400

        # Place order on IBKR
        order_id = self.nextOrderId
        self.nextOrderId += 1
        try:
            self.placeOrder(order_id, contract, order)
        except Exception as e:
            print(f"Error placing order: {e}")
            return "Order placement failed", 400
        
        self.positions[symbol] = desired_position
        return "Order Executed", 200
        
# Determine the port based on the argument passed
if len(sys.argv) > 2 and (sys.argv[2] in ['7496', 'LiveTrading', 'Live', 'LIVE']):
    port = 7496
else:
    port = IB_PORT

if len(sys.argv) > 3 and sys.argv[3].isdigit():
    client_id = int(sys.argv[3])
else:
    client_id = random.randint(900, 999)

def get_new_client_id(client_id):
    return client_id + 1

# Initialize IBKRClient 
ibkr = IBotView(port=port, client_id=client_id)

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

    order_type = data.get('order', None) # MKT, LMT, (TODO: STP, TRAIL, FIXED, PARKED
    action = data.get('action', None) # BUY, SELL
    price = float(data.get('price', 0))
    quantity = int(data.get('quantity', "0"))

    reason = data.get('reason', None) # Open-Long, Open-Short, Close-Long, Close-Short

    try:
        ibkr.strategy_simply_reverse(symbol, contract_type, action, order_type, price, ibkr.positions.get(symbol, 0), quantity)
    except ConnectionError as e:
        print(f"Connection error: {e}")
        return "Not connected to TWS/IB Gateway", 503
    except Exception as e:
        print(f"Error executing strategy: {e}")
        return "Strategy execution failed", 400

    return "Order Executed", 200

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
                new_client_id = get_new_client_id(ibkr.client_id)
                print(f"Attempting to reconnect with new client ID: {new_client_id}")
                ibkr = IBotView(port=ibkr.port, client_id=new_client_id)
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

# The error "Failed to connect to TWS/IB Gateway: Timeout: Could not connect to TWS/IB Gateway"
# occurs because the script was unable to establish a connection with the TWS (Trader Workstation)
# or IB Gateway within the specified timeout period (10 seconds in the ib_connect method).

# Possible reasons for this error:
# 1. TWS or IB Gateway is not running on your machine.
# 2. TWS or IB Gateway is running but not configured to accept API connections.
# 3. The port number specified (7497 for paper trading or 7496 for live trading) is incorrect.
# 4. There's a firewall or antivirus software blocking the connection.
# 5. The API connection settings in TWS or IB Gateway are not properly configured.

# To resolve this:
# 1. Ensure TWS or IB Gateway is running before starting this script.
# 2. In TWS or IB Gateway, go to File -> Global Configuration -> API -> Settings and make sure
#    "Enable ActiveX and Socket Clients" is checked.
# 3. Verify that the correct port number is being used (7497 for paper trading, 7496 for live trading).
# 4. Temporarily disable firewall or antivirus software to test if they're causing the issue.
# 5. In TWS or IB Gateway, ensure that the API settings allow connections from the IP address
#    where this script is running (usually 127.0.0.1 for localhost).

# If the issue persists, you may want to increase the timeout period in the ib_connect method
# to give more time for the connection to be established.
