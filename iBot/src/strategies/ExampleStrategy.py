from .BaseStrategy import BaseStrategy
from .SignalProcessor import TradingSignal, SignalType
from typing import List

class SimpleMovingAverageStrategy(BaseStrategy):
    def __init__(self, symbols: list, fast_period: int = 10, slow_period: int = 20):
        super().__init__()
        self.symbols = set(symbols)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.prices = {symbol: [] for symbol in symbols}

    def update_price(self, symbol: str, price: float):
        """Update price data for a symbol"""
        if symbol in self.prices:
            self.prices[symbol].append(price)
            # Keep only needed history
            max_length = max(self.fast_period, self.slow_period)
            self.prices[symbol] = self.prices[symbol][-max_length:]

    def generate_signals(self) -> List[TradingSignal]:
        """Generate trading signals based on moving average crossover"""
        signals = []
        
        for symbol in self.symbols:
            prices = self.prices[symbol]
            
            if len(prices) < self.slow_period:
                continue
                
            # Calculate moving averages
            fast_ma = sum(prices[-self.fast_period:]) / self.fast_period
            slow_ma = sum(prices[-self.slow_period:]) / self.slow_period
            current_price = prices[-1]
            
            # Generate signals based on MA crossover
            if fast_ma > slow_ma:
                signals.append(TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=current_price,
                    reason="Fast MA crossed above Slow MA"
                ))
            elif fast_ma < slow_ma:
                signals.append(TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=current_price,
                    reason="Fast MA crossed below Slow MA"
                ))
                
                
        return signals 