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

from config import rpc_user, rpc_password, rpc_port, rpc_host


rpc_connection = AuthServiceProxy(f'http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}')


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)



import json
from decimal import Decimal
import sqlite3

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

def mempool_sync():
    try:
        mempool = rpc_connection.getrawmempool()

        transactions = []
        with sqlite3.connect(DATABASE, timeout=5000) as connection:
            cursor = connection.cursor()
            for txid in mempool:
                # Check if the transaction is already in the database
                cursor.execute('SELECT 1 FROM mempool WHERE tx_id = ?', (txid,))
                existing_transaction = cursor.fetchone()

                if not existing_transaction:
                    # Transaction not in the database, fetch details from RPC
                    transaction = rpc_connection.getrawtransaction(txid, 1)

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

                        input_transaction = rpc_connection.getrawtransaction(input_txid, 1)
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




        

# Call mempool_sync once and then wait for 8 seconds before calling it again
if __name__ == '__main__':
    while True:
        mempool_sync()
        print("Waiting for 8 seconds before the next iteration...")
        time.sleep(20)

