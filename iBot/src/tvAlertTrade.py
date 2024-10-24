from flask import Flask, request
import json
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from threading import Thread
from utils.ib_contract import create_contract
from utils.ib_order import create_order

app = Flask(__name__)

class IBKRClient(EWrapper, EClient):
    def __init__(self, port=7497, client_id=9):
        EClient.__init__(self, self)
        self.port = port
        self.client_id = client_id

    def ib_connect(self):
        self.connect('127.0.0.1', self.port, clientId=self.client_id)
        thread = Thread(target=self.run)
        thread.start()


ibkr = IBKRClient(port=7497, client_id=9)
ibkr.ib_connect()  # Connect to TWS paper trading on a separate thread

@app.route('/webhook', methods=['POST'])
def webhook():
    data = json.loads(request.data)
    ticker = data['ticker']
    action = data['action']
    if action == 'buy':
        ibkr.placeOrder(1, create_contract(ticker), create_order("MKT", "BUY", 100))
    elif action == 'sell':
        ibkr.placeOrder(2, create_contract(ticker), create_order("MKT", "SELL", 100))
    return "Order Executed", 200

if __name__ == '__main__':
    app.run(debug=True)
