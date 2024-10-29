from ibapi.contract import Contract
from ibapi.order import Order
from enum import Enum
import time
from typing import Dict, Optional

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"
    HOLD = "HOLD"

class TradingSignal:
    def __init__(self, symbol: str, signal_type: SignalType, price: float, 
                 target_position: float = None, reason: str = ""):
        self.symbol = symbol
        self.signal_type = signal_type
        self.price = price
        self.target_position = target_position
        self.reason = reason
        self.timestamp = time.time()

class SignalProcessor:
    def __init__(self, order_manager, max_position_size: int = 1):
        self.order_manager = order_manager
        self.max_position_size = max_position_size
        self.strategies = []
        self.active_symbols = set()

    def add_strategy(self, strategy):
        """Add a trading strategy to the processor"""
        self.strategies.append(strategy)
        # Add symbols from strategy to active symbols
        self.active_symbols.update(strategy.get_symbols())

    def process_signals(self):
        """Process signals from all strategies and generate orders"""
        all_signals = []
        
        # Collect signals from all strategies
        for strategy in self.strategies:
            signals = strategy.generate_signals()
            if signals:
                all_signals.extend(signals)

        # Process each signal
        for signal in all_signals:
            self._handle_signal(signal)

    def _handle_signal(self, signal: TradingSignal):
        """Handle individual trading signals"""
        # Get current position
        current_position = self.order_manager.get_position_for_symbol(signal.symbol)
        position_size = current_position['position'] if current_position else 0

        # Calculate order quantity based on signal and current position
        order_quantity = self._calculate_order_quantity(signal, position_size)
        
        if order_quantity == 0:
            return

        # Create and place order
        self._place_order(signal, order_quantity)

    def _calculate_order_quantity(self, signal: TradingSignal, current_position: float) -> int:
        """Calculate the order quantity based on signal and current position"""
        if signal.signal_type == SignalType.CLOSE:
            return -current_position  # Close entire position
        
        if signal.target_position is not None:
            # If target position is specified, calculate difference
            return int(signal.target_position - current_position)
        
        if signal.signal_type == SignalType.BUY:
            # Don't exceed max position size
            return min(self.max_position_size - current_position, 1)
        
        if signal.signal_type == SignalType.SELL:
            # Don't exceed max short position size
            return max(-self.max_position_size - current_position, -1)
        
        return 0

    def _place_order(self, signal: TradingSignal, quantity: int):
        """Place order based on signal and calculated quantity"""
        if quantity == 0:
            return

        action = "BUY" if quantity > 0 else "SELL"
        abs_quantity = abs(quantity)

        # Create contract
        contract = self._create_contract(signal.symbol)
        
        # Create order
        order = Order()
        order.action = action
        order.totalQuantity = abs_quantity
        order.orderType = "LMT"
        order.lmtPrice = signal.price
        
        # Send order
        self.order_manager.placeOrder(contract, order)

    def _create_contract(self, symbol: str) -> Contract:
        """Create contract object for the symbol"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "FUT"  # Adjust based on your needs
        contract.exchange = "CME"  # Adjust based on your needs
        contract.currency = "USD"
        return contract 