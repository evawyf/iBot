
# TODO: Too confuse for all cases 
def adjust_order_quantity(ticker, action, reason, desired_final_position, position_counts, init_quantity):
    """
    This method adjusts the order quantity based on the current position and the desired action.
    
    It does the following:
    1. Initializes the order count for a ticker if it doesn't exist.
    2. Sets a default quantity if none is provided.
    3. Calculates the adjusted quantity based on the action and reason:
        - For opening positions (BUY/SELL with 'Open-'), it aims to reach the desired quantity.
        - For closing positions (BUY/SELL with 'Close-'), it aims to close the entire position.
    4. Updates the order count for the ticker.
    5. Returns the adjusted quantity for the new order.

    The method ensures that the final position after the order matches the desired state:
    - For opening orders, it reaches the desired quantity.
    - For closing orders, it brings the position to zero.

    This approach allows for position tracking and prevents over-buying or over-selling.
    """

    if ticker not in position_counts:
        position_counts[ticker] = 0

    if not desired_final_position:
        desired_final_position = init_quantity 


    if action.upper() == 'BUY' and reason == 'Open-Long':
        
        if desired_final_position < position_counts[ticker]:
            raise ValueError(f"[No action needed] Desired quantity: {desired_final_position} is less than current position: {position_counts[ticker]} for action: {action}, reason: {reason}")
        desired_final_position = abs(desired_final_position)
        adj_quantity = desired_final_position - position_counts[ticker]
        if adj_quantity <= 0:
            raise ValueError(f"Invalid desired quantity: {desired_final_position}, or current position: {position_counts[ticker]} for action: {action}, reason: {reason}")
        
    elif action.upper() == 'BUY' and reason == 'Close-Short':
        if desired_final_position > position_counts[ticker]:
            raise ValueError(f"[No action needed] Desired quantity: {desired_final_position} is greater than current position: {position_counts[ticker]} for action: {action}, reason: {reason}")   
        desired_final_position = 0
        if position_counts[ticker] >= 0:
            adj_quantity = 0
        else:
            adj_quantity = abs(position_counts[ticker])

    elif action.upper() == 'SELL' and reason == 'Open-Short':
        desired_final_position = -abs(desired_final_position)
        adj_quantity = position_counts[ticker] - desired_final_position
        if adj_quantity < 0:
            adj_quantity = 0

    elif action.upper() == 'SELL' and reason == 'Close-Long':
        desired_final_position = 0
        if position_counts[ticker] <= 0:
            adj_quantity = 0
        else:
            adj_quantity = position_counts[ticker]

    else:
        raise ValueError(f"Invalid action: {action} or reason: {reason}, no quantity adjustment made")

    signal = 1 if action.upper() == 'BUY' else -1 
    position_counts[ticker] += signal * adj_quantity
    
    return adj_quantity

if __name__ == "__main__":

    def test_adjust_order_quantity():
        position_counts = {}
        init_quantity = 10

        # Test case 1: BUY Open-Long
        position_counts['AAPL'] = 0
        assert adjust_order_quantity('AAPL', 'BUY', 'Open-Long', 5, position_counts, init_quantity) == 5
        assert position_counts['AAPL'] == 5

        position_counts['AAPL'] = 3
        assert adjust_order_quantity('AAPL', 'BUY', 'Open-Long', 5, position_counts, init_quantity) == 2
        assert position_counts['AAPL'] == 5

        position_counts['AAPL'] = 10
        # assert adjust_order_quantity('AAPL', 'BUY', 'Open-Long', 5, position_counts, init_quantity) == 0
        with pytest.raises(ValueError):
            adjust_order_quantity('AAPL', 'BUY', 'Open-Long', 5, position_counts, init_quantity)
        assert position_counts['AAPL'] == 10  # Ensure position hasn't changed

        position_counts['AAPL'] = -20
        assert adjust_order_quantity('AAPL', 'BUY', 'Open-Long', 5, position_counts, init_quantity) == 25
        assert position_counts['AAPL'] == 5

        # Test case 2: SELL Close-Long
        position_counts['AAPL'] = 5
        assert adjust_order_quantity('AAPL', 'SELL', 'Close-Long', 0, position_counts, init_quantity) == 5
        assert position_counts['AAPL'] == 0

        position_counts['AAPL'] = 0
        assert adjust_order_quantity('AAPL', 'SELL', 'Close-Long', 0, position_counts, init_quantity) == 0
        assert position_counts['AAPL'] == 0

        position_counts['AAPL'] = -3
        with pytest.raises(ValueError, match="Cannot close long position, no long position exists"):
            adjust_order_quantity('AAPL', 'SELL', 'Close-Long', 0, position_counts, init_quantity)
        assert position_counts['AAPL'] == -3  # Ensure position hasn't changed

        # Test case 3: SELL Open-Short
        position_counts['AAPL'] = 0
        assert adjust_order_quantity('AAPL', 'SELL', 'Open-Short', 3, position_counts, init_quantity) == 3
        assert position_counts['AAPL'] == -3

        position_counts['AAPL'] = 4
        assert adjust_order_quantity('AAPL', 'SELL', 'Open-Short', 3, position_counts, init_quantity) == 7
        assert position_counts['AAPL'] == -3   

        position_counts['AAPL'] = -1
        assert adjust_order_quantity('AAPL', 'SELL', 'Open-Short', 3, position_counts, init_quantity) == 2
        assert position_counts['AAPL'] == -3

        position_counts['AAPL'] = -5
        assert adjust_order_quantity('AAPL', 'SELL', 'Open-Short', 3, position_counts, init_quantity) == 0
        assert position_counts['AAPL'] == -5

        # Test case 4: BUY Close-Short
        position_counts['AAPL'] = -3
        assert adjust_order_quantity('AAPL', 'BUY', 'Close-Short', 0, position_counts, init_quantity) == 3
        assert position_counts['AAPL'] == 0

        position_counts['AAPL'] = 0
        assert adjust_order_quantity('AAPL', 'BUY', 'Close-Short', 0, position_counts, init_quantity) == 0
        assert position_counts['AAPL'] == 0

        position_counts['AAPL'] = 5
        with pytest.raises(ValueError, match="Cannot close short position, no short position exists"):
            adjust_order_quantity('AAPL', 'BUY', 'Close-Short', 0, position_counts, init_quantity)
        assert position_counts['AAPL'] == 5  # Ensure position hasn't changed

        # Test case 5: Invalid action
        position_counts['AAPL'] = 0
        try:
            adjust_order_quantity('AAPL', 'HOLD', 'Open-Long', 5, position_counts, init_quantity)
        except ValueError as e:
            assert str(e) == "Invalid action: HOLD or reason: Open-Long, no quantity adjustment made"

        print("All test cases passed!")

    test_adjust_order_quantity()



