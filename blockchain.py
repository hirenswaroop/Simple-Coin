# Author: Hiren Swaroop

# Allow Python 2 to work up to the python version check
from __future__ import print_function

import time
import hashlib
import encryption
import base64
import json
import sys
import copy

# Python Version Check
if sys.version_info < (3,5):
	print('Python version detected: ' + str(sys.version_info[0]) + '.'+str(sys.version_info[1]))
	print('Python version required: 3.5 or higher')
	sys.exit(1)

# Author: Mr. Sea
class ChainEncoder(json.JSONEncoder):
	def default(self, object):
		if hasattr(object, 'toJSON'):
			return object.toJSON()
		else:
			return json.JSONEncoder.default(self, object)

# Author: Mr. Sea
class ChainDecoder(json.JSONDecoder):
	def object_hook(self, obj):
		if '__type__' not in obj:
			return obj

		type = obj['__type__']
		if type == 'Transaction':
			obj.pop('__type__')

			rtn = Transaction.parseJSON(obj)
			return rtn
		
		return obj


# Defines a transaction consiting of
# the sender's and receiver's public
# keys, timestamp, and a hash signed
# by the sender
class Transaction:
	# Constructor for the transaction that sets
	# the sender and receiver public keys, the sender's
	# private key, operation, time, and hash of the
	# transaction
	def __init__(self, receiver, operation, sender = None, timestamp = None, t_hash = None):
		self.sender = None
		self.receiver = receiver.public
		self.operation = operation

		if timestamp != None:
			self.timestamp = timestamp
		else:
			self.timestamp = time.time()

		if sender != None:
			self.sender = sender.public

		if t_hash == None:
			self.t_hash = self.hash()

			if sender != None:
				self.t_hash = encryption.encryptWithKey(sender.private, self.t_hash)
			else:
				self.t_hash = encryption.encryptWithKey(receiver.private, self.t_hash)
		else:
			self.t_hash = t_hash

		self.verify()

	# Author: Mr. Sea
	# Signs the transaction if it isn't signed and checks hash
	def verify(self):
		# Unsign the hash if needed 
		unsigned_hash = self.t_hash

		if self.sender != None:
			unsigned_hash = encryption.decryptWithKey(self.sender, self.t_hash)
		else:
			# If the sender is the System then unsign it with the receiver's ID
			unsigned_hash = encryption.decryptWithKey(self.receiver, self.t_hash)

		if self.hash() != unsigned_hash:
			raise Exception('Hash Mismatch')
		
		if self.operation <= 0:
			raise Exception("Operation <= 0")

		return True

	# Hashes the transaction
	def hash(self):
		transaction = hashlib.sha256()
		if self.sender != None:
			transaction.update((str(self.sender)).encode())
		else:
			transaction.update('System'.encode())
		transaction.update((str(self.receiver)).encode())
		transaction.update((str(self.timestamp)).encode())
		transaction.update((str(self.operation)).encode())

		return transaction.hexdigest()
	
	# Author: Mr. Sea
	def toJSON(self):
		json = {
			"__type__": self.__class__.__name__,
		}
		json.update(self.__dict__)

		return json

	# Author: Mr. Sea
	@staticmethod
	def parseJSON(json):

		receiver = Wallet('', json['receiver'], '')
		sender = Wallet('', json['sender'], '')

		return Transaction(receiver, json['operation'], sender, 
								json['timestamp'], json['hash'])

	# Returns a String in JSON format
	def __repr__(self):
		return json.dumps(self, cls=ChainEncoder)


# Defines a block consisting of an index,
# data, timestamp, hash of current,
# block, hash of previous block,
# nonce, a hashing function, hash combining
# function, and a merkle root generation
# function
class Block:
	# Constructor for the block that sets the
	# index, time, data, previous and next blocks,
	# nonce, and the merkle root of the block
	def __init__(self, data, prev_block):
		self.index = 0
		self.timestamp = time.time()
		self.data = data
		self.currhash = None
		self.prevhash = None
		self.prev_block = prev_block
		self.next_block = None
		self.nonce = 0
		self.merkle_root = self.gen_Merkle_Root()

		if prev_block != None:
			self.index = prev_block.index + 1
			self.prevhash = prev_block.currhash

	# Hashes the block
	def hash(self):
		block = hashlib.sha256()
		block.update((str(self.index)).encode())
		block.update((str(self.timestamp)).encode())
		block.update((str(self.merkle_root)).encode())
		block.update((str(self.prevhash)).encode())
		block.update((str(self.nonce)).encode())

		return block.hexdigest()

	# Combines two hashes
	def hash_combine(self, hash1, hash2):
		combined_hash = hashlib.sha256()
		combined_hash.update((str(hash1)).encode())
		combined_hash.update((str(hash2)).encode())

		return combined_hash.hexdigest()

	# Generates the merkle root of the block
	# using the hashes of the transactions in
	# the block
	def gen_Merkle_Root(self):
		tempdata = self.data[:]
		i = 0

		while(not all(isinstance(i, str) for i in tempdata)):
			tempdata[i] = tempdata[i].hash()
			i += 1

		while(len(tempdata) != 1):
			if(len(tempdata) > 1):
				h1 = tempdata.pop(0)
				h2 = tempdata.pop(0)
				tempdata.append(self.hash_combine(h1, h2))
		return tempdata[0]

	# Author: Mr. Sea
	# Verifies the block by verifying transactions and checking Merkle Root
	def verify(self):
		block_id = 'Block {0}'.format(self.index)

		if self.hash() != self.currhash:
			raise Exception(block_id + 'Hash Mismatch')

		for idx, transaction in enumerate(self.data):
			try:
				transaction.verify()
			except Exception as err:
				raise Exception(block_id + 'Transaction {0}: {1}'.format(idx + 1, str(err)))

		if self.gen_Merkle_Root() != self.merkle_root:
			raise Exception('Merkle Root Mismatch')

		return True


	# Author: Mr. Sea
	def toJSON(self):
		jsonObject = {
			"__type__": self.__class__.__name__
		}
		jsonObject.update(self.__dict__)

		return jsonObject

	# Returns a JSON of the current block
	def __repr__(self):
		return json.dumps(self, cls=ChainEncoder)


# Defines a linked list of blocks
# and can append a block, verify
# the chain, calculate the balance
# of a user, verify a transaction,
# check the balance, and get the
# latest block
class Chain:
	difficutly = 2
	max_transactions = 256

	# Constructor for the block chain that creates the genesis block
	def __init__(self, creator):
		data = [Transaction(creator, 100)]
		self.genesis = Block(data, None)
		self.genesis.time = time.time()
		temphash = self.genesis.hash()
		while(len(temphash) - len(temphash.lstrip('0')) < self.difficutly):
			self.genesis.nonce += 1
			temphash = self.genesis.hash()
		self.genesis.currhash = self.genesis.hash()
		self.head = self.tail = self.genesis

	# Adds a block to the block chain and calculates the correct nonce
	def mine_block(self, data, miner):
		data.insert(0, Transaction(miner, 10))

		if(len(data) > self.max_transactions):
			data = data[:self.max_transactions]

		new_block = Block(data, self.tail)
		new_block.time = time.time()
		temphash = new_block.hash()

		while(len(temphash) - len(temphash.lstrip('0')) < self.difficutly):
			new_block.nonce += 1
			temphash = new_block.hash()

		self.tail.next_block = new_block
		self.tail = new_block
		new_block.currhash = new_block.hash()

	# Verifies the integrity of the chain by checking hashes
	def verify(self):
		block = copy.deepcopy(self.tail)

		while block.index != 0:
			try:
				block.verify()
			except Exception as err:
				raise Exception('Chain Verification Failure: {0}'.format(str(err)))

			for idx, transaction in enumerate(block.data):
				try:
					self.verifyTransaction(transaction)
				except Exception as err:
					raise Exception('Block {0}: Transaction {1}: {2}'.format(block.index, idx, str(err)))

			if block.prevhash != None:
				if block.prevhash != block.prev_block.currhash:
					raise Exception('Block {0}: Previous hash does not match the current hash'.format(block.index))
			else:
				if block != self.head:
					raise Exception('Block {0}: Previous hash missing'.format(block.index))

			block = block.prev_block

		return True, block.index

	# Calculates the balance of the id passed in as a parameter
	def calcBalance(self, user_id):
		iterBlock = copy.deepcopy(self.head)
		balance = 0

		while(iterBlock != None):
			t = iterBlock.data

			for i in t:
				amount = int(i.operation)

				if(amount < 0):
					continue
				if(i.sender == user_id):
					balance -= amount
				elif(i.receiver == user_id):
					balance += amount

			iterBlock = iterBlock.next_block
		return balance

	# Verifies that a transaction is greater than 0 and the balance after the transaction
	# is valid
	def verifyTransaction(self, transaction):
		operation = int(transaction.operation)
		b = self.calcBalance(transaction.sender)
		if(operation > 0 and b > operation):
			return True
		else:
			return False

	# Makes sure the user has not overspent coins
	def checkBal(self, userId, verified_transactions, unverified_transaction):
		b = self.calcBalance(userId)
		for i in verified_transactions:
			if(i.sender == userId):
				b -= i.operation
		if(b - unverified_transaction.operation < 0):
			return False
		else:
			return True

	# Gets block at specified index
	def getBlock(self, index):
		iterBlock = copy.deepcopy(self.head)

		while(iterBlock != None):
			if iterBlock.index == index:
				return iterBlock
			else:
				iterBlock = iterBlock.next_block

	# Gets the tail of the linked list
	def getLatestBlock(self):
		return self.tail

# Create a wallet with Base64 encoded strings or with 
# public and private being tuples with numbers.  If tuples
# are used then the value passed for 'n' is ignored.
class Wallet:
	def __init__(self, realname, public, private, n = ""):
		if realname == None or len(realname.strip()) == 0:
			realname = ""

		if isinstance(public, tuple):
			n = encryption.intToBase64String(public[1])
			public = encryption.intToBase64String(public[0])

		if isinstance(private, tuple):
			n = encryption.intToBase64String(private[1])
			private = encryption.intToBase64String(private[0])
			

		self.name = realname
		self.public = public + n
		self.private = private + n
	
	# Author: Mr. Sea
	def toJSON(self):
		json = {
			"__type__": self.__class__.__name__
		}
		json.update(self.__dict__)
		return json

	# Author: Mr. Sea
	def __repr__(self):
		return json.dumps(self, cls=ChainEncoder)


# if __name__ == '__main__':
# 	names = ['A', 'B', 'Miner']
# 	keys = dict()

# 	for person in names:
# 		pubKey, n = encryption.load(person + '_public.key')
# 		privKey, n = encryption.load(person + '_private.key')

# 		pubKey = encryption.intToBase64String(pubKey)
# 		privKey = encryption.intToBase64String(privKey)
# 		n = encryption.intToBase64String(n)

# 		keys[person] = Wallet(person, pubKey, privKey, n)

# 	creator = keys['A']

# 	transaction_pool = [list()]
# 	verified_transactions = list()
# 	ledger = list()
# 	c = Chain(creator)

# 	j = 1
# 	for transaction_list in transaction_pool:
# 		i = 1
# 		for transaction in transaction_list:
# 			if keys['Miner'].public not in ledger:
# 				ledger.append(keys['Miner'].public)
# 			if transaction.sender not in ledger:
# 				ledger.append(transaction.sender)
# 			if transaction.receiver not in ledger:
# 				ledger.append(transaction.receiver)
# 			amount = str(transaction.operation)
# 			if(c.verifyTransaction(transaction) and c.checkBal(transaction.sender, verified_transactions, transaction)):
# 				print("Transaction " + str(i) + " (Amount: " + amount + "): User " + str(ledger.index(transaction.sender)) + " -> User " + str(ledger.index(transaction.receiver)) + " Accepted")
# 				verified_transactions.append(transaction)
# 			else:
# 				print("Transaction " + str(i) + " (Amount: " + amount + "): User " + str(ledger.index(transaction.sender)) + " -> User " + str(ledger.index(transaction.receiver)) + " Declined")
# 			i += 1
# 		if(len(verified_transactions) > 0):
# 			j += 1
# 			l = len(verified_transactions)
# 			verified_transactions.insert(0, Transaction(keys['Miner'], 10))
# 			c.mine_block(verified_transactions)
# 			verified_transactions = list()
# 			print("Mining Block " + str(j - 1) + "...")
# 			print("(<" + str(c.getLatestBlock().nonce) + ">, <" + str(c.getLatestBlock().currhash) + ">)")

# 	# Chain verification
# 	print("\nChain Verification...")

# 	b, i = c.verify()
# 	if(b):
# 		print("Verification True")
# 		for user in ledger:
# 			print("Amount in User " + str(ledger.index(user)) + "'s Wallet:", c.calcBalance(user))
# 	else:
# 		print("Verification False")
# 		print("Invalid block at index:", i)
