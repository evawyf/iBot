from ibapi.contract import Contract 
import datetime
"""
Initializes contract
"""

def create_contract(symbol, contract_type):
    if contract_type == "FUT":
        return create_futures_contract(symbol)
    elif contract_type == "STK":
        return create_stock_contract(symbol)
    elif contract_type == "OPT":
        return create_option_contract(symbol)
    else:
        raise ValueError(f"Invalid contract type: {contract_type}")

def create_futures_contract(symbol, exchange="CME", currency="USD", lastTradeDateOrContractMonth=None):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "FUT"
    contract.exchange = exchange
    contract.currency = currency
    
    if lastTradeDateOrContractMonth is None:
        lastTradeDateOrContractMonth = expiry_check()
    
    contract.lastTradeDateOrContractMonth = lastTradeDateOrContractMonth
    
    print(f"[FUT Contract] created with symbol: {contract.symbol}, "
          f"exchange: {contract.exchange}, currency: {contract.currency}, "
          f"lastTradeDateOrContractMonth: {contract.lastTradeDateOrContractMonth}")
    
    return contract

def expiry_check():
    current_date = datetime.datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    contract_months = [3, 6, 9, 12]
    next_contract_month = min(month for month in contract_months if month > current_month) if current_month < 12 else 3
    next_contract_year = current_year if next_contract_month > current_month else current_year + 1
    return f"{next_contract_year}{next_contract_month:02d}"


def create_stock_contract(symbol, exchange="SMART", currency="USD"):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = exchange
    contract.currency = currency
    
    print(f"[STK Contract] created with symbol: {contract.symbol}, "
          f"exchange: {contract.exchange}, currency: {contract.currency}")
    
    return contract


# TODO: confirm default exchange and other parameters
def create_option_contract(symbol, exchange="SMART", currency="USD", 
                           lastTradeDateOrContractMonth=None, strike=None, right=None):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "OPT"
    contract.exchange = exchange
    contract.currency = currency
    contract.lastTradeDateOrContractMonth = lastTradeDateOrContractMonth
    contract.strike = strike
    contract.right = right
    
    print(f"ContractOPT created with symbol: {contract.symbol}, "
          f"exchange: {contract.exchange}, currency: {contract.currency}, "
          f"lastTradeDateOrContractMonth: {contract.lastTradeDateOrContractMonth}, "
          f"strike: {contract.strike}, right: {contract.right}")
    
    return contract
