import threading, time, sys, os

# Add the parent directory to the Python path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..IBRealtimeDataBarGenerator import IBRealtimeDataBarGenerator
from utils.contract import create_contract


def conn_ib_realtime_data_generator(port, client_id, symbol, contract_type, bar_frequency_seconds=60):

    app = IBRealtimeDataBarGenerator(symbol, contract_type, bar_frequency_seconds=60)  # 1-minute bars
    
    print("Attempting to connect to TWS...")
    app.connect("127.0.0.1", port, client_id)

    contract = create_contract(symbol, contract_type)

    # Start the socket in a thread
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()

    # Wait for connection
    time.sleep(1)  # Give it a second to connect

    if not app.isConnected():
        print("Failed to connect to TWS. Make sure it's running and allows API connections.")
        return

    print("Connected to TWS.")

    # Request market data
    print("Requesting market data for MES...")
    app.reqMktData(1, contract, "", False, False, [])

    print(f"Fetching realtime data for MES and generating {app.bar_frequency_str} bars. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping data fetch...")
    finally:
        app.cancelMktData(1)
        app.disconnect()
        print("Disconnected from TWS.")
        

if __name__ == "__main__":

    PORT = 7497
    CLIENT_ID = 0
    SYMBOL = "MES"
    CONTRACT_TYPE = "FUT"

    conn_ib_realtime_data_generator(PORT, CLIENT_ID, SYMBOL, CONTRACT_TYPE)
