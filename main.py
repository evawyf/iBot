from OrderManager import IBOrderManager
from DataRealtimeBarGenerator import IBRealtimeDataBarGenerator
from DataHistoricalBarCollector import IBHistoricalDataCollector
from utils.clientid_assigner import ClientIDAssigner
from utils.exit import run_check_for_exit
import asyncio
import concurrent.futures
import time

async def run_task(task):
    if await task.ib_connect():
        await task.start()
    else:
        print(f"[ERROR] {task.__class__.__name__} failed to connect to TWS.")

async def iBot(*tasks):
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [loop.run_in_executor(executor, run_task, task) for task in tasks]
        await asyncio.gather(*futures)

def run_iBot(*tasks):
    asyncio.run(iBot(*tasks))

if __name__ == "__main__":

    PORT = 7497
    PRICE = 222.25

    # Initialize the IB connections tasks 
    assigner = ClientIDAssigner(clients=["order_manager", 
                                         "realtime_data_generator", 
                                         "historical_data_generator"])

    order_manager = IBOrderManager(port=PORT, client_id=assigner.client_id_map["order_manager"])
    realtime_data = IBRealtimeDataBarGenerator(port=PORT, client_id=assigner.client_id_map["realtime_data_generator"], symbol="MES", contract_type="FUT", bar_frequency_seconds=60)
    historical_data = IBHistoricalDataCollector(port=PORT, client_id=assigner.client_id_map["historical_data_generator"], symbol="MES", contract_type="FUT", frequency="1 day", duration="1 M")

    tasks = []

    # Define a task for the order manager
    def order_manager_task(order_manager, price):
        if order_manager.ib_connect():
            try:
                order_manager.place_limit_order("MES", "FUT", "BUY", 1, price)
                time.sleep(10)
                for i in range(1, 6):
                    order_manager.place_limit_order("MES", "FUT", "BUY", 1, price + i)
                    time.sleep(1)
                order_manager.cancel_order_by_details("MES", "BUY", price)
                time.sleep(10)
                order_manager.cancel_all_orders()
            finally:
                order_manager.ib_disconnect()
        else:
            print("[ERROR] Failed to connect to TWS.")

    # Add order manager task to the list of tasks to be run
    tasks.append(lambda: order_manager_task(order_manager, PRICE))

    # Test the realtime data manager
    def realtime_data_task(realtime_data):
        if realtime_data.ib_connect():
            try:
                realtime_data.start()
                time.sleep(60)  # Run for 60 seconds
            finally:
                realtime_data.stop()
                realtime_data.ib_disconnect()
        else:
            print("[ERROR] realtime_data Failed to connect to TWS.")

    # Add realtime data task to the list of tasks to be run
    tasks.append(lambda: realtime_data_task(realtime_data))

    # Test the historical data collector
    def historical_data_task(historical_data):
        if historical_data.ib_connect():
            try:
                historical_data.start()
                time.sleep(60)  # Run for 60 seconds
            finally:
                historical_data.stop()
                historical_data.ib_disconnect()
        else:
            print("[ERROR] historical_data Failed to connect to TWS.")

    # Add historical data task to the list of tasks to be run
    tasks.append(lambda: historical_data_task(historical_data))

    # Run all tasks parallelly
    run_iBot(*tasks)

    # After all tasks are completed, disconnect all clients and exit
    print("All tasks completed.")
    
    clients = [order_manager, realtime_data, historical_data]
    for client in clients:
        if client.isConnected():
            client.ib_disconnect()
    
    print("All clients disconnected. Exiting...")
    exit(0)
