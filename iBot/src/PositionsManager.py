from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from iBot.src.utils.sample_ib_contract import create_contract
from ibapi.common import *
from datetime import datetime
import threading
import random
import redis

#TODO 
class StrategyPositionsManager(EWrapper, EClient):
    def __init__(self, port, max_wait_time=30):
        EClient.__init__(self, self)
        self.port = port
        self.client_id = random.randint(1000, 1999)
        self.positions = {}
        self.strategy_positions = {}
        self.lock = threading.Lock()
        self.position_event = threading.Event()
        self.connection_event = threading.Event()
        self.max_wait_time = max_wait_time
        self.task_name = "StrategyPositionsManager"
        self.order_strategy_map = {}  # Maps order IDs to strategy names
        
        # Initialize Redis connection
        try:
            self.redis = redis.Redis(host='localhost', port=6379, db=0)
            self.redis.ping()
        except redis.ConnectionError:
            print("Error: Could not connect to Redis. Please ensure Redis server is running.")
            raise

    def ib_connect(self):
        try:
            self.connect('127.0.0.1', self.port, self.client_id)
        except Exception as e:
            print(f"Error connecting: {e}")
            return False

        api_thread = threading.Thread(target=self.run, daemon=True)
        api_thread.start()

        if not self.connection_event.wait(timeout=self.max_wait_time):
            print("Timeout waiting for connection. Please check your connection.")
            self.disconnect()
            return False

        print("Connection established.")
        return True

    def ib_disconnect(self):
        print(f"Disconnecting client task [{self.task_name}] ...")
        self.disconnect()
        print(f"Client disconnected.")

    def register_order(self, order_id: int, strategy_name: str):
        """Register an order ID with a strategy name"""
        with self.lock:
            self.order_strategy_map[order_id] = strategy_name

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        """Called when order status changes"""
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        
        if status in ["Filled", "PartiallyFilled"]:
            strategy_name = self.order_strategy_map.get(orderId)
            if strategy_name:
                self.update_strategy_position_from_order(strategy_name, orderId, filled, avgFillPrice)

    def update_strategy_position_from_order(self, strategy_name: str, order_id: int, filled: float, avg_price: float):
        """Update strategy position when an order is filled"""
        with self.lock:
            contract = self.openContracts.get(order_id)
            if not contract:
                return
                
            key = f"{strategy_name}:{contract.symbol}_{contract.secType}"
            current_position = self.strategy_positions.get(key, {'position': 0, 'avgCost': 0})
            
            # Update position and average cost
            new_position = current_position['position'] + filled
            if new_position != 0:
                new_avg_cost = ((current_position['position'] * current_position['avgCost']) + 
                              (filled * avg_price)) / new_position
            else:
                new_avg_cost = 0

            self.strategy_positions[key] = {
                'position': new_position,
                'avgCost': new_avg_cost,
                'lastUpdate': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Store in Redis
            self.redis.hset(f"strategy_position:{key}", mapping={
                'position': str(new_position),
                'avgCost': str(new_avg_cost),
                'lastUpdate': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    def get_strategy_position(self, strategy_name: str, symbol: str, contract_type: str) -> dict:
        """Get position details for a specific strategy and instrument"""
        with self.lock:
            strategy_key = f"{strategy_name}:{symbol}_{contract_type}"
            return self.strategy_positions.get(strategy_key)

    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Callback for overall account position updates"""
        super().position(account, contract, position, avgCost)
        with self.lock:
            key = f"{contract.symbol}_{contract.secType}"
            self.positions[key] = {
                'position': position,
                'avgCost': avgCost,
                'account': account
            }
            self.position_event.set()


if __name__ == "__main__":
    app = StrategyPositionsManager(port=7497)
    if app.ib_connect():

        contract = create_contract("MES", "FUT")
        app.register_order(1, "test strategy")
        app.update_strategy_position_from_order("test strategy", 1, 1, 100)
        print(app.get_strategy_position("test strategy", "MES", "FUT"))

    app.ib_disconnect()
