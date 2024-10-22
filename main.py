from IBOrderManager import IBOrderManager
import time
from utils.exit import run_check_for_exit
from data_manager import conn_ib_realtime_data_generator
from utils.clientid_assigner import ClientIDAssigner



if __name__ == "__main__":

    PORT = 7497
    # Initialize the IB connections tasks 
    assigner = ClientIDAssigner(clients=["order_manager", "realtime_data_generator"])
    order_manager = IBOrderManager(port=PORT, client_id=assigner.client_id_map["order_manager"])
    realtime_data_manager = conn_ib_realtime_data_generator(port=PORT, client_id=assigner.client_id_map["realtime_data_generator"], 
                                                            symbol="MES", contract_type="FUT", bar_frequency_seconds=60)
    # strategy_manager = conn_strategy_boxes(task_name="strategy_boxes", port=PORT, client_id=6)

    time.sleep(1)

    # Run the exit check in a separate thread 
    # clients = [order_manager, realtime_data_manager]
    # run_check_for_exit(clients)

    """
    # Test the order manager
    """
    PRICE = 222.25   
    order_manager.place_limit_order("MES", "FUT", "BUY", 1, PRICE)
    time.sleep(10)
    for i in range(1, 6):
        order_manager.nextOrderId += 1
        order_manager.place_limit_order("MES", "FUT", "BUY", 1, PRICE + i)
        time.sleep(1)
    order_manager.cancel_order_by_details("MES", "BUY", PRICE)
    time.sleep(10)
    order_manager.cancel_all_orders()

    """
    # Test the data manager
    """


