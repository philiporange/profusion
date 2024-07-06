import json
import math
from typing import Any
import zipfile

from . import __version__, __program__
from . import Bloom, BloomException


BIN_SIZE = 255
CAPACITY = 1e6
ERROR_RATIO = 1e-15


class CountingBloom(Bloom):
    """Counting Bloom filter implementation"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.type = "counting bloom"
        self.path = kwargs.get("path", None)
        self.bin_size = kwargs.get("bin_size", BIN_SIZE)
        self.capacity = kwargs.get("capacity", CAPACITY)
        self.error_ratio = kwargs.get("error_ratio", ERROR_RATIO)

        if self.bin_size <= 0:
            raise BloomException("bin_size must be > 0")

        if self.path is not None and self.path != "":
            self.load(self.path)
        else:
            self._init_counting_bloom()

    def _init_counting_bloom(self) -> None:
        """Initialize new Counting Bloom filter properties"""
        self.capacity = int(self.capacity)
        self.hashes = self._hashes(self.error_ratio)
        bins = self.hashes * self.capacity / math.log(2)
        self.bins = int(math.ceil(bins))
        self.bin_bytes = len(self._int2bytes(self.bin_size))
        self.bytes = self.bin_bytes * self.bins
        self.bf = bytearray(b"\0" * self.bytes)

    def add(self, s: str, amount: int = 1) -> bool:
        """Add amount to element"""
        result = True
        for index in self._indexes(s):
            if not self._increment_bin(index, amount):
                result = False

        return result

    def value(self, s: str) -> int:
        """Get value of element"""
        return min(self._bin(index) for index in self._indexes(s))

    def check(self, s: str, trigger: int = -1) -> bool:
        """Check if value of element is at least trigger"""
        if not 0 <= trigger <= self.bin_size:
            trigger = self.bin_size
        else:
            trigger = trigger
        return self.value(s) >= trigger

    def save(self, path: str = None) -> None:
        if path is not None:
            self.path = path

        if self.path is None:
            raise BloomException("No path specified")

        metadata = {
            "version": __version__,
            "program": __program__,
            "type": self.type,
            "capacity": int(self.capacity),
            "hashes": int(self.hashes),
            "error_ratio": float(self.error_ratio),
            "bin_size": int(self.bin_size),
            "bins": self.bins,
            "bin_bytes": self.bin_bytes,
            "bytes": self.bytes,
        }

        with zipfile.ZipFile(self.path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("metadata.json", json.dumps(metadata))
            zf.writestr("bf.bin", self.bf)

    def load(self, path: str) -> None:
        if not path:
            raise BloomException("No path specified")

        with zipfile.ZipFile(path, "r") as zf:
            try:
                metadata = json.loads(zf.read("metadata.json"))
                if metadata["type"] != self.type:
                    raise BloomException(f"Invalid type: {metadata['type']}")

                self.hashes = int(metadata["hashes"])
                self.capacity = int(metadata["capacity"])
                self.error_ratio = float(metadata["error_ratio"])
                self.bin_size = int(metadata["bin_size"])
                self.bins = int(metadata["bins"])
                self.bin_bytes = int(metadata["bin_bytes"])
                self.bytes = int(metadata["bytes"])

                self.bf = bytearray(zf.read("bf.bin"))
            except KeyError as e:
                raise BloomException(f"Invalid file format: missing {e}")

        self.path = path

    def __contains__(self, s: str) -> bool:
        return self.check(s)

    def _indexes(self, s: str) -> list:
        """Get indexes of element"""
        for i in range(self.hashes):
            yield self._hash(s, i) % self.bins

    def _bin(self, index: int) -> int:
        """Get value of bin"""
        start = index * self.bin_bytes
        end = start + self.bin_bytes
        return self._bytes2int(self.bf[start:end])

    def _set_bin(self, index: int, value: int) -> None:
        """Set value of bin"""
        start = index * self.bin_bytes
        end = start + self.bin_bytes
        bytes_value = self._int2bytes(value, self.bin_bytes)
        self.bf[start:end] = bytes_value

    def _increment_bin(self, index: int, amount: int) -> bool:
        """Increase value of bin by amount, return True if full"""
        value = self._bin(index)
        if value == self.bin_size:
            return True
        value = min(value + amount, self.bin_size)
        self._set_bin(index, value)
        return value == self.bin_size

    def _decrement_bin(self, index: int, amount: int) -> bool:
        """Decrease value of bin by amount, return True if empty"""
        value = self._bin(index)
        if value == 0:
            return True
        value = max(value - amount, 0)
        self._set_bin(index, value)
        return value == 0

    @staticmethod
    def _int2bytes(i: int, _bytes: int = -1) -> bytes:
        """Transform integer to bytes representation (big endian)"""
        s = i.to_bytes((i.bit_length() + 7) // 8, byteorder="big")
        return s.rjust(_bytes, b"\0") if _bytes > -1 else s

    @staticmethod
    def _bytes2int(s: bytes) -> int:
        """Transform bytes to integer representation (big endian)"""
        return int.from_bytes(s, byteorder="big")
