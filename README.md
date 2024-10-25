
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

## MicroFamily

| **Symbol** | **Contract**                      | **Tick Size**   | **Tick Value** | **Approximate Initial Margin** |
|------------|-----------------------------------|-----------------|----------------|---------------------------------|
| **MES**    | Micro E-mini S&P 500              | 0.25 points     | $1.25          | $1,200 - $1,500                |
| **MNQ**    | Micro E-mini Nasdaq-100           | 0.25 points     | $0.50          | $1,500 - $2,000                |
| **MGC**    | Micro Gold                        | 0.10 points     | $1.00          | $1,000 - $1,200                |
| **MCL**    | Micro Crude Oil                   | 0.01 points     | $1.00          | $1,000 - $1,200                |
| **MBT**    | Micro Bitcoin                     | 5 points        | $0.50          | $2,000 - $2,500                |
| **MYM**    | Micro E-mini Dow                  | 1 point         | $0.50          | $700 - $1,000                  |
| **M2K**    | Micro E-mini Russell 2000         | 0.10 points     | $0.50          | $600 - $900                    |

These values give you a general idea, but for exact and up-to-date figures, it's best to check with your broker, as margins may vary based on volatility and risk settings.

## PORT assign

account_summary: 10
order_manager: [1000, 1999]

data_realtime: 20
data_historical: 21 

strategy_manager: 50-70
tradingview: [8000, 8999]

tests: [9000, 9999]

TradingView Format:
```
{
  "ticker": "{{ticker}}",
  "contract": "FUT",
  "exchange": "{{exchange}}"
  "order": "LMT",
  "action": "BUY",
  "price": "90",
  "quantity": "1",
  "reason": "Open-Long"
}
```

## Installation

install the dependencies using pip:
```
pip install -r requirements.txt
```
