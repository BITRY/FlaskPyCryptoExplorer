# refresh_data.py

import sqlite3
from datetime import datetime, timedelta
import time

DATABASE = "pruxplor.db"

def create_view():
    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()

        # Set your desired PRAGMA statements
        cursor.execute('PRAGMA cache_size = 100000;')
        cursor.execute('PRAGMA journal_mode = WAL;')

        # Create or replace the view
        cursor.execute('CREATE VIEW IF NOT EXISTS vw_addresses_balance AS '
                       'SELECT address, '
                       'SUM(CASE WHEN transaction_type = "incoming" THEN incoming_amount ELSE -outgoing_amount END) AS balance '
                       'FROM addresses '
                       'GROUP BY address;')

def refresh_and_save_data():
    while True:
        create_view()
        with sqlite3.connect(DATABASE, timeout=250000) as connection:
            cursor = connection.cursor()

            # Drop and recreate the precomputed table based on the view
            cursor.execute('DROP TABLE IF EXISTS precomputed_addresses_balance;')
            cursor.execute('CREATE TABLE IF NOT EXISTS precomputed_addresses_balance AS '
                           'SELECT * FROM vw_addresses_balance;')

            connection.commit()

        # Fetch the refreshed data
        with sqlite3.connect(DATABASE, timeout=25000) as connection:
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM precomputed_addresses_balance;')
            data = cursor.fetchall()

        # Save the data to a text file
        with open("precomputed_data.txt", 'w') as file:
            for row in data:
                file.write(f"{row[0]}\t{row[1]}\n")

        print("Precomputed data refreshed. Waiting for 2 minutes...")
        time.sleep(9800)  # Wait for 2 minutes before the next recomputation

if __name__ == "__main__":
    refresh_and_save_data()

