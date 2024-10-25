# iBot

iBot is a trading bot that uses the Interactive Brokers API to automate trading strategies.

## Requirements

- Python 3.6+
- Interactive Brokers account
- Interactive Brokers Trader Workstation (TWS) or IB Gateway

### Python Dependencies

- ibapi>=9.81.1,<10.0
- pandas>=1.0.0
- numpy>=1.18.0
- (Add any other dependencies your project uses)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/iBot.git
   cd iBot
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

4. Install the project in editable mode:
   ```
   pip install -e .
   ```

## Debug

```
lsof -i :$PORT   
```


## Configuration

1. Ensure that Interactive Brokers Trader Workstation (TWS) or IB Gateway is running.

2. Open `src/config.py` and adjust the settings as needed:
   ```python
   TWS_HOST = '127.0.0.1'  # TWS/Gateway host
   TWS_PORT = 7497         # TWS/Gateway port (7497 for paper trading, 7496 for live)
   CLIENT_ID = 1           # Unique client ID
   ```

## Usage

Run the main script:
```
python scr/main.py
```

Or use the console script:
```
ibot
```

## Development

To install development dependencies:

```
pip install -e .[dev]
```

This will install additional packages like pytest and flake8 for testing and linting.

To run tests:

```
pytest
```

To check code style:
```
flake8 src tests
```

## Project Structure

```
iBot/
│
├── src/
│ ├── init.py
│ ├── main.py
│ ├── config.py
│ ├── utils/
│ │ ├── init.py
│ │ ├── path_helper.py
│ │ └── client_manager.py
│ ├── data/
│ │ ├── init.py
│ │ ├── realtime_data.py
│ │ └── historical_data.py
│ ├── order/
│ │ ├── init.py
│ │ └── order_manager.py
│ └── strategies/
│ ├── init.py
│ └── example_strategy.py
│
├── tests/
│ ├── init.py
│ ├── test_client_manager.py
│ └── test_order_manager.py
│
├── docs/
│ └── README.md
│
├── requirements.txt
├── setup.py
├── .gitignore
└── README.md
```


## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Disclaimer

This software is for educational purposes only. Do not risk money which you are afraid to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS.
