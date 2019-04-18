from flask import Flask
from flask import render_template
from flask import request
from flask import send_file
from sqlite3 import Error
import blockchain
import sqlite3
import encryption
import keyGeneration
import json
import _thread
import threading
import requests
import random
import hashlib
import server
import sys
import time

# Python Version Check
if sys.version_info < (3,5):
	print('Python version detected: ' + str(sys.version_info[0]) + '.'+str(sys.version_info[1]))
	print('Python version required: 3.5 or higher')
	sys.exit(1)

# Creates the http server
ledger = Flask(__name__)

# Creates the keys and wallet for the creator of the blockchain
creator_public = open('Creator_public.key', 'r').read()
creator_private = open('Creator_private.key', 'r').read()
creator_wallet = blockchain.Wallet('Creator', creator_public, creator_private)

# Creates the blockchain object initialized with the creator's wallet
chain = blockchain.Chain(creator_wallet)
peer_list = list()
peer_lock = threading.Lock()

# Contains a host consisting of an ip address
# and a port and a wallet
class Peer():
	def __init__(self, host, wallet = None):
		self.host = host
		host = host.split(':')

		self.ip_address = host[0]
		self.port = int(host[1])
		hasWallet = False

		# If a wallet is passed into the constructor
		# wallet is set as the specified wallet
		if wallet:
			self.wallet = wallet
		else:
			for peer in peer_list:
				if peer.host == self.host:
					self.wallet = peer.wallet
					hasWallet = True
				else:
					continue

			# If a wallet is not passed into the constructor
			# public and private keys are generated
			if not hasWallet:
				time.sleep(2)
				print('Generating Keys...')
				public, private = keyGeneration.genKeys()
				self.wallet = blockchain.Wallet('Peer ' + self.host, public, private)

	# Author: Mr. Sea
	# Returns the json representation of the peer
	def toJSON(self):
		json = {
			'__type__': self.__class__.__name__,
			'host': self.host,
			'public': self.wallet.public
		}
		return json

	# Author: Mr. Sea
	# Converts json to a string
	def __repr__(self):
		return json.dumps(self, cls=blockchain.ChainEncoder)

# HTTP Server Routing
# Handles the /transactions route for both GET and POST requests
@ledger.route('/transactions', methods = ['GET', 'POST'])
def transactions():
	# Handles the GET request route
	if request.method == 'GET':
		block_index = request.values.get('start')

		# If the index is valid the HTML template is returned
		# Otherwise, an error page is returned with a 404 code
		if block_index:
			try:
				block_index = int(block_index)
			except:
				return render_template('error.html'), 404
			if block_index >= 0 and block_index <= chain.getLatestBlock().index:
				return render_template('transaction_list.html',
					index = block_index,
					length = chain.getLatestBlock().index,
					chain = chain
				)
			else:
				return render_template('error.html'), 404
		else:
			return render_template('transaction_list.html',
					index = 0,
					length = chain.getLatestBlock().index,
					chain = chain
				)

	# Handles the POST request route
	elif request.method == 'POST':
		data = json.loads(request.get_data().decode('UTF-8'))
		transaction_list = list()
		verified_transactions = list()

		for transaction in data['transactions']:
			sender_public = transaction['sender']
			receiver_public = transaction['receiver']
			operation = transaction['operation']
			timestamp = transaction['timestamp']
			t_hash = transaction['t_hash']

			# Initializes a wallet for both the sender and receiver
			sender_wallet = blockchain.Wallet('', sender_public, '')
			receiver_wallet = blockchain.Wallet('', receiver_public, '')

			# Initializes a peer object for both the sender and receiver
			sender = Peer('{0}:{1}'.format('127.0.0.1', random.randrange(5002, 6000)), sender_wallet)
			receiver = Peer('{0}:{1}'.format('127.0.0.1', random.randrange(5002, 6000)), receiver_wallet)
			
			# Sets the name of the peer in the wallet of the peer
			sender.wallet.name = 'Peer {0}'.format(sender.host)
			receiver.wallet.name = 'Peer {0}'.format(receiver.host)

			# If the sender is not in the peer list, it is added
			if not any(x.wallet.public == sender_wallet.public for x in peer_list):
				peer_lock.acquire(blocking=True)
				peer_list.append(sender)
				peer_lock.release()

			# If the receiver is not in the peer list, it is added
			if not any(x.wallet.public == receiver_wallet.public for x in peer_list):
				peer_lock.acquire(blocking=True)
				peer_list.append(receiver)
				peer_lock.release()

			# Creates a transaction with the correct parameters and
			# adds it to a list of transactions
			transaction = blockchain.Transaction(receiver.wallet, operation, sender.wallet, timestamp, t_hash)
			transaction_list.append(transaction)
		
		# Verifies each transaction is valid and adds them to a block
		for transaction in transaction_list:
			amount = str(transaction.operation)

			if(chain.verifyTransaction(transaction) and chain.checkBal(transaction.sender, verified_transactions, transaction)):
				verified_transactions.append(transaction)

		if(len(verified_transactions) > 0):
			chain.mine_block(verified_transactions, sender_wallet)

		return ''

# Handles the /transactions/ID GET route
@ledger.route('/transactions/<ID>')
def go_to(ID):
	# Checks if the ID given is an integer and
	# returns an error page and 404 if it isn't
	try:
		ID = int(ID)
	except:
		return render_template('error.html'), 404

	# Checks to make sure the ID is within the bounds of the blockchain
	if ID >= 0 and ID <= chain.getLatestBlock().index:
		return render_template('transaction_list.html',
			index = ID,
			length = ID,
			chain = chain
		)
	else:
		return render_template('error.html'), 404

# Handles the /peers route for both GET and POST requests
@ledger.route('/peers', methods = ['GET', 'POST'])
def peers():
	if request.method == 'GET':
		peer_mode = request.values.get('mode')

		# Checks if the mode is json and returns a string
		# representation of the peer list
		if peer_mode == 'json':
			peers_json = {
				'peers' : peer_list
			}
			peers_json = json.dumps(peers_json, indent=4, cls=blockchain.ChainEncoder)

			return peers_json

		# Checks if the mode is not entered which means
		# the list of all peers will be returned in HTML format
		elif peer_mode == None:
			if len(peer_list) > 0:
				return render_template('peers.html',
					ledger = peer_list,
					length = len(peer_list)
				)
			else:
				return 'Peer List Empty'
		else:
			return render_template('error.html'), 404

	elif request.method == 'POST':
		data = json.loads(json.loads(request.get_data().decode('UTF-8')))

		request_host_hash = hashlib.sha256()
		request_host_hash.update(request.host.encode())
		request_host_hash = request_host_hash.hexdigest()

		is_new = True

		try:
			new_data = data['new_peer']
		except:
			is_new = False

		# The data being sent is from a peer not in the peer list
		if is_new:
			peer_public = data['new_peer']['public_key']
			nonce = data['new_peer']['nonce']
			peer_host = data['new_peer']['host']

			# Initializes the new peer
			nonce = encryption.decryptWithKey(peer_public, str(nonce))
			peer_wallet = blockchain.Wallet('Peer ' + peer_host, peer_public, '')
			new_peer = Peer(peer_host, peer_wallet)
			duplicate = is_duplicate(new_peer)

			# Verifies the new peer is not already in peer list
			if not duplicate:
				# Locks access to peer_list and adds the new peer
				peer_lock.acquire(blocking=True)
				peer_list.append(new_peer)
				peer_lock.release()
				nonce = encryption.encryptWithKey(peer_public, str(nonce))

				# Initializes the request data to be returned to server
				req_data = {
					'peer_list' : peer_list,
					'nonce' : nonce
				}
				payload = json.dumps(req_data, indent=4, cls=blockchain.ChainEncoder)
				url = 'http://{0}/peers?mode=json'.format(new_peer.host)

				# Gets the peer list of the new peer
				response = requests.get(url)
				new_peer_list_json = json.loads(response.content)

				update_peer_list(request_host_hash, new_peer_list_json)

				print('Peer {0} Registered'.format(new_peer.host))
				return payload

			else:
				print('Peer {0} Not Registered: Already in Ledger'.format(new_peer.host))

		# The data being sent is from a peer already in the peer list
		elif not is_new:
			for registered_peer in data['peer_list']:
				host = registered_peer['host']
				public_key = registered_peer['public']

				# Initializes the new peer
				peer_wallet = blockchain.Wallet('Peer {0}'.format(host), public_key, '')
				new_peer = Peer(host, peer_wallet)
				duplicate = is_duplicate(new_peer)

				# Verifies the new peer is not already in peer list
				if not duplicate:
					# Locks access to peer_list and adds the new peer
					peer_lock.acquire(blocking=True)
					peer_list.append(new_peer)
					peer_lock.release()

					# Sends GET request to new peer asking for their peer list
					url = 'http://{0}/peers?mode=json'.format(new_peer.host)

					# Gets the peer list of the new peer
					response = requests.get(url)
					new_peer_list_json = json.loads(response.content)

					update_peer_list(request_host_hash, new_peer_list_json)

					print('Peer {0} Registered'.format(new_peer.host))
				else:
					print('Peer {0} Not Registered: Already in Ledger'.format(new_peer.host))

		else:
			print('Peers Not Registered: Invalid Data')

		return ''

# Handles the /heartbeat route for GET requests
@ledger.route('/heartbeat')
def heartbeat():
	return 'alive', 200

# Handles all extraneous routes
@ledger.route('/<path:path>')
def catch_all(path):
	return render_template('error_page.html'), 404

# Checks is the new peer is already in the peer list
def is_duplicate(new_peer):
	# Creates a hash to represent the new peer
	new_host_hash = hashlib.sha256()
	new_host_hash.update(new_peer.host.encode())
	new_host_hash = new_host_hash.hexdigest()
	temp_hash_list = list()

	# Creates a list of hashes to represent all peers in peer list
	for peer in peer_list:
		temp_hash = hashlib.sha256()
		temp_hash.update(peer.host.encode())
		temp_hash = temp_hash.hexdigest()
		temp_hash_list.append(temp_hash)

	if new_host_hash not in temp_hash_list:
		return False
	else:
		return True

# Contacts each peer in the peer list at 
# /heartbeat route every 60 seconds and
# removes them if they are inactive
def contact_peers():
	time.sleep(1)

	while 1:
		for peer in peer_list:
			# Ignores creator
			if peer.host == '127.0.0.1:5000':
				continue
			url = 'http://{0}/heartbeat'.format(peer.host)

			# Checks to see if the peer is still on the network
			try:
				status = requests.get(url)
			except:
				peer_list.remove(peer)
				print('Peer {0} Removed From Ledger: Inactive'.format(peer.host))

			# Checks the status code returned by the GET
			# request and removes the peer if the code is 404
			if status.status_code == 404:
				peer_list.remove(peer)
				print('Peer {0} Removed From Ledger: Inactive'.format(peer.host))

		time.sleep(60)

# Updates the peer list with GET requests data
def update_peer_list(request_host_hash, json_data):
	for peer in json_data['peers']:
		peer_hash = hashlib.sha256()
		peer_hash.update(peer['host'].encode())
		peer_hash = peer_hash.hexdigest()

		if peer_hash != request_host_hash:
			new_peer_wallet = blockchain.Wallet('Peer {0}'.format(peer['host']), peer['public'], '')
			new_peer = Peer(peer['host'], new_peer_wallet)
			duplicate = is_duplicate(new_peer)

			# Verifies that the new peer is not already in the peer list
			if not duplicate:
				# Locks access to peer_list and adds the new peer
				peer_lock.acquire(blocking=True)
				peer_list.append(new_peer)
				peer_lock.release()

				print('Peer {0} Registered'.format(new_peer.host))
			else:
				print('Peer {0} Not Registered: Already in Ledger'.format(new_peer.host))

# Runs flask server and peer to peer server
if __name__ == '__main__':
	# Creates peer to peer server
	p2p = server.P2P()

	# Threading
	# Initializes http server thread
	t_ledger = threading.Thread(target=ledger.run, args=(p2p.ip_address, p2p.port))

	# Initializes peer to peer server thread
	t_p2p = threading.Thread(target=p2p.multithread)

	# Initializes heartbeat system thread
	t_contact = threading.Thread(target=contact_peers)

	# Sets the threads to background processes
	t_ledger.daemon = True
	t_p2p.daemon = True
	t_contact.daemon = True

	# Starts the threads
	t_ledger.start()
	t_p2p.start()
	t_contact.start()

	# Makes the threads run forever
	t_ledger.join()
	t_p2p.join()
	t_contact.join()
