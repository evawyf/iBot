from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from threading import Lock
import time

class TWS_Client(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

class ClientManager:
    def __init__(self):
        self.clients = {}
        self.lock = Lock()

    def connect_client(self, client_id, host='127.0.0.1', port=7497, client_name=None):
        with self.lock:
            if client_id in self.clients:
                print(f"Client ID {client_id} is already in use.")
                return None

            client = TWS_Client()
            client.connect(host, port, client_id)
            self.clients[client_id] = {'client': client, 'name': client_name}
            print(f"Connected client ID {client_id}" + (f" ({client_name})" if client_name else ""))
            return client

    def get_all_clients(self):
        with self.lock:
            return {id: {'client': info['client'], 'name': info['name']} for id, info in self.clients.items()}

    def disconnect_client(self, client_id):
        with self.lock:
            if client_id in self.clients:
                client = self.clients[client_id]['client']
                client_name = self.clients[client_id]['name']
                client.disconnect()
                del self.clients[client_id]
                print(f"Disconnected client ID {client_id}" + (f" ({client_name})" if client_name else ""))
                return True
            else:
                print(f"No client found with ID {client_id}")
                return False

    def disconnect_all_clients(self):
        for client_id in list(self.clients.keys()):
            self.disconnect_client(client_id)

# Usage example
if __name__ == "__main__":
    manager = ClientManager()

    # Connect some clients
    manager.connect_client(11, client_name="Order Manager")
    manager.connect_client(22, client_name="Data Generator")
    manager.connect_client(33, client_name="Historical Data")

    # Get all connected clients
    all_clients = manager.get_all_clients()
    print("Connected clients:")
    for client_id, info in all_clients.items():
        print(f"ID: {client_id}, Name: {info['name']}")

    # Disconnect a specific client
    manager.disconnect_client(22)
    time.sleep(5)

    # Disconnect all remaining clients
    manager.disconnect_all_clients()
