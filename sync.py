# Import necessary libraries
from flask import Flask, render_template
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import time

from config import rpc_user, rpc_password, rpc_port, rpc_host


import json
import sqlite3


from flask_socketio import SocketIO, emit


batch_size = 500
# Database configuration
DATABASE = 'pruxplor.db'



# Create a Flask application
app = Flask(__name__)



from socketio import Client

def connectsocketio(Client):
    while True:
        try:
            # Connect to the socket server
            socket = Client()
            socket.connect('http://localhost:5001')
            return socket
        except Exception as e:
            print(f"Connection failed: {e}")
            time.sleep(5)  # Wait for 5 seconds before attempting to reconnect





def disconnect():
    socket = Client()  
    socket.disconnect()



def connecttorpc():

    rpc_connection = None

    while not rpc_connection:
        try:
            rpc_connection = AuthServiceProxy(f'http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}', timeout=2000)
        except Exception as e:
            print(f"Error connecting to RPC: {str(e)}")
            print("Retrying in 1 second...")
            time.sleep(1)

    return rpc_connection

def make_rpc_request(rpc_connection, method, *params):
    max_retries = 90
    retry_delay = 1  # in seconds
    for _ in range(max_retries + 1):
        try:
            connecttorpc()
            return getattr(rpc_connection, method)(*params)
        except (JSONRPCException, ConnectionRefusedError) as e:
            print(f"Error in RPC request: {str(e)}")
            print("Retrying in {} seconds...".format(retry_delay))
            time.sleep(retry_delay)

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            print("Retrying in {} seconds...".format(retry_delay))
            time.sleep(retry_delay)

    raise Exception(f"Failed to make RPC request after {max_retries} retries.")






def create_hashrate_table():
    try:
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            cursor = connection.cursor()

            # Create the new hashrate table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hashrate (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ActualHashrate REAL,
                    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            connection.commit()

    except Exception as e:
        print(f"Error creating hashrate table: {e}")



def create_db():
    """Create the SQLite database and necessary tables."""
    with sqlite3.connect(DATABASE, timeout=5000) as connection:
        cursor = connection.cursor()

import sqlite3

DATABASE = "pruxplor.db"

def create_db():
    """Create the SQLite database and necessary tables."""
    with sqlite3.connect(DATABASE, timeout=5000) as connection:
        cursor = connection.cursor()

        # Create chaindata table with indexes on all columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chaindata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blockcount INTEGER,
                block_hash TEXT,
                block_tx TEXT,
                bits,
                nonce,
                block_version,
                block_size,
                tx_count,               
                time_received DATETIME,
                accounted INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blockcount ON chaindata (blockcount);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_block_hash ON chaindata (block_hash);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_block_tx ON chaindata (block_tx);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bits ON chaindata (bits);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nonce ON chaindata (nonce);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_block_version ON chaindata (block_version);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_block_size ON chaindata (block_size);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_count ON chaindata (tx_count);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_received_chaindata ON chaindata (time_received);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_accounted ON chaindata (accounted);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_id ON chaindata (id);')
        connection.commit()

        # Create blockdetails table with indexes on all columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blockdetails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_id TEXT,
                size INTEGER,
                fee REAL,
                inputs TEXT,
                outputs TEXT,
                time_received DATETIME,
                receiver_address TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_id_blockdetails ON blockdetails (tx_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_size ON blockdetails (size);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fee ON blockdetails (fee);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inputs ON blockdetails (inputs);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_outputs ON blockdetails (outputs);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_received_blockdetails ON blockdetails (time_received);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_receiver_address ON blockdetails (receiver_address);')
        connection.commit()

        # Create addresses table with indexes on all columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                tx_id TEXT,
                blockcount INTEGER,
                incoming_amount INTEGER,
                outgoing_amount INTEGER,
                time_received DATETIME,
                transaction_type TEXT  -- 'incoming' or 'outgoing'
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_address ON addresses (address);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_id_addresses ON addresses (tx_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blockcount_addresses ON addresses (blockcount);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_incoming_amount ON addresses (incoming_amount);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_outgoing_amount ON addresses (outgoing_amount);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_received_addresses ON addresses (time_received);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_type ON addresses (transaction_type);')
        connection.commit()


        # Create addresses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mempool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_id TEXT,
                size INTEGER,
                fee REAL,
                inputs TEXT,
                outputs TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        connection.commit()





# Create database at the start of the app
create_db()
create_hashrate_table()







def cleanUpPartiallyProcessedBlocks():

    global cleanup_done  # Assuming cleanup_done is defined elsewhere in your script
    
    with sqlite3.connect(DATABASE, timeout=5000) as connection:
        cursor = connection.cursor()

        try:    

            # Start a transaction
            connection.execute('BEGIN TRANSACTION')

            # Query the database for blocks that are accounted but not fully processed
            cursor.execute('SELECT block_hash, block_tx FROM chaindata WHERE accounted = 0')

            partially_processed_blocks = cursor.fetchall()

            # Process each partially processed block
            for block_hash, block_tx in partially_processed_blocks:
                # Delete entries in blockdetails
                cursor.execute('DELETE FROM blockdetails WHERE tx_id = ?', (block_hash,))
                print(f"Delet in blockdetails the  tx_id`s  for block =  {block_hash} ")


                cursor.execute('DELETE FROM addresses WHERE tx_id = ?', (block_tx,))
                print(f"Delet in addresses  the  tx_id  for block =  {block_tx} ")

            # Commit the transaction
            connection.execute('COMMIT')
            print("Deleted unfinished synced blocks and related entries")


            # Check if there are rows with accounted = 0 in the chaindata table
            cursor.execute('SELECT COUNT(*) FROM chaindata WHERE accounted = 0')
            remaining_rows = cursor.fetchone()[0]

            if remaining_rows > 0:
                cursor.execute('DELETE FROM chaindata WHERE accounted = 0')
                print("Deleted entire rows in chaindata where accounted is 0")
                connection.commit()
                print("Remaining rows with accounted = 0. Introducing time delay.")
                time.sleep(2)
                
            connection.commit()

            # Mark cleanup as done
            cleanup_done = True

        except Exception as e:
            # Rollback the transaction in case of an error
            connection.execute('ROLLBACK')
            print(f"Error: {e}")
            print("Transaction rolled back")



# Assuming cleanup_done is a global variable
cleanup_done = False







# Define records outside the function to maintain state
records = []

from decimal import Decimal



# Global variable to store records
records = []












# Function to add amounts to addresses
def addAmountToAddress(connection, incoming_to_insert):
    global records
    
    print(f"Added {len(incoming_to_insert)} records to addresses for transactions.")
    
    try:
        for record in incoming_to_insert:
            # Extract record
            incoming_amount = Decimal(record['incoming_amount']) * Decimal(1e8)
            outgoing_amount = Decimal(record['outgoing_amount']) * Decimal(1e8)
            record = (
                record['address'],
                record['tx_id'],
                int(incoming_amount),
                int(outgoing_amount),
                record['time_received'],
                record['transaction_type'],
                record['blockcount']
            )

            records.append(record)


    except sqlite3.OperationalError as e:
        print(f"Error adding amounts to addresses: {e}")





import sqlite3

# Assuming rpc_connection, block_data, block_data['time'], and block_data['height'] are defined somewhere

# Function to check if a string is a valid hexadecimal value
def is_valid_hex(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False






from decimal import Decimal

def generateAddressEntries(connection, block_data):
    cursor = connection.cursor()
    rpc_connection = connecttorpc()  # Establish the RPC connection
    print(f"block_data {block_data}.")

    try:
        # Process Outputs
        for tx_id in block_data['tx']:
            if tx_id:
                try:
                    tx = make_rpc_request(rpc_connection, 'getrawtransaction', tx_id, 1)

                    # Handle vout correctly
                    vout = tx.get('vout', [])
                    incoming_to_insert = []
                    batch_size = 100
                    for output in vout:
                        output_addresses = output.get('scriptPubKey', {}).get('addresses', [])
                        if output_addresses:
                            output_address = output_addresses[0]
                            output_amount = Decimal(str(output.get('value', 0)))  # Use Decimal for better precision

                            if output_address:
                                print(f"Added incoming {output_amount} to {output_address} for transaction {tx_id}.")
                                incoming_to_insert.append({
                                    'tx_id': tx_id,
                                    'address': output_address,
                                    'incoming_amount': Decimal(output_amount),
                                    'outgoing_amount': 0,
                                    'time_received': block_data['time'],
                                    'transaction_type': 'incoming',
                                    'blockcount': block_data['height']
                                })

                                # Check if the batch size is reached
                                if len(incoming_to_insert) >= batch_size:
                                    addAmountToAddress(connection, incoming_to_insert)
                                    incoming_to_insert = []

                    # Check if there are any remaining records
                    if len(incoming_to_insert) > 0:
                        addAmountToAddress(connection, incoming_to_insert)
                        print(f"Input transaction")

                except Exception as e:
                    print(f"Error fetching raw transaction details for output transaction {tx_id}: {str(e)}")

        # Process inputs
        for tx_id in block_data['tx']:
            if tx_id:
                try:
                    tx = make_rpc_request(rpc_connection, 'getrawtransaction', tx_id, 1)
                    print(f"Processing inputs for transaction {tx_id}: {tx}")

                    vin = tx.get('vin', [])
                    incoming_to_insert = []
                    batch_size = 100
                    for input_tx in vin:
                        if 'coinbase' in input_tx:
                            print(f"Coinbase detected for transaction {tx_id}.")
                            coinbase_amount = Decimal(str(tx.get('vout', [])[0].get('value', 0)))
                            incoming_to_insert.append({
                                'tx_id': tx_id,
                                'address': "COINBASE",
                                'incoming_amount': 0,
                                'outgoing_amount': coinbase_amount,
                                'time_received': block_data['time'],
                                'transaction_type': 'outgoing',
                                'blockcount': block_data['height']
                            })
                        else:
                            prev_tx_id = input_tx.get('txid')
                            prev_vout = input_tx.get('vout')

                            if prev_tx_id:
                                try:
                                    prev_tx = make_rpc_request(rpc_connection, 'getrawtransaction', prev_tx_id, 1)
                                    if 'vout' in prev_tx:
                                        prev_output = prev_tx['vout'][prev_vout]

                                        # Process inputs
                                        input_info = {'address': "", 'outgoing_amount': Decimal(0)}

                                        # Check if 'addresses' is present in the scriptPubKey
                                        if 'addresses' in prev_output.get('scriptPubKey', {}):
                                            addresses = prev_output['scriptPubKey']['addresses']
                                            if addresses:
                                                prev_address = addresses[0]
                                                prev_amount = Decimal(str(prev_output.get('value', 0)))  # Use Decimal for better precision

                                                if prev_address:
                                                    incoming_to_insert.append({
                                                        'tx_id': tx_id,
                                                        'address': prev_address,
                                                        'incoming_amount': 0,
                                                        'outgoing_amount': Decimal(prev_amount),
                                                        'time_received': block_data['time'],
                                                        'transaction_type': 'outgoing',
                                                        'blockcount': block_data['height']
                                                    })

                                                    if len(incoming_to_insert) >= batch_size:
                                                        addAmountToAddress(connection, incoming_to_insert)
                                                        incoming_to_insert = []

                                except Exception as e:
                                    print(f"Error processing input transaction {prev_tx_id}: {str(e)}")

                    # Check if there are any remaining records
                    if len(incoming_to_insert) > 0:
                        addAmountToAddress(connection, incoming_to_insert)

                except Exception as e:
                    print(f"Error getting raw transaction for input transaction {tx_id}: {str(e)}")

        print(f"Generated address entries for block {block_data['height']}.")

    except Exception as e:
        print(f"Error processing transactions: {str(e)}")

    print(f"Generated address entries for block {block_data['height']}.")




class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)





def mempool_sync():
    rpc_connection = connecttorpc()  # Establish the RPC connection
    try:
        mempool = make_rpc_request(rpc_connection, 'getrawmempool')

        transactions = []
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            cursor = connection.cursor()
            for txid in mempool:
                # Check if the transaction is already in the database
                cursor.execute('SELECT 1 FROM mempool WHERE tx_id = ?', (txid,))
                existing_transaction = cursor.fetchone()

                if not existing_transaction:
                    # Transaction not in the database, fetch details from RPC
                    transaction = make_rpc_request(rpc_connection, 'getrawtransaction', txid, 1)
                    

                    input_value = sum(input.get('value', input.get('amount', 0)) for input in transaction.get('vin', []))
                    output_value = sum(output.get('value', output.get('amount', 0)) for output in transaction.get('vout', []))
                    fee = (input_value - output_value) / 100000000  # Convert satoshis to BTC

                    outputs = []
                    real_receiver = None  # Initialize real receiver information
                    for output in transaction.get('vout', []):
                        receiver_address = output['scriptPubKey']['addresses'][0] if 'addresses' in output['scriptPubKey'] else 'N/A'
                        amount = output['value']
                        outputs.append({'receiver_address': receiver_address, 'amount': amount})

                        # Check if the output is a potential real receiver (non-change output)
                        if amount > 0:
                            # Additional checks, if needed, to confirm it as the real receiver
                            # For example, checking if the address meets certain criteria

                            # Assign the first non-change output as the real receiver
                            if real_receiver is None:
                                real_receiver = {'receiver_address': receiver_address, 'amount': amount}

                    inputs = []
                    for _input in transaction.get('vin', []):
                        input_txid = _input.get('txid', '')
                        vout = _input.get('vout', '')

                        input_transaction = make_rpc_request(rpc_connection, 'getrawtransaction', input_txid, 1)
                        input_amount = input_transaction['vout'][vout]['value']

                        inputs.append({'transaction_id': input_txid, 'vout': vout, 'amount': input_amount})

                    transaction['fee'] = str(fee)  # Convert fee to string
                    transaction['outputs'] = outputs
                    transaction['inputs'] = inputs
                    transaction['real_receiver'] = real_receiver
                    transactions.append(transaction)

                    # Print types and values for debugging
                    print(f"Values before insertion: {txid}, {int(transaction['size'])}, {float(fee)}, {json.dumps(inputs, cls=DecimalEncoder)}, {json.dumps(outputs, cls=DecimalEncoder)}")

                    try:
                        # Store the transaction in the database
                        cursor.execute('''
                            INSERT INTO mempool (tx_id, size, fee, inputs, outputs)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (txid, int(transaction['size']), str(fee), json.dumps(inputs, cls=DecimalEncoder), json.dumps(outputs, cls=DecimalEncoder)))

                        # Commit the transaction
                        connection.commit()
                    except sqlite3.Error as e:
                        # Rollback the transaction on error
                        connection.rollback()
                        print(f"SQLite error during insertion: {e}")

        return transactions

    except JSONRPCException as e:
        print(f"Error: {str(e)}")

    rpc_connection.close()






def get_hashrate():
    rpc_connection = connecttorpc()  # Establish the RPC connection
    try:
        mining_info = make_rpc_request(rpc_connection, 'getmininginfo')
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

        




# Helper function to check if a string is a valid hexadecimal
def is_valid_hex(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False



def issynced(rpc_connection, current_block):

    try:
        # Get the latest block height from the daemon
        latest_block = make_rpc_request(rpc_connection, 'getblockcount')

        # Set a threshold for synchronization (e.g., 500 blocks behind)
        sync_threshold = latest_block - 500

        # Check if the current block is less than or equal to the sync threshold
        return current_block >= sync_threshold

    except JSONRPCException as e:
        print(f"Error checking synchronization status: {str(e)}")
        return False



def insert_chaindata(cursor, connection):

    # Example usage:
    block_data = {
        'blockcount': 1,
        'block_hash': '32dca787cfb73d50595a599b6fd72afce9a7c52ead22b8f15dfd8aabc5eaac32',
        'block_tx': '275a35ac6f6d4a6f7a60ee3ca38a90fe98e43646b6535cf3f99f6b004a4016b6',
        'time_received': 1406496258,
        'accounted': 1,
        'bits': '1e0ffff0',
        'nonce': 2984499,
        'block_version': 1,
        'block_size': 246,
        'tx_count': 0
     }

    cursor.execute('''
        INSERT INTO chaindata (blockcount, block_hash, block_tx, bits, nonce, block_version, block_size, tx_count, time_received, accounted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (block_data['blockcount'],
          block_data['block_hash'],
          block_data['block_tx'],
          block_data['bits'],
          block_data['nonce'],
          block_data['block_version'],
          block_data['block_size'],
          block_data['tx_count'],
          block_data['time_received'],
          block_data['accounted']))
    
    print(f"Inserted block {block_data['blockcount']} into chaindata.")
    connection.commit()
    current_block = 1


    return current_block


def insert_blockdetails(cursor, tx_id, size, fee, inputs, outputs, timestamp, receiver_address):
    cursor.execute('''
        INSERT INTO blockdetails (tx_id, size, fee, inputs, outputs, time_received, receiver_address)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (tx_id, size, fee, json.dumps(inputs, cls=DecimalEncoder), json.dumps(outputs, cls=DecimalEncoder), timestamp, receiver_address))
    connection.commit()    
    
    
# Define max journal size in megabytes
max_journal_size_mb = 35  
hasratecounter = int() 


# Function to populate database with block data
def populateDatabase():
    global hasratecounter 

    rpc_connection = connecttorpc()  # Establish the RPC connection


    global records
    records_to_insert2_accumulated = []
    records_to_insert3_accumulated = []
    try:
        # Retrieve the latest accounted block count from the database
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            connection.execute('PRAGMA journal_size_limit = {}'.format(max_journal_size_mb * 1024 * 1024))  # Set max journal size
            cursor = connection.cursor()
            cursor.execute('SELECT MAX(blockcount) FROM chaindata WHERE accounted = 1')
            latest_accounted_block = cursor.fetchone()[0]

        # If there are no accounted blocks, set the latest_accounted_block to -1
        if latest_accounted_block is None:
            latest_accounted_block = -1

        # Start synchronization from block 0 if the database is empty, otherwise from the latest accounted block + 1
        current_block = 0 if latest_accounted_block == -1 else latest_accounted_block + 1

        # Batch size for committing records to the database
        batch_size = 2
        if current_block == 0:
            current_block = insert_chaindata(cursor, connection) 
            
            
        while True:
            # Check synchronization status
            rpc_connection = connecttorpc()  # Establish the RPC connection
            synced_status = issynced(rpc_connection, current_block)

            if synced_status:
                print(f"Is SYNCED")
                break  # Exit the loop if synchronized
                

            try:
                # Use getblockhash to get the block hash for the current block
                block_hash = make_rpc_request(rpc_connection, 'getblockhash', current_block)

                # Use getblock with the hash to get the block data   
                block_data = make_rpc_request(rpc_connection, 'getblock', block_hash)

                print(f"Block Data for {current_block}: {block_data}")

                # Fetch transaction details separately
                block_data['nTx'] = len(block_data['tx'])
                print(f"Transaction Details for {current_block}: {block_data['tx']}")

                # Insert block data into chaindata table
                with sqlite3.connect(DATABASE, timeout=5000) as connection:
                    connection.execute('PRAGMA journal_size_limit = {}'.format(max_journal_size_mb * 1024 * 1024))  # Set max journal size
                    cursor = connection.cursor()



                # Call populateDatabaseDetails and store the returned values
                tx_id, size, fee, inputs, outputs, timestamp, receiver_address = populateDatabaseDetails(block_hash, block_data)

                # Insert transaction data and update accounted status
                with sqlite3.connect(DATABASE, timeout=5000) as connection:
                    connection.execute('PRAGMA journal_size_limit = {}'.format(max_journal_size_mb * 1024 * 1024))  # Set max journal size
                    cursor = connection.cursor()

                    if current_block > 1:
                        batch_size = 1000

                    if current_block > 10000:
                        batch_size = 500

                    if current_block > 1000000:
                        batch_size = 300

                    # Skip inserting transaction data for block 0
                    if current_block > 0:
                        # Generate entries in the addresses table for incoming and outgoing transactions
                        generateAddressEntries(connection, block_data)

                        # Use the existing logic for subsequent blocks
                        tx_list = block_data['tx'] if isinstance(block_data['tx'], list) else [block_data['tx']]
                        tx_list_str = ', '.join(tx_list)

                        records_to_insert2 = [(block_data['height'], block_data['hash'], tx_list_str, block_data['time'], 0,
                                               block_data['bits'], block_data['nonce'], block_data['version'], block_data['size'],
                                               block_data['nTx'])]

                        records_to_insert3 = [(tx_id, size, fee, json.dumps(inputs, cls=DecimalEncoder), json.dumps(outputs, cls=DecimalEncoder), timestamp, receiver_address)]

                        # Accumulate records for insertion
                        records_to_insert2_accumulated.extend(records_to_insert2)
                        records_to_insert3_accumulated.extend(records_to_insert3)

                        if len(records_to_insert2_accumulated) >= batch_size:
                            cursor.executemany('''
                                INSERT INTO chaindata (blockcount, block_hash, block_tx, time_received, accounted,
                                                       bits, nonce, block_version, block_size, tx_count)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', records_to_insert2_accumulated)

                            print(f"records_to_insert2 records_to_insert2 records_to_insert2 records_to_insert2 records_to_insert2    1")

                            cursor.executemany('''
                                INSERT INTO blockdetails (tx_id, size, fee, inputs, outputs, time_received, receiver_address)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', records_to_insert3_accumulated)

                            print(f"records{records}")

                            # Insert the batch into the database
                            cursor.executemany('''
                                INSERT INTO addresses (address, tx_id, incoming_amount, outgoing_amount, time_received, transaction_type, blockcount)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', records)
                            print(f"addresses into DB")

                            # Clear processed records
                            records = []

                            # Set accounted to 1 for the synced blocks in chaindata table
                            start_block = current_block - len(records_to_insert2_accumulated)  # Calculate the start block
                            end_block = current_block   # Calculate the end block
                            cursor.execute('UPDATE chaindata SET accounted = 1 WHERE blockcount BETWEEN ? AND ?', (start_block, end_block))
                            print(f"DB ADDDDDDD    3")

                            # Clear accumulated records
                            records_to_insert2_accumulated = []
                            records_to_insert3_accumulated = []

                            connection.commit()
                            socket.emit('reload_page')
                            hasratecounter = hasratecounter + 1
                            if hasratecounter == 5:
                                hasratecounter = 0
                                get_hashrate()
                                mempool_sync()



                print(f"Synced block {block_data['height']} successfully.")
                current_block += 1


            except JSONRPCException as e:
                print(f"Error retrieving data for block {current_block}: {str(e)}")
                time.sleep(10)  # Adjust the sleep time based on your needs

    except JSONRPCException as e:
        print(f"Error: {str(e)}")







import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)







def get_latest_unaccounted_block():
    try:
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            connection.row_factory = sqlite3.Row  # Use Row factory to access columns by name
            cursor = connection.cursor()

            # Select the latest unaccounted block from the chaindata table
            cursor.execute('SELECT block_hash FROM chaindata WHERE accounted = 0 ORDER BY id DESC LIMIT 1')
            
            result = cursor.fetchone()

            if result:
                return result['block_hash']  # Access the column by name
            else:
                return None  # Return None if no unaccounted blocks are found in the table

    except sqlite3.Error as e:
        print(f"SQLite error during unaccounted block retrieval: {e}")
        return None










def get_address(script_pubkey):
    addresses = script_pubkey.get('addresses', [])
    return addresses[0] if addresses else None

def process_inputs(transaction):
    inputs = []
    for vin in transaction['vin']:
        input_info = {}
        if 'coinbase' in vin:
            input_info['coinbase'] = vin['coinbase']
        else:
            input_info['txid'] = vin['txid']
            input_info['vout'] = vin['vout']
            input_info['address'] = get_address(vin.get('scriptPubKey', {}))
            input_info['amount'] = -vin.get('value', 0)
        inputs.append(input_info)
    return inputs


def process_outputs(transaction):
    outputs = []
    for vout in transaction['vout']:
        output_info = {}
        output_info['value'] = vout['value']
        output_info['scriptPubKey'] = vout['scriptPubKey']
        output_info['address'] = get_address(vout['scriptPubKey'])
        output_info['amount'] = vout['value']
        outputs.append(output_info)
    return outputs



def populateDatabaseDetails(block_hash, block_data):
    rpc_connection = connecttorpc()  # Establish the RPC connection

    try:
        # Use getblock to get the block data for the latest accounted block_tx
        print(f"Fetching block data for block_tx: {block_hash}")

        try:
            block_data = make_rpc_request(rpc_connection, 'getblock', block_hash, True)
            print(f"Block data22: {block_data}")

            # Process block data and extract needed variables
            tx_id = block_hash
            size = block_data.get('size', 0)
            fee = 0  # Calculate fee based on transaction inputs and outputs
            inputs = []  # Extract input information from block_data['tx']
            outputs = []  # Extract output information from block_data['tx']

            for txid in block_data['tx']:
                try:
                    print(f"Fetching transaction details for txid: {txid}")
                    transaction = make_rpc_request(rpc_connection, 'getrawtransaction', txid, 1)
                    print(f"Transaction details: {transaction}")

                    # Process inputs and outputs
                    inputs.extend(process_inputs(transaction))
                    outputs.extend(process_outputs(transaction))

                except JSONRPCException as e:
                    print(f"Error fetching transaction details: {str(e)}")
                    if e.code == -32601:
                        print(f"Method not found (getrawtransaction): {str(e)}")
                        return []
                    else:
                        raise

            # Modify outputs to include receiver_address
            for output in outputs:
                script_pubkey = output['scriptPubKey']
                receiver_address = get_address(script_pubkey)
                output['receiver_address'] = receiver_address

            # Extract timestamp from block data
            timestamp = block_data.get('time')

            # Print types and values for debugging
            print(f"Values before insertion: {tx_id}, {size}, {fee}, {json.dumps(inputs, cls=DecimalEncoder)}, {json.dumps(outputs, cls=DecimalEncoder)}, {timestamp}, {receiver_address}")

            return tx_id, size, fee, json.dumps(inputs, cls=DecimalEncoder), json.dumps(outputs, cls=DecimalEncoder), timestamp, receiver_address  # Return the processed block data as a list

        except JSONRPCException as e:
            if e.code == -5:
                print(f"Block not found: {block_hash}")
                return []  # Skip further processing for this block
            elif e.code == -32601:
                print(f"Method not found (getblock): {str(e)}")
                return []
            else:
                raise

    except JSONRPCException as e:
        print(f"Error: {str(e)}")


    





# Check for cleanup only once when the application starts
if not cleanup_done:
    cleanUpPartiallyProcessedBlocks()




# Block synchronization logic
try:   
    socket = connectsocketio(Client)
    populateDatabase()
    print(f"getinfo: {str(getinfo)}")
except JSONRPCException as e:
    print(f"Error: {str(e)}")







# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=0)
