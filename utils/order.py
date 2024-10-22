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
    print(f"OrderLMT created with action: {order.action}, "
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
    print(f"OrderMKT created with action: {order.action}, "
          f"totalQuantity: {order.totalQuantity}, "
          f"orderType: {order.orderType}")
    return order


