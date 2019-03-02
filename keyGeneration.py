import random
import base64
import math
import time

# Gets the range of values from start to stop by step
def yRange (start, stop, step):
	while start < stop:
		yield start
		start += step

# Generates a random prime of numBits bits in size
def getPrime(numBits):
	upper = 1 << (numBits + 1)
	lower = 1 << (numBits)

	num = random.randrange(lower, upper, 1)

	# Checks if num is prime
	def isPrime(num):
		if (num == 2):
			return True

		if not num & 1:
			return False

		return pow(2, num - 1, num) == 1

	while not isPrime(num):
		num += 2

		while num.bit_length() > numBits:
			num = num // 2
			if (not num & 1) and (num != 2):
				num += 1
	return num

# Finds the greatest common denominator between x and y
def gcd(x, y):
	while (y):
		x, y = y, x % y

	return x

# Finds a value d where e * d = 1 (mod(tn))
def egcd(tn, e):
	temptn = tn
	x, y, u, v = 0, 1, 1, 0
	while tn != 0:
		q, r = e // tn, e % tn
		m, n = x - u * q, y - v * q
		e, tn, x, y, u, v = tn, r, u, v, m, n

	if (y < 0):
		y = y % temptn
	return y

# Encodes a number in base 64
def base64encode(num):
	temp = base64.b64encode(num.to_bytes(math.ceil(num.bit_length() / 8), 'little'))
	return temp

def genKeys(name):
	p = getPrime(2048)
	q = getPrime(2048)
	n = p * q
	tn = (p - 1) * (q - 1)
	e = 0
	while True:
		e = random.randrange(1 << 3000, tn, 1)
		if (gcd(e, tn) != 1):
			continue
		break
	d = 0
	d = egcd(tn, e)

	eb64 = str(base64encode(e).decode())
	nb64 = str(base64encode(n).decode())
	db64 = str(base64encode(d).decode())

	puKey = eb64 + nb64
	prKey = db64 + nb64

	# puKey = open("{0}_public.key".format(name), "w")
	# puKey.write(eb64 + nb64)

	# prKey = open("{0}_private.key".format(name), "w")
	# prKey.write(db64 + nb64)

	return puKey, prKey