from ibapi.order import Order
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
    print(f"[MKT Order]created with action: {order.action}, "
          f"totalQuantity: {order.totalQuantity}, "
          f"orderType: {order.orderType}")
    return order

def create_order(order_type, action, totalQuantity, price=0):
    if order_type == "MKT":
        return create_market_order(action, totalQuantity)
    elif order_type == "LMT":
        return create_limit_order(action, totalQuantity, price)
    else:
        raise ValueError(f"Invalid order type: {order_type}")

