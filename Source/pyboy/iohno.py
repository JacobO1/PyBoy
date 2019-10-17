import io

class BytesIOhNo(io.BytesIO):
	def __init__(self):
		super(BytesIOhNo, self).__init__()
		self.counter = 0
		self.byte = b'0'
		self.empty = 0  #Used to ensure that all write()-data has actually been written prior to a read() call
		self.BYTE_MAX = 255

	def write(self, data):
		if len(data) > 1:
			return sum([self.write(b) for b in data])
		else:
			if data == 0x00:
				self.counter += 1
				return 1
			else:
				if self.counter > 0:
					# Flush zeros
					rest = self.counter % self.BYTE_MAX
					for i in range(self.counter // self.BYTE_MAX):
						super().write(self.byte)
						super().write(self.BYTE_MAX.to_bytes(1, "little"))
					if (rest != 0):
						super().write(self.byte)
						super().write(rest.to_bytes(1, "little"))
					self.counter = 0

				# write single byte
				return super().write(data)

	def read(self, amount):
		if amount > 1:
			return sum([self.read(1) for _ in range(amount)])
		else:
			if self.counter != 0:
				self.counter -= 1
				return self.byte
			else:
				self.byte = super().read(amount)
				if self.byte == 0x00:
					self.counter = super().read(amount)
				return self.byte
