import sys
import os
import threading
import time

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ..IBOrderManager import IBOrderManager


# TODO: check if max_wait_time is needed, and the app.nextOrderId function
def conn_ib_order_manager(port, client_id, max_wait_time=10):

    app = IBOrderManager()
    # Try to connect
    try:
        app.connect('127.0.0.1', port, client_id)
    except Exception as e:
        print(f"Error connecting: {e}")
        return None

    # Start the socket in a thread
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()

    # Wait for nextValidId with a timeout
    start_time = time.time()
    while app.nextOrderId is None and time.time() - start_time < max_wait_time:
        time.sleep(0.1)

    if app.nextOrderId is None:
        print("Timeout waiting for nextValidId. Please check your connection.")
        app.disconnect()
        return None

    print(f"Received nextValidId: {app.nextOrderId}")
    print("Connection established.")

    return app
    

# Usage example:
if __name__ == "__main__":

    PORT = 7497
    PRICE = 200

    app = conn_ib_order_manager(PORT, 1)

    # Your IB tasks go here
    # For example:
    app.place_limit_order("MES", "FUT", "BUY", 1, PRICE)
    
    # Wait for 5 seconds (or adjust as needed)
    time.sleep(5)

    for i in range(1, 6):
        app.place_limit_order("MES", "FUT", "BUY", 1, PRICE + i)
        time.sleep(1)
    
    # Cancel the order
    app.cancel_order_by_details("MES", "BUY", PRICE)

    # Don't forget to disconnect when done
    # app.disconnect()

    app.place_limit_order("AAPL", "STK", "BUY", 1, 100)

    time.sleep(10)
    app.cancel_all_orders()

    # Disconnect
    app.ib_disconnect()
