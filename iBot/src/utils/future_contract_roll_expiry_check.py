
import calendar
from datetime import date, datetime, timedelta

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
    
    # Example usage of get_lastTradeDateOrContractMonth
    print(f"\nCurrent date: {datetime.now().date()}")
    print(f"lastTradeDateOrContractMonth: {get_roll_date_lastTradeDateOrContractMonth()}")

