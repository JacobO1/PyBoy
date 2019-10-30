import io
import pdb

class BytesIOhNo():
	def __init__(self):
		self._buffer = io.BytesIO()
		self.counter = 0
		self.byte = b'\x00'
		self.empty = b'\x00'
		self.BYTE_MAX = 255

	def seek(self, profiler):
		self._buffer.seek(profiler)

	def flush(self):
		if self.counter > 0:
			rest = self.counter % self.BYTE_MAX
			for i in range(self.counter // self.BYTE_MAX):
				self._buffer.write(self.byte)
				self._buffer.write(self.BYTE_MAX.to_bytes(1, "little"))
			if (rest != 0):
				self._buffer.write(self.byte)
				self._buffer.write(rest.to_bytes(1, "little"))
		self.counter = 0

	def write(self, data):
		if len(data) > 1:
			return sum([self.write(hex(b)) for b in data])
		else:
			if data == b'\x00':
				self.counter += 1
				return 1
			else:
				self.flush()
				return self._buffer.write(data)

	def read(self, amount):
		if amount > 1:
			return sum([self.read(1) for _ in range(amount)])
		else:
			if self.counter > 0:
				self.counter -= 1
				return b'\x00'
			else:
				self.byte = self._buffer.read(amount)
				if self.byte == b'\x00':
					self.counter = int.from_bytes(self._buffer.read(amount), "little")
					self.counter -= 1
				assert len(self.byte) != 0
				return self.byte
