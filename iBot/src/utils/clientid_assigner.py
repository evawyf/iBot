
import random
from iBot.src.utils.sample_bidict import BiDict

class ClientIDAssigner:
    def __init__(self, clients=[]):
        self.client_id_map = BiDict()
        for client in clients:
            self.assign_client_id(client)


    def assign_client_id(self, task_name):
        task = task_name.lower()
        # Assign client IDs based on the task name
        if "account" in task:
            self.assign_client_id_range(task_name, 10, 19)
        elif "order" in task:
            self.assign_client_id_range(task_name, 20, 29)
        elif "data" in task:
            self.assign_client_id_range(task_name, 30, 39)
        elif "indicator" in task:
            self.assign_client_id_range(task_name, 50, 59)
        elif "strategy" in task:
            self.assign_client_id_range(task_name, 60, 69)
        else:
            self.assign_client_id_range(task_name, 90, 99)  # Default range for unspecified tasks

    
    def assign_client_id_range(self, task_name, start, end):
        available_ids = set(range(start, end)) - set(self.client_id_map.inverse.keys())
        assigned_id = random.choice(list(available_ids)) if available_ids else None
        self.client_id_map[task_name] = assigned_id
        print(f"Assigned client ID {assigned_id} to task {task_name}. ")

# Example usage:
# assigner = ClientIDAssigner()
# order_id = assigner.assign_client_id("order_manager")
# data_id = assigner.assign_client_id("data_collector")
# strategy_id = assigner.assign_client_id("strategy_executor")
# print(f"Order manager ID: {order_id}")
# print(f"Data collector ID: {data_id}")
# print(f"Strategy executor ID: {strategy_id}")
# print(f"Client ID map: {assigner.client_id_map}")

