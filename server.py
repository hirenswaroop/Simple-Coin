import socket
import threading
import encryption
import blockchain
import requests
import ledger
import random
import json
import sys
import time

# Peer to peer server with attributes:
# IP address, Port, Broadcast socket, and Listen socket
class P2P():
	def __init__(self):
		self.ip_address = socket.gethostbyname(socket.gethostname())
		self.port = random.randint(5002, 6000)
		self.peer_broadcast = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.peer_listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		self.peer_broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.peer_broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

		self.peer_broadcast.bind(('', self.port))
		self.peer_listen.bind(('', 5001))

	# Broadcasts the json {coin:simplecoin} to all
	# network interfaces on the network
	def broadcast(self):
		message = dict()
		message['coin'] = 'simplecoin'
		message = json.dumps(message)
		time.sleep(1)

		while 1:
			self.peer_broadcast.sendto(message.encode(), ('<broadcast>', 5001))
			print('Message Broadcasted')

			# Waits 300 second in between broadcasts
			time.sleep(300)

	# Listens for broadcasts and sends peer data to
	# sender of broadcast
	def listen(self):
		new_peer = ledger.Peer('{0}:{1}'.format(self.ip_address, self.port))

		while 1:
			# Waits until a message is received
			msg, addr = self.peer_listen.recvfrom(2048)
			if addr[0] != self.ip_address:
				message = json.loads(msg.decode())

				# Verifies that the broadcast is correct
				if message['coin'] == 'simplecoin':
					print('Message From {0}\n'.format(addr))
					data_dict = dict()

					plain_nonce = random.randint(1, 1 << 24)
					nonce = encryption.encryptWithKey(new_peer.wallet.private, str(plain_nonce))

					data_dict['public_key'] = new_peer.wallet.public
					data_dict['nonce'] = nonce
					data_dict['host'] = new_peer.host

					# Initializes new peer post request data
					json_arg = {
						'new_peer' : data_dict
					}
					payload = json.dumps(json_arg)

					url = 'http://{0}:{1}/peers'.format(addr[0], addr[1])
					peer_list_data = requests.post(url, json=payload)

					if peer_list_data.text != '':
						peer_list_data = json.loads(peer_list_data.text)
						new_nonce = peer_list_data['nonce']
						new_nonce = encryption.decryptWithKey(new_peer.wallet.private, new_nonce)

						# Verifies nonce is correct
						if int(new_nonce) == plain_nonce:
							# Initializes peer list post request data
							json_arg = {
								'peer_list' : peer_list_data['peer_list']
							}
							payload = json.dumps(json_arg, indent=4, cls=blockchain.ChainEncoder)
							post_req = requests.post(url, json=payload)
						else:
							print('Peers Not Registered: Invalid Nonce')
					else:
						print('Peer {0}:{1} Not Registered: Already in Ledger'.format(addr[0], addr[1]))

	# Multithreads the broadcast and listen functions
	def multithread(self):
		# Initializes the broadcast thread
		t_broadcast = threading.Thread(target=self.broadcast)

		# Initializes the listen thread
		t_listen = threading.Thread(target=self.listen)

		# Sets the threads to background processes
		t_broadcast.daemon = True
		t_listen.daemon = True

		# Starts the threads
		t_broadcast.start()
		t_listen.start()
		
		# Makes the threads run forever
		t_broadcast.join()
		t_listen.join()