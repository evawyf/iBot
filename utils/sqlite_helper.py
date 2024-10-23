import sqlite3
import threading
import queue
import pandas as pd

class SQLiteHelper:
    def __init__(self, db_name):
        self.db_name = db_name
        self.sqlite_queue = queue.Queue()
        self.sqlite_thread = threading.Thread(target=self.sqlite_worker, daemon=True)
        self.sqlite_thread.start()

        if 'market' in self.db_name.lower():
            self.table_name = 'market_data'
        elif 'historical' in self.db_name.lower():
            self.table_name = 'historical_data'
        else:
            self.table_name = 'data'

    def sqlite_worker(self):
        with sqlite3.connect(self.db_name) as db:
            self.create_data_table(db)
            
            while True:
                operation, args = self.sqlite_queue.get()
                
                if operation == "INSERT":
                    self.insert_data_to_sqlite(db, args)
                elif operation == "INSERT_MANY":
                    self.insert_many_to_sqlite(db, args)
                elif operation == "CLOSE":
                    break
                
                self.sqlite_queue.task_done()

    def create_data_table(self, db):
        db.execute(f'''
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            timestamp TEXT,
            symbol TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (timestamp, symbol)
        )
        ''')
        db.commit()

    def insert_data_to_sqlite(self, db, args):
        db.execute(f'''
        INSERT OR REPLACE INTO {self.table_name} 
        (timestamp, symbol, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', args)
        db.commit()

    def insert_many_to_sqlite(self, db, args):
        db.executemany(f'''
        INSERT OR REPLACE INTO {self.table_name} 
        (timestamp, symbol, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', args)
        db.commit()

    def queue_insert(self, data):
        if isinstance(data, (list, tuple)) and len(data) == 7:
            self.sqlite_queue.put(("INSERT", data))
        elif isinstance(data, pd.DataFrame):
            records = data.to_records(index=False)
            self.sqlite_queue.put(("INSERT_MANY", list(records)))
        else:
            raise ValueError("Invalid data format for insertion")

    def close(self):
        self.sqlite_queue.put(("CLOSE", None))
        self.sqlite_thread.join()
