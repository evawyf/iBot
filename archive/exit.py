import threading
import time

def check_for_exit(clients):
    print("Press Ctrl+C to exit...")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Exiting...")
        for client in clients:
            client.disconnect()

def run_check_for_exit(clients):
    exit_thread = threading.Thread(target=check_for_exit, args=(clients,))
    exit_thread.start()
    return exit_thread