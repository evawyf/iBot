
import random
from utils.bidict import BiDict

class ClientIDAssigner:
    def __init__(self, clients=[]):
        self.client_id_map = BiDict()
        for client in clients:
            self.assign_client_id(client)


    def assign_client_id(self, task_name):
        task = task_name.lower()
        # Assign client IDs based on the task name
        if "account" in task:
            self.assign_client_id_range(task_name, 1000, 1999)
        elif "order" in task:
            self.assign_client_id_range(task_name, 2000, 2999)
        elif "data" in task:
            self.assign_client_id_range(task_name, 3000, 3999)
        elif "indicator" in task:
            self.assign_client_id_range(task_name, 5000, 5999)
        elif "strategy" in task:
            self.assign_client_id_range(task_name, 6000, 6999)
        else:
            self.assign_client_id_range(task_name, 9000, 9999)  # Default range for unspecified tasks

    
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

