# Import necessary libraries


from gevent import monkey

import re



import eventlet
from flask import Flask, render_template
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from flask_socketio import SocketIO, emit
from threading import Thread
import time
import datetime
from flask import Flask, render_template, request, url_for
import re
from datetime import datetime, timedelta
import json



from config import rpc_user, rpc_password, rpc_port, rpc_host


rpc_connection = AuthServiceProxy(f'http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}')


import json
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dfsfghfu654353rdgfdsgdfgsdgfdreDSDdaer234D!'

socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")



def create_rpc_connection():
    # Replace with your actual RPC server information
    return AuthServiceProxy("http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}")




# Database configuration
DATABASE = 'pruxplor.db'

# Define the custom filter
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    # Convert Unix timestamp to datetime object
    dt_object = datetime.utcfromtimestamp(value)
    # Format the datetime object as a string
    return dt_object.strftime(format)




def get_latest_and_last_blocks(cursor):
    # Set your desired PRAGMA statements (if needed, this can be optional)
    cursor.execute('PRAGMA cache_size = 10000;')
    cursor.execute('PRAGMA journal_mode = WAL;')

    # Get the latest synced block based on the highest id
    cursor.execute('SELECT * FROM chaindata WHERE accounted = 1 ORDER BY id DESC LIMIT 1')
    latest_block = cursor.fetchone()

    # Get the last 10 blocks based on the highest ids
    cursor.execute('SELECT * FROM chaindata WHERE accounted = 1 ORDER BY id DESC LIMIT 10')
    last_10_blocks = cursor.fetchall()

    return latest_block, last_10_blocks

from decimal import Decimal
import json

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


def get_hashrate():
    try:
        mining_info = rpc_connection.getmininginfo()
        hashrate = mining_info.get('networkhashps', 'N/A')
        return hashrate

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
                        ActualHashrate REAL,
                        Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Insert the hashrate into the table
                cursor.execute('INSERT INTO hashrate (ActualHashrate) VALUES (?)', (hashrate,))
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


def extract_receiver_address(output):
    match = re.search(r'receiver_address: (.+)$', output)
    return match.group(1) if match else None


def get_average_hashrate_over_time(cursor, interval_minutes, num_entries=None):
    try:
        if num_entries is not None:
            cursor.execute(f'''
                SELECT ActualHashrate
                FROM hashrate
                ORDER BY Timestamp DESC
                LIMIT {num_entries}
            ''')
        else:
            cursor.execute(f'''
                SELECT ActualHashrate
                FROM hashrate
            ''')
        rows = cursor.fetchall()

        # Extract hashrates from the selected entries
        hashrates = [row['ActualHashrate'] for row in rows]

        # Calculate the average hashrate
        if hashrates:
            avg_hashrate = sum(hashrates) / len(hashrates)
            # Convert to megahashes per second (MH/s)
            avg_hashrate_mhs = avg_hashrate / 1_000_000
            return avg_hashrate_mhs
        else:
            return 'N/A'

    except Exception as e:
        print(f"Error getting average hashrate over time: {e}")
        return 'N/A'





@app.route('/')
def index():
    try:
        # Set up the database connection with PRAGMA statements
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            connection.row_factory = sqlite3.Row  # Access columns by name
            cursor = connection.cursor()

            # Set your desired PRAGMA statements
            cursor.execute('PRAGMA cache_size = 10000;')
            cursor.execute('PRAGMA journal_mode = WAL;')

            # Get the latest synced block and the last 10 blocks from the database
            latest_block, last_10_blocks = get_latest_and_last_blocks(cursor)

            # Load the latest hashrate from the hashrate table
            cursor.execute('SELECT ActualHashrate FROM hashrate ORDER BY Timestamp DESC LIMIT 1')
            latest_hashrate_row = cursor.fetchone()

            # Check if there is a latest hashrate
            if latest_hashrate_row:
                latest_hashrate = latest_hashrate_row['ActualHashrate']
            else:
                latest_hashrate = 'N/A'

            # Fetch average hashrates for different time intervals
            avg_hashrate_1min = get_average_hashrate_over_time(cursor, 1, 1)
            avg_hashrate_1h = get_average_hashrate_over_time(cursor, 60, 60)
            avg_hashrate_6h = get_average_hashrate_over_time(cursor, 6 * 60, 6 * 60)
            avg_hashrate_12h = get_average_hashrate_over_time(cursor, 12 * 60, 12 * 60)
            avg_hashrate_24h = get_average_hashrate_over_time(cursor, 24 * 60, 24 * 60)
            avg_hashrate_48h = get_average_hashrate_over_time(cursor, 48 * 60)

            # Calculate the timestamp for 1 minute ago
            one_minute_ago = datetime.utcnow() - timedelta(minutes=1)

            # Fetch transactions not older than 1 minute
            cursor.execute('SELECT * FROM mempool WHERE timestamp >= ? ORDER BY rowid DESC LIMIT 15', (one_minute_ago,))
            rows = cursor.fetchall()

            transactions = []
            for row in rows:
                transaction = {
                    'txid': row['tx_id'],
                    'size': row['size'],
                    'fee': float(row['fee']),  # Convert 'fee' to float
                    'inputs': json.loads(row['inputs']),
                    'outputs': json.loads(row['outputs'])
                }
                transactions.append(transaction)

            # Pass the data to the index.html template
            return render_template(
                'index.html',
                latest_block=latest_block,
                last_10_blocks=last_10_blocks,
                latest_hashrate=latest_hashrate,
                avg_hashrate_1min=avg_hashrate_1min,
                avg_hashrate_1h=avg_hashrate_1h,
                avg_hashrate_6h=avg_hashrate_6h,
                avg_hashrate_12h=avg_hashrate_12h,
                avg_hashrate_24h=avg_hashrate_24h,
                avg_hashrate_48h=avg_hashrate_48h,
                transactions=transactions
            )

    except json.JSONDecodeError as e:
        return f"Error decoding JSON: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"




    
@socketio.on('reload_page', namespace='/')
def handle_reload_page():
    print("Received reload_page event")
    socketio.emit('reload', namespace='/')  # Emit 'reload' instead of 'reload_page'
    print("Emitted reload event")
    




def get_block_data(block_hash):
    try:
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            # Set your desired PRAGMA statements
            cursor.execute('PRAGMA cache_size = 10000;')
            cursor.execute('PRAGMA journal_mode = WAL;')
            cursor.execute('SELECT * FROM chaindata WHERE block_hash = ?', (block_hash,))
            block_data_row = cursor.fetchone()

        # Convert the sqlite3.Row object to a dictionary
        block_data = dict(block_data_row)

        return block_data
    except Exception as e:
        print(f"Error fetching block data: {str(e)}")
        return None









def findblockcontent(block_hash):
    try:
        # Search in the /chaindata table for the block_hash
        # Assuming that you have a function get_block_txs_by_hash in your database module
        block_data = get_block_data(block_hash)
        
        # If block_data is not found, return an empty list
        if not block_data:
            return []

        # Get the block_txs value from the block_data
        block_txs = block_data.get('block_tx', '')
        
        # If there are no block_txs, return an empty list
        if not block_txs:
            return []

        # Call moreblockdetails to get details for each transaction
        result = moreblockdetails(block_txs)

        return result

    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def moreblockdetails(block_txs):
    try:
        # If there are no block_txs, return an empty list
        if not block_txs:
            return []

        # Split the block_tx values
        block_tx_values = block_txs.split(',')

        # Create a list to store details for each transaction
        transaction_details = []

        # Iterate through each block_tx
        for tx_id in block_tx_values:
            try:
                # Get raw transaction details
                raw_transaction = rpc_connection.getrawtransaction(tx_id.strip(), 1)

                # Display transaction inputs
                inputs_info = []
                for vin in raw_transaction['vin']:
                    if 'coinbase' in vin:
                        inputs_info.append("Coinbase Input")
                    else:
                        input_tx_id = vin.get('txid', '')
                        input_vout = vin.get('vout', 0)
                        inputs_info.append(f"Input from TXID: {input_tx_id}, VOUT: {input_vout}")

                # Display transaction outputs
                outputs_info = []
                for vout in raw_transaction['vout']:
                    value = vout['value']
                    script_pubkey = vout['scriptPubKey']

                    # Add print statements to check content
                    print("Script Pubkey:", script_pubkey)

                    addresses = script_pubkey.get('addresses', [])

                    # Add print statements to check content
                    print("Addresses:", addresses)

                    # Use the second value after the comma as receiver_address, if available
                    if len(addresses) > 1:
                        receiver_addresses = addresses[1:]
                    else:
                        receiver_addresses = addresses

                    # Convert receiver_addresses to a string for display
                    receiver_addresses_str = ', '.join(receiver_addresses)

                    # Add print statements to check content
                    print("Receiver Addresses:", receiver_addresses_str)

                    outputs_info.append(f"Value: {value},{receiver_addresses_str}")

                # Append details for the current transaction to the list
                transaction_details.append({
                    'tx_id': tx_id,
                    'inputs': inputs_info,
                    'outputs': outputs_info
                })

            except JSONRPCException as e:
                print(f"Error fetching transaction details: {str(e)}")

        # Return the list of transaction details
        return transaction_details

    except JSONRPCException as e:
        print(f"Error: {str(e)}")






# Modify your block_details route
@app.route('/block/<block_hash>')
def block_details(block_hash):
    try:
        block_data = get_block_data(block_hash)
        print("Block Data:", block_data)
        if not block_data:
            return render_template('generic_error.html', message='Block not found')

        # Get the block_txs value from the block_data
        block_txs = block_data.get('block_tx', '')

        # If there are no block_txs, return an empty list
        if not block_txs:
            return render_template('generic_error.html', message='No transactions in the block')

        # Call findblockcontent to get transaction details using block_hash
        transaction_details = findblockcontent(block_hash)



        # Render block.html with block_data and transaction_details
        return render_template('block.html', block_data=block_data, transaction_details=transaction_details)

    except Exception as e:
        print(f"Error: {str(e)}")
        return render_template('generic_error.html', message='An error occurred')



def get_block_details(block_txs):
    try:
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            # Set your desired PRAGMA statements
            cursor.execute('PRAGMA cache_size = 10000;')
            cursor.execute('PRAGMA journal_mode = WAL;')

            placeholders = ', '.join(['?' for _ in block_txs])
            sql_query = f'SELECT * FROM blockdetails WHERE tx_id IN ({placeholders})'
            print("SQL Query:", sql_query)
            
            cursor.execute(sql_query, block_txs)
            block_details = cursor.fetchall()
            
            result = []
            for detail in block_details:
                try:
                    inputs = json.loads(detail['inputs'])
                    outputs = json.loads(detail['outputs'])
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {str(e)}")
                    inputs = []
                    outputs = []

                result.append({
                    'id': detail['id'],
                    'tx_id': detail['tx_id'],
                    'size': detail['size'],
                    'fee': detail['fee'],
                    'inputs': inputs,
                    'outputs': outputs,
                    'time_received': detail['time_received'],
                    'receiver_address': detail['receiver_address']
                })

            print("Fetched Block Details:", result)

        return result
    except Exception as e:
        print(f"Error fetching block details: {str(e)}")
        return []




def convert_rows_to_dicts(rows):
    return [dict(row) for row in rows]

def calculate_balance(entries):
    balance = 0
    for entry in entries:
        incoming_amount = entry['incoming_amount']
        outgoing_amount = entry['outgoing_amount']

        if incoming_amount:
            balance += incoming_amount
            entry['transaction_type'] = 'incoming'
        elif outgoing_amount:
            balance -= outgoing_amount
            entry['transaction_type'] = 'outgoing'
        else:
            entry['transaction_type'] = ''

        entry['balance'] = round(balance, 2)

    # Display the final balance at the last entry
    if entries:
        entries[-1]['final_balance'] = round(balance, 2)

    return entries


from flask import render_template, request, redirect, url_for

# ...

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST' or request.method == 'GET':
        # Get the search input from the user
        search_input = request.args.get('search') or request.form.get('search')

        # Validate the input
        if not search_input:
            return render_template('error.html', message='Please enter a search query.')

        # Redirect to the appropriate route based on input type
        is_txid = bool(re.match(r'^[0-9a-fA-F]{64}$', search_input))
        return redirect(url_for('tx') if is_txid else 'address', search=search_input)

    # Your logic for handling other cases
    return render_template('index.html')

@app.route('/address', methods=['GET', 'POST'])
def address():
    if request.method == 'POST' or request.method == 'GET':
        # Get the address input from the user
        address_input = request.args.get('search') or request.form.get('search')

        # Validate the address input
        max_address_length = len("PWH4tGUv47TtYFfzSaNtssZsxZ6j777sg9")

        if not address_input or not address_input.isalnum() or len(address_input) > max_address_length:
            return render_template('error.html', message=f'Invalid address format. Please enter a valid alphanumeric address with a maximum length of {max_address_length} characters.')

        # Additional protection: Check if the address follows a specific pattern
        address_pattern = re.compile(r'^[A-Za-z0-9]+$')
        if not address_pattern.match(address_input):
            return render_template('error.html', message='Invalid address format. Please enter a valid alphanumeric address.')

        # Search for the address in the database
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            connection.row_factory = sqlite3.Row  # Access columns by name
            cursor = connection.cursor()
            # Set your desired PRAGMA statements
            cursor.execute('PRAGMA cache_size = 10000;')
            cursor.execute('PRAGMA journal_mode = WAL;')

            # Find all entries for the given address in ascending order by ID
            cursor.execute('SELECT * FROM addresses WHERE address = ? ORDER BY id ASC', (address_input,))
            all_entries = cursor.fetchall()

            if not all_entries:
                return render_template('error.html', message='No entries found for the given address.')

            # Convert SQLite Row objects to dictionaries
            all_entries_dict = convert_rows_to_dicts(all_entries)

            # Calculate the balance for all entries in the database
            all_entries_dict = calculate_balance(all_entries_dict)

            # Pagination
            entries_per_page = int(request.args.get('entries_per_page', 50))
            num_entries = len(all_entries_dict)
            num_pages = (num_entries - 1) // entries_per_page + 1

            # Start from the last page available
            current_page = int(request.args.get('page', num_pages))

            # Adjust start and end indices based on the current page
            start_idx = max(0, (current_page - 1) * entries_per_page)
            end_idx = min(start_idx + entries_per_page, num_entries)

            # Get the entries for the current page
            address_entries = all_entries_dict[start_idx:end_idx]

            # Calculate the final balance
            final_balance = address_entries[-1]['balance'] if address_entries else 0

            # Generate pagination links
            pagination_links = range(max(current_page - 5, 1), min(current_page + 6, num_pages + 1))

            for entry in address_entries:
                entry['cleaned_tx_id'] = re.sub('\W', '', entry ['tx_id']) 

            
            for entry in address_entries:
                entry['cleaned_tx_id'] = re.sub('\W', '', entry ['tx_id']) 

        return render_template('address.html', address_entries=address_entries, address_input=address_input,
                               entries_per_page=entries_per_page, current_page=current_page, num_pages=num_pages,
                               pagination_links=pagination_links, final_balance=final_balance)

    return render_template('address.html')

@app.route('/tx', methods=['GET', 'POST'])
def tx():
    mined_status = False
    mined_entry = None

    if request.method == 'POST' or request.method == 'GET':
        # Get the tx_id input from the user
        tx_id_input = request.args.get('search') or request.form.get('search')

        # Search for entries in the database for the given tx_id
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            connection.row_factory = sqlite3.Row  # Access columns by name
            cursor = connection.cursor()
            # Set your desired PRAGMA statements
            cursor.execute('PRAGMA cache_size = 10000;')
            cursor.execute('PRAGMA journal_mode = WAL;')

            # Check if there is a mined entry
            cursor.execute('SELECT * FROM chaindata WHERE block_tx = ? ORDER BY id ASC', (tx_id_input,))
            mined_entry = cursor.fetchone()

            if mined_entry:
                mined_status = True
                print("Found mined entry:", mined_entry)

            # Find all entries for the given tx_id in ascending order by ID
            cursor.execute('SELECT * FROM addresses WHERE tx_id = ? ORDER BY id ASC', (tx_id_input,))
            all_entries = cursor.fetchall()

        # Convert sqlite3.Row objects to dictionaries
        entries_list = [dict(entry) for entry in all_entries]

        # Fetch address for each entry and add it to the dictionary
        for entry in entries_list:
            entry['address'] = fetch_address(entry['id'])  # Assuming 'id' is the primary key in your 'addresses' table

        # Your logic for displaying the entries in your template
        return render_template('tx.html', entries=entries_list, mined_status=mined_status, mined_entry=mined_entry, tx_id_input=tx_id_input)

    # Your logic for handling other cases (e.g., if request.method == 'GET' without search parameter)
    return render_template('tx.html')  # Adjust the template name as needed





# Function to fetch address based on entry id
def fetch_address(entry_id):
    with sqlite3.connect(DATABASE, timeout=5000) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute('SELECT address FROM addresses WHERE id = ?', (entry_id,))
        result = cursor.fetchone()
        return result['address'] if result else None
        
        
        
        
TEXT_FILE_PATH = "precomputed_data.txt"
RESULTS_PER_PAGE_OPTIONS = [25, 50, 100, 500]

def load_precomputed_data(page_number=1, results_per_page=25):
    # Load precomputed data from the text file
    with open('precomputed_data.txt', 'r') as file:
        data = [line.strip().split('\t') for line in file]

    # Sort the data based on balance in descending order
    sorted_data = sorted(data, key=lambda x: float(x[1]), reverse=True)

    # Calculate the start and end indices for the current page
    start_index = (page_number - 1) * results_per_page
    end_index = start_index + results_per_page

    # Slice the sorted data to get the addresses for the current page
    addresses_page = sorted_data[start_index:end_index]

    return addresses_page




# Your existing route for /coindistribution
@app.route('/coindistribution', methods=['GET', 'POST'])
def coindistribution():
    try:
        # Get the current page number from the query parameters
        page_number = int(request.args.get('page', 1))

        # Get the selected results per page from the form or use the default
        results_per_page = int(request.args.get('results_per_page', 25))

        # Load precomputed data for the current page and results per page
        precomputed_data = load_precomputed_data(page_number, results_per_page)

        # Render the template with the precomputed data
        return render_template(
            'coindistribution.html',
            precomputed_data=precomputed_data,
            page_number=page_number,
            results_per_page=results_per_page,
            result_options=RESULTS_PER_PAGE_OPTIONS
        )

    except Exception as e:
        # Handle exceptions if needed
        print(f"Error in coindistribution route: {str(e)}")
        return "Error occurred"





@app.route('/mempool')
def mempool_transactions():
    try:
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            connection.row_factory = sqlite3.Row  # Access columns by name
            cursor = connection.cursor()
            # Set your desired PRAGMA statements
            cursor.execute('PRAGMA cache_size = 10000;')
            cursor.execute('PRAGMA journal_mode = WAL;')
            
            # Load the latest 20 transactions from mempool from the SQLite database
            cursor.execute('SELECT * FROM mempool ORDER BY rowid DESC LIMIT 20')
            rows = cursor.fetchall()

            transactions = []
            for row in rows:
                transaction = {
                    'txid': row['tx_id'],
                    'size': row['size'],
                    'fee': float(row['fee']),  # Convert 'fee' to float
                    'inputs': json.loads(row['inputs']),
                    'outputs': json.loads(row['outputs'])
                }
                transactions.append(transaction)

        return render_template('mempool.html', transactions=transactions)

    except json.JSONDecodeError as e:
        return f"Error decoding JSON: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"




if __name__ == '__main__':
    eventlet.monkey.patch_all()
    monkey.patch_all()

    # Run the Flask-SocketIO app with Gevent on 0.0.0.0:5000
    socketio.run(app, host='0.0.0.0', port=5001)
