from ibapi.order import Order

tick_size = {
    "MES": 0.25,
    "MGC": 0.10,
    "MNQ": 0.25,
    "MBT": 1  # 5 index point
}

"""
Initializes order types
"""
def create_limit_order(action, totalQuantity, lmtPrice, eTradeOnly=False, firmQuoteOnly=False):
    order = Order()
    order.action = action
    order.totalQuantity = totalQuantity
    order.orderType = "LMT"
    order.lmtPrice = lmtPrice
    # Explicitly set eTradeOnly and firmQuoteOnly
    order.eTradeOnly = eTradeOnly
    order.firmQuoteOnly = firmQuoteOnly
    print(f"[LMT Order] created with action: {order.action}, "
          f"totalQuantity: {order.totalQuantity}, "
          f"orderType: {order.orderType}, "
          f"lmtPrice: {order.lmtPrice}")
    return order

def create_market_order(action, totalQuantity, eTradeOnly=False, firmQuoteOnly=False):
    order = Order()
    order.action = action
    order.totalQuantity = totalQuantity
    order.orderType = "MKT"
    # Explicitly set eTradeOnly and firmQuoteOnly
    order.eTradeOnly = eTradeOnly
    order.firmQuoteOnly = firmQuoteOnly
    print(f"[MKT Order] created with action: {order.action}, "
          f"totalQuantity: {order.totalQuantity}, "
          f"orderType: {order.orderType}")
    return order

def create_order(symbol, order_type, action, totalQuantity, price=0):
    if action.upper() == "BUY":
        signal = 1
    elif action.upper() == "SELL":
        signal = -1
    else:
        raise Exception(f"Invalid order type {action}, should be BUY or SELL")

    if order_type == "MKT":
        return create_market_order(action, totalQuantity)
    elif order_type == "LMT":
        tick = 1
        if symbol.startswith("MES"):
            tick = tick_size["MES"]
        elif symbol.startswith("MNQ"):
            tick = tick_size["MNQ"]
        elif symbol.startswith("MBT"):
            tick = tick_size["MBT"]
        elif symbol.startswith("MGC"):
            tick = tick_size["MGC"]
        else:
            print("New symbol and tick size not supported.")
        price = round(price / tick + signal) * tick
        return create_limit_order(action, totalQuantity, price)
    else:
        raise ValueError(f"Invalid order type: {order_type}")

