from flask import Flask, request
import json

from threading import Thread, Lock
from datetime import datetime
import sys
import time
import random
import redis
import os
import threading

from src.iBotViewApp import IBotView
from src.OrderManager import OrderManager
from iBot.src.utils.sample_ib_contract import create_contract
from iBot.src.utils.sample_ib_order import create_order
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

# Initialize IBKRClient
ibkr = IBotView(port=IB_PORT)
orderManager = OrderManager(port=IB_PORT)

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
    exchange = data.get('exchange', None)  # SMART, CME, NYSE, etc
    
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
    order_id = orderManager.place_order(symbol, order_type, action, adjusted_quantity, price)

    try:
        # Place order on IBKR
        order_id = orderManager.nextOrderId
        orderManager.nextOrderId += 1
        
        try:
            orderManager.placeOrder(order_id, contract, order)
            orderManager.record_order(order_id, symbol, contract_type, action, order_type, adjusted_quantity, price)
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
