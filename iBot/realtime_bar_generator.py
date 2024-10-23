from DataRealtimeBarGenerator import IBRealtimeDataBarGenerator
from utils.clientid_assigner import ClientIDAssigner
import signal
import sys

PORT = 7497
SYMBOL = "MES"
CONTRACT_TYPE = "FUT"


assigner = ClientIDAssigner(clients=["realtime_data_generator"])
client_id = assigner.client_id_map["realtime_data_generator"]
realtime_bar_generator = IBRealtimeDataBarGenerator(PORT, client_id, SYMBOL, CONTRACT_TYPE, bar_frequency_seconds=60)

if realtime_bar_generator.ib_connect():
    print("Press Ctrl+1 to disconnect and exit.")
    realtime_bar_generator.start()
else:
    print("Failed to connect to TWS.")
