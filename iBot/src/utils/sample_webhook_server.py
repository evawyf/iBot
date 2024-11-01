
from flask import Flask, request, jsonify
import json
import sys

app = Flask(__name__)

# Define a route for the webhook to receive TradingView alerts
@app.route('/webhook', methods=['POST'])
def webhook(app):
    data = request.json  # Get the JSON data sent by TradingView
    print("Received data:", json.dumps(data, indent=2))  # Print data for debugging

    # # Example: You can parse the 'ticker' and 'action' (buy/sell) from the alert
    ticker = data.get('ticker', None)
    action = data.get('action', None)

    # Example: You can place an order on IBKR
    # if action == 'buy':
    #     ibkr.placeOrder(1, create_contract(ticker), create_order("MKT", "BUY", 100))
    # elif action == 'sell':
    #     ibkr.placeOrder(2, create_contract(ticker), create_order("MKT", "SELL", 100))
    # return "Order Executed", 200

    if ticker and action:
        print(f"Received alert for {action} on {ticker}")

    # Respond to TradingView to acknowledge that you received the alert
    return jsonify(success=True), 200


if __name__ == '__main__':
    # Get the port from command line arguments
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5678
    # Start the web server, listening on the specified port
    app.run(debug=True, port=port)
