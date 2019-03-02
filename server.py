from flask import Flask
from flask import render_template
from flask import request
import blockchain
import json
import threading

server = Flask(__name__)
client = Flask(__name__)

creator_public = open("Creator_public.key", "r").read()
creator_private = open("Creator_private.key", "r").read()
creator = blockchain.Wallet('Creator', creator_public, creator_private)

miner_public = open("miner_public.key", "r").read()
miner_private = open("miner_private.key", "r").read()
miner = blockchain.Wallet('Miner', miner_public, miner_private)

chain = blockchain.Chain(creator)
transaction_list = list()
verified_transactions = list()
ledger = list()

@server.route('/transactions', methods = ['GET', 'POST'])
def transactions():
	if request.method == 'GET':
		block_index = request.values.get('start')

		if block_index:
			if int(block_index) == 0:
				block_index = int(block_index) + 1
			else:
				block_index = int(block_index)
			if block_index <= chain.getLatestBlock().index:
				return render_template('transaction_list.html',
					index = block_index,
					length = chain.getLatestBlock().index,
					chain = chain
				)
			else:
				return render_template('error.html')
		else:
			return render_template('transaction_list.html',
					index = 1,
					length = chain.getLatestBlock().index,
					chain = chain
				)

	elif request.method == 'POST':
		data = json.loads(request.get_data().decode('UTF-8'))

		for i in range(len(data['transactions'])):
			sender_public = data['transactions'][i]['sender']
			receiver_public = data['transactions'][i]['receiver']
			operation = data['transactions'][i]['operation']
			timestamp = data['transactions'][i]['timestamp']
			t_hash = data['transactions'][i]['t_hash']

			sender = blockchain.Wallet('A', sender_public, "")
			receiver = blockchain.Wallet('B', receiver_public, "")

			transaction = blockchain.Transaction(receiver, operation, sender, timestamp, t_hash)
			transaction_list.append(transaction)
		
		i = 1

		for transaction in transaction_list:
			if miner.public not in ledger:
				ledger.append(miner.public)
			if transaction.sender not in ledger:
				ledger.append(transaction.sender)
			if transaction.receiver not in ledger:
				ledger.append(transaction.receiver)

			amount = str(transaction.operation)

			if(chain.verifyTransaction(transaction) and chain.checkBal(transaction.sender, verified_transactions, transaction)):
				verified_transactions.append(transaction)

			i += 1

		if(len(verified_transactions) > 0):
			l = len(verified_transactions)
			chain.mine_block(verified_transactions, miner)

		return "Number of Accepted Transaction: {0}\n".format(l)

@server.route('/transactions/<int:ID>')
def go_to(ID):
	if ID <= chain.getLatestBlock().index:
		return render_template('transaction_list.html',
			index = ID,
			length = ID,
			chain = chain
		)
	else:
		return render_template('error.html')

@server.route('/peers', methods = ['GET', 'POST'])
def peers():
	if request.method == 'GET':
		peer_mode = request.values.get('mode')

		if peer_mode == 'json':
			return open("peers.json", "r").read()
		elif peer_mode == None:
			return render_template('peers.html',
					ledger = ledger,
					length = len(ledger)
				)

	elif request.method == 'POST':
		data = json.loads(request.get_data().decode('UTF-8'))

		data['peer']

@server.route('/heartbeat')
def heartbeat():
	return "alive", 200

# Threading
server.run(port = 8001)