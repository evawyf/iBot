from ibapi.contract import Contract 

import calendar
from datetime import date, datetime, timedelta

"""
Initializes contract
"""

def get_default_exchange(symbol):
    """
    Maps symbols to their most popular exchanges.
    """
    exchange_map = {
        # US Stocks
        "AAPL": "NASDAQ",
        "MSFT": "NASDAQ",
        "GOOGL": "NASDAQ",
        "AMZN": "NASDAQ",
        "FB": "NASDAQ",
        "TSLA": "NASDAQ",
        "JPM": "NYSE",
        "JNJ": "NYSE",
        "V": "NYSE",
        "PG": "NYSE",
        
        # US Futures
        "ES": "CME",
        "MES": "CME",
        "NQ": "CME",
        "MNQ": "CME",
        "MBT": "CME",
        "CL": "NYMEX",
        "GC": "COMEX",
        "MGC": "COMEX",
        "SI": "COMEX",
        "ZB": "CBOT",
        "ZN": "CBOT",
        "ZC": "CBOT",
        "ZS": "CBOT",
        "6E": "CME",
        
        # Non-US Stocks
        "BABA": "NYSE",  # Alibaba (China)
        "TSM": "NYSE",   # Taiwan Semiconductor
        "ASML": "NASDAQ",  # ASML Holding (Netherlands)
        "SAP": "NYSE",   # SAP SE (Germany)
        
        # Cryptocurrencies
        "BTCUSD": "COINBASE",
        "ETHUSD": "COINBASE"
    }
    
    return exchange_map.get(symbol, "SMART")  # Default to SMART if not found


def create_contract(symbol, contract_type, exchange=None):
    if contract_type == "FUT":
        symbol = symbol[:-2] if symbol[-1] == '!' and symbol[-2].isdigit() else symbol
    if exchange is None:
        exchange = get_default_exchange(symbol)

    if contract_type == "FUT":
        return create_futures_contract(symbol, exchange)
    elif contract_type == "STK":
        return create_stock_contract(symbol, exchange)
    elif contract_type == "OPT":
        return create_option_contract(symbol, exchange)
    else:
        raise ValueError(f"Invalid contract type: {contract_type}")

def create_futures_contract(symbol, exchange="CME", currency="USD", lastTradeDateOrContractMonth=None):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "FUT"
    contract.exchange = exchange
    contract.currency = currency
    
    if lastTradeDateOrContractMonth is None:
        lastTradeDateOrContractMonth = get_roll_date_lastTradeDateOrContractMonth()
    
    contract.lastTradeDateOrContractMonth = lastTradeDateOrContractMonth
    
    print(f"[FUT Contract] created with symbol: {contract.symbol}, "
          f"exchange: {contract.exchange}, currency: {contract.currency}, "
          f"lastTradeDateOrContractMonth: {contract.lastTradeDateOrContractMonth}")
    
    return contract

def create_stock_contract(symbol, exchange="SMART", currency="USD"):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = exchange
    contract.currency = currency
    
    print(f"[STK Contract] created with symbol: {contract.symbol}, "
          f"exchange: {contract.exchange}, currency: {contract.currency}")
    
    return contract

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
    
    print(f"[OPT Contract] created with symbol: {contract.symbol}, "
          f"exchange: {contract.exchange}, currency: {contract.currency}, "
          f"lastTradeDateOrContractMonth: {contract.lastTradeDateOrContractMonth}, "
          f"strike: {contract.strike}, right: {contract.right}")
    
    return contract


"""
Future contract roll expiry
"""
def get_roll_expiry(year):
    # Quarterly expiration months for MES: March (3), June (6), September (9), December (12)
    months = [3, 6, 9, 12]
    contract_info = {}

    for month in months:
        # Get the first day of the month
        first_day_of_month = date(year, month, 1)
        
        # Find the third Friday (contract expiry)
        third_friday = [day for day in range(15, 22) if calendar.weekday(year, month, day) == calendar.FRIDAY][0]
        expiry_date = date(year, month, third_friday)
        
        # Find the second Thursday (roll date)
        second_thursday = [day for day in range(8, 15) if calendar.weekday(year, month, day) == calendar.THURSDAY][0]
        roll_date = date(year, month, second_thursday)
        
        contract_info[f'{year} {calendar.month_name[month]}'] = {
            'roll_date': roll_date,
            'expiry_date': expiry_date
        }
    
    return contract_info

def get_roll_date_lastTradeDateOrContractMonth():
    current_date = datetime.now().date()
    current_year = current_date.year
    contracts = get_roll_expiry(current_year)
    
    # Check if we need to look at next year's contracts
    if current_date > max(contract['roll_date'] for contract in contracts.values()):
        contracts.update(get_roll_expiry(current_year + 1))
    
    for contract, dates in sorted(contracts.items()):
        if current_date <= dates['roll_date']:
            return dates['expiry_date'].strftime("%Y%m")
    
    # If we've passed all roll dates, return the first contract of next year
    next_year_contracts = get_roll_expiry(current_year + 1)
    return next(iter(next_year_contracts.values()))['expiry_date'].strftime("%Y%m")


if __name__ == "__main__":

    # Example usage for 2024
    contracts_2024 = get_roll_expiry(2024)
    for contract, dates in contracts_2024.items():
        print(f"Contract: {contract}, Roll Date: {dates['roll_date']}, Expiry Date: {dates['expiry_date']}")
    
    # Example usage of get_roll_date_lastTradeDateOrContractMonth
    print(f"\nCurrent date: {datetime.now().date()}")
    print(f"lastTradeDateOrContractMonth: {get_roll_date_lastTradeDateOrContractMonth()}")



