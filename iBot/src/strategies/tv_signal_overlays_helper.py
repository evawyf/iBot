import sys
import os
from typing import Tuple, Union

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ib_contract import create_contract
from utils.ib_order import create_order

def signal_overlay_strategy_quantity_adjustment(
    current_position: float,
    symbol: str,
    contract_type: str,
    exchange: str,
    order_type: str,
    action: str,
    price: float,
    quantity: float,
    default_quantity: float,
    reverse_position_potential: bool = False
) -> Tuple[Union[object, str], Union[object, str], float]:
    """
    Signal Overlay Strategy for creating contracts and orders based on given parameters.

    Args:
        current_position (float): Current position.
        symbol (str): Trading symbol.
        contract_type (str): Type of contract.
        exchange (str): Exchange name.
        order_type (str): Type of order.
        action (str): Action to take ('BUY' or 'SELL').
        price (float): Price for the order.
        quantity (float): Quantity to trade.
        default_quantity (float): Default quantity to trade. If no quantity is provided or open-long/open-short, use this default quantity.
        reverse_position_potential (bool, optional): Whether to potentially reverse the position. Defaults to False.

    Returns:
        Tuple[Union[object, str], Union[object, str], float]: A tuple containing the contract object,
        order object, and adjusted quantity, or error messages if creation fails.

    Raises:
        ValueError: If input parameters are invalid.
    """
    if not isinstance(current_position, (int, float)):
        raise ValueError("current_position must be a number")
    if action not in ["BUY", "SELL"]:
        raise ValueError("action must be either 'BUY' or 'SELL'")
    if not isinstance(quantity, (int, float)) or quantity <= 0:
        raise ValueError("quantity must be a positive number")
    if not isinstance(reverse_position_potential, bool):
        raise ValueError("reverse_position_potential must be a boolean")

    if reverse_position_potential: # open-long/open-short situation
        if (current_position > 0 and action == "SELL") or (current_position < 0 and action == "BUY"): # Reverse position situation
            adjusted_quantity = default_quantity + abs(current_position)
        else:
            adjusted_quantity = quantity # Not reversing position, same direction position, just simply add quantity
    else: # close-long/close-short situation
        adjusted_quantity = min(quantity, abs(current_position))

    try:
        contract = create_contract(symbol=symbol, contract_type=contract_type, exchange=exchange)
    except Exception as e:
        return f"Contract creation failed: {str(e)}", 400, 0

    try:
        order = create_order(order_type=order_type, action=action, totalQuantity=adjusted_quantity, price=price)
    except Exception as e:
        return f"Order creation failed: {str(e)}", 400, 0

    return contract, order, adjusted_quantity

if __name__ == "__main__":
    print(signal_overlay_strategy_quantity_adjustment(5, "MGC", "FUT", "COMEX", "LMT", "BUY", 150, 3, reverse_position_potential=True))