import sys
import os
from typing import Tuple, Union
from utils.ib_contract import create_contract
from utils.ib_order import create_order

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def signal_overlay_strategy(
    init_position: float,
    symbol: str,
    contract_type: str,
    exchange: str,
    order_type: str,
    action: str,
    price: float,
    quantity: float,
    reverse_position: bool = False
) -> Tuple[Union[object, str], Union[object, str]]:
    """
    Signal Overlay Strategy for creating contracts and orders based on given parameters.

    Args:
        init_position (float): Initial position.
        symbol (str): Trading symbol.
        contract_type (str): Type of contract.
        exchange (str): Exchange name.
        order_type (str): Type of order.
        action (str): Action to take ('BUY' or 'SELL').
        price (float): Price for the order.
        quantity (float): Quantity to trade.
        reverse_position (bool, optional): Whether to reverse the position. Defaults to False.

    Returns:
        Tuple[Union[object, str], Union[object, str]]: A tuple containing the contract and order objects,
        or error messages if creation fails.

    Raises:
        ValueError: If input parameters are invalid.
    """
    if not isinstance(init_position, (int, float)):
        raise ValueError("init_position must be a number")
    if action not in ["BUY", "SELL"]:
        raise ValueError("action must be either 'BUY' or 'SELL'")
    if not isinstance(quantity, (int, float)) or quantity <= 0:
        raise ValueError("quantity must be a positive number")
    if not isinstance(reverse_position, bool):
        raise ValueError("reverse_position must be a boolean")

    if reverse_position:
        if (init_position > 0 and action == "SELL") or (init_position < 0 and action == "BUY"):
            adjustment_quantity = quantity + abs(init_position)
        else:
            raise ValueError("Reverse position is not allowed in this situation")
    else:
        adjustment_quantity = min(quantity, abs(init_position))

    try:
        contract = create_contract(symbol=symbol, contract_type=contract_type, exchange=exchange)
    except Exception as e:
        return f"Contract creation failed: {str(e)}", 400

    try:
        order = create_order(order_type=order_type, action=action, totalQuantity=adjustment_quantity, price=price)
    except Exception as e:
        return f"Order creation failed: {str(e)}", 400

    return contract, order
