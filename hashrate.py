# mempool.py

import sqlite3
import time
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import json
from decimal import Decimal
import json
import sqlite3
from json.decoder import JSONDecodeError



DATABASE = 'pruxplor.db'

from config import rpc_user, rpc_password, rpc_port


rpc_connection = AuthServiceProxy(f'http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}')


from flask_socketio import SocketIO, emit
from socketio import Client

# Connect to the Flask-SocketIO server
socket = Client()
socket.connect('http://localhost:5001')  # Replace with the actual URL of your Flask-SocketIO server





def get_hashrate():
    try:
        mining_info = rpc_connection.getmininginfo()
        hashrate = mining_info.get('networkhashps', 'N/A')
        print(f"Hashrate: {hashrate}")

        # Manually convert Decimal to float for serialization
        hashrate_float = float(hashrate)
        socket.emit('hashrate_data', {'hashrate': hashrate_float}, namespace='/')


        write_hashrate_to_db(hashrate)

    except JSONRPCException as e:
        print(f"Error getting hashrate: {e}")
        return 'N/A'

def write_hashrate_to_db(hashrate):
    retry_count = 10

    while retry_count > 0:
        try:
            with sqlite3.connect(DATABASE, timeout=5000) as connection:
                cursor = connection.cursor()

                # Create the table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS hashrate (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ActualHashrate TEXT,
                        Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Convert hashrate to string before inserting
                hashrate_str = str(hashrate)

                # Insert the hashrate into the table
                cursor.execute('INSERT INTO hashrate (ActualHashrate) VALUES (?)', (hashrate_str,))
                connection.commit()

            # If successful, break out of the loop
            break

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                print("Database is locked. Retrying in 1 second.")
                time.sleep(1)
                retry_count -= 1
            else:
                print(f"Error writing hashrate to database: {e}")
                break
        except Exception as e:
            print(f"Error writing hashrate to database: {e}")
            break
    else:
        print("Unable to write to the database after 10 retries. Please check the database.")

        





if __name__ == '__main__':
    while True:
        get_hashrate()
        print("Waiting for 8 seconds before the next iteration...")
        time.sleep(8)

