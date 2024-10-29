from abc import ABC, abstractmethod
from typing import List
from .SignalProcessor import TradingSignal

class BaseStrategy(ABC):
    def __init__(self):
        self.symbols = set()

    @abstractmethod
    def generate_signals(self) -> List[TradingSignal]:
        """Generate trading signals for the strategy"""
        pass

    def get_symbols(self) -> set:
        """Return set of symbols used by this strategy"""
        return self.symbols 