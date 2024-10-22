
# iBot

## DONE 

1. order_manager: send, fut/stk, lmt/mkt, cancel one, cancel all
2. client_id, threads
3. data_manager: real-time data generate bar

## TODO list

1. data_manager: historical data (run daily), tick data (real-time)
2. indicators
3. strategies
4. order_manager -> database as record (order id, symbol, action, price, quantity, order_type) etc 


## PORT assign

account_summary: 10
order_manager: 11

data_realtime: 20
data_historical: 21 

strategy_manager: 50-70


## Installation

install the dependencies using pip:
```
pip install -r requirements.txt
```
