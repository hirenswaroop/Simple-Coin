import base64
import math
import sys

# Loads and returns the keys from a file
# Returns: a tuple of the (Key, N) as integers
def load(filename):
	file = open(filename, 'r')
	str = file.read()
	file.close()

	key = str[0:len(str)//2]
	n = str[len(str)//2:]

	key = base64StringToInt(key)
	n = base64StringToInt(n)

	return (key,n)

#Converts a Base64 String to an integer
def base64StringToInt(s):
	return int.from_bytes(base64.b64decode(s.encode()), 'little')

#Converts an integer to a Base64 String
def intToBase64String(n):
	return base64.b64encode(n.to_bytes(math.ceil(n.bit_length() / 8), 'little')).decode()

# Encrypts a message and returns the cipher text
def encrypt(e, n, msg):
	m = int.from_bytes(msg.encode(), 'little')
	c = pow(m, e, n)
	b64m = base64.b64encode(c.to_bytes(math.ceil(c.bit_length() / 8), 'little'))
	return b64m.decode()

# Decrypts a cipher text and returns the message
def decrypt(d, n, msg):
	c = base64.b64decode(msg.encode())
	c = int.from_bytes(c, 'little')
	m = pow(c, d, n)

	msg = m.to_bytes(math.ceil(m.bit_length() / 8), 'little')
	msg = msg.decode()
	return msg


# Encrypts msg using a complete Base64 key
def encryptWithKey(s, msg):
	key = s[0:len(s) // 2]
	n = s[len(s) // 2:]

	return encrypt(base64StringToInt(key), base64StringToInt(n), msg)

# Decrypts msg using a complete Base64 key
def decryptWithKey(s, msg):
	key = s[:len(s) // 2]
	n = s[len(s) // 2:]

	return decrypt(base64StringToInt(key), base64StringToInt(n), msg)

def main():
	try:
		puKey = open("public.key", "r")
		prKey = open("private.key", "r")

		public = puKey.readline()
		private = prKey.readline()

		e, n = public[:len(public) // 2], public[len(public) // 2:]
		d = private[:len(private) // 2]
		e = base64decode(e)
		n = base64decode(n)
		d = base64decode(d)

		input2 = sys.argv[1]
		if (input2 == "-h"):
			print("-e for encrypt\n-d for decrypt\n-s for sign")
			print("example input: -e input_file output_file")
			exit()

		input_file = sys.argv[2]
		with open(input_file, "r") as file:
			m = file.read()
			if not m:
				print("Error: File is empty")
				exit()

			if (input2 == "-e"):
				msg = encrypt(e, n, m)
			elif (input2 == "-d"):
				msg = decrypt(d, n, m)
			elif (input2 == "-s"):
				msg = encrypt(d, n, m)
			else:
				print("Invalid parameters use -h for help")
				exit()

			output_file = open(sys.argv[3], "w")
			output_file.write(str(msg))
	except Exception:
		print("Invalid parameters use -h for help")

if __name__ == "__main__":
	main()