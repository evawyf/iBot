import sys
import os
from typing import Tuple, Union

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from utils.ib_contract import create_contract
# from utils.ib_order import create_order

def reverse_position_quantity_adjustment_helper(
    current_position: float,
    action: str,
    quantity: float,
    reason: str
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
    # if not isinstance(reverse_position_potential, bool):
    #     raise ValueError("reverse_position_potential must be a boolean")

    reverse_position_potential = reason.lower().startswith('open')
    opposite_position = (current_position >= 0 and action == "SELL") or (current_position <= 0 and action == "BUY")

    if reverse_position_potential and opposite_position: 
        adjusted_quantity = quantity - current_position
    else:
        # Not reversing position, same direction position, just simply add quantity
        adjusted_quantity = quantity 

    return adjusted_quantity, 200

if __name__ == "__main__":
    print(reverse_position_quantity_adjustment_helper(5, "MGC", "FUT", "COMEX", "LMT", "BUY", 150, 3, 'open-long'))