import io
import struct
import ctypes


class BinaryReader:
    def __init__(self, path=None, buffer=None):
        if path is not None:
            with open(path, 'rb') as f:
                self._buffer = io.BytesIO(f.read())
        elif buffer is not None:
            if isinstance(buffer, bytes):
                self._buffer = io.BytesIO(buffer)
            elif isinstance(buffer, bytearray):
                self._buffer = io.BytesIO(bytes(buffer))
            elif isinstance(buffer, io.BytesIO):
                self._buffer = buffer
            else:
                raise ValueError("Buffer must be bytes, bytearray or BytesIO")
        else:
            raise ValueError("Either path or buffer must be specified")

    def read_byte(self):
        return self._buffer.read(1)[0]

    def read_bytes(self, length: int):
        return self._buffer.read(length)

    def read_uleb128(self) -> int:
        result = 0
        shift = 0
        while True:
            byte = self.read_byte()
            result |= (byte & 0x7f) << shift
            if byte & 0x80 == 0:
                break
            shift += 7
        return result

    def read_string(self):
        length = self.read_uleb128()
        return self._buffer.read(length).decode('utf-8')

    def read_float(self) -> float:
        return struct.unpack('f', self._buffer.read(4))[0]

    def read_double(self) -> float:
        return struct.unpack('d', self._buffer.read(8))[0]

    def read_sleb128(self) -> int:
        value = self.read_uleb128()
        sign = value & 1
        value >>= 1
        return value if sign == 0 else ctypes.c_int64(~(value - 1)).value

    def read_bool(self) -> bool:
        return self.read_byte() != 0

    def read_b_uint(self) -> int:
        return struct.unpack('>I', self._buffer.read(4))[0]

    def read_b_int(self) -> int:
        return struct.unpack('>i', self._buffer.read(4))[0]

    def read_b_ulong(self) -> int:
        return struct.unpack('>Q', self._buffer.read(8))[0]

    def read_b_long(self) -> int:
        return struct.unpack('>q', self._buffer.read(8))[0]

    def read_hash(self) -> int:
        value = ctypes.c_int(self.read_uleb128()).value
        return ctypes.c_int((value & 1) ^ (value >> 1)).value

    def read_array_len(self) -> int:
        return self.read_uleb128() // 2

    def read_all(self) -> bytes:
        self.reset()
        return self._buffer.read()

    def skip(self, length: int):
        self._buffer.seek(length, io.SEEK_CUR)

    def reset(self):
        self._buffer.seek(0)
