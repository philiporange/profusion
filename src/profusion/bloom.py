import binascii
import gzip
import json
import math
import os
from typing import Any, Tuple

import mmh3

from . import __version__, __program__


CAPACITY = 1e6
ERROR_RATIO = 1e-15


class BloomException(Exception):
    pass


class Bloom:
    """Bloom filter implementation"""

    def __init__(self, **kwargs: Any) -> None:
        self.type = "bloom"
        self.capacity = kwargs.get("capacity", CAPACITY)
        self.error_ratio = kwargs.get("error_ratio", ERROR_RATIO)
        self.path = kwargs.get("path", None)

        # Validate initialization parameters
        if self.capacity <= 0:
            raise BloomException("capacity must be > 0")
        if not 0 < self.error_ratio < 1:
            raise BloomException("error_ratio must be between 0 and 1")

        if self.path is not None and os.path.isfile(self.path):
            self.load(self.path)
        else:
            self._init_bloom()

    def _init_bloom(self) -> None:
        """Initialize new Bloom filter properties"""
        self.capacity = int(self.capacity)
        self.hashes = self._hashes(self.error_ratio)
        bins = self.hashes * self.capacity / math.log(2)
        self.bins = int(math.ceil(bins))
        self.bytes = (self.bins // 8) + 1
        self.bf = bytearray(b"\0" * self.bytes)

    def add(self, s: str) -> None:
        """Add element to filter"""
        for byte_index, bit_index in self._indexes(s):
            self.bf[byte_index] |= 1 << bit_index

    def check(self, s: str) -> bool:
        """Check if element is in filter"""
        return all(
            (self.bf[byte_index] >> bit_index) & 1
            for byte_index, bit_index in self._indexes(s)
        )

    def check_then_add(self, s: str) -> bool:
        """Check if element was already in filter then add it"""
        result = True
        for byte_index, bit_index in self._indexes(s):
            if not (self.bf[byte_index] >> bit_index) & 1:
                result = False
                self.bf[byte_index] |= 1 << bit_index
        return result

    def save(self, path: str = None) -> None:
        """Save filter to file"""
        if path:
            self.path = path
        elif not hasattr(self, "path"):
            raise BloomException(
                "path must be specified at init or when calling save()"
            )

        saved_bloom = {
            "version": __version__,
            "program": __program__,
            "type": self.type,
            "bloom": {
                "bins": self.bins,
                "hashes": self.hashes,
                "bf": binascii.hexlify(self.bf).decode(),
            },
        }

        with gzip.open(self.path, "wb") as f:
            f.write(json.dumps(saved_bloom).encode())

    def load(self, path: str) -> None:
        """Load filter from file"""
        if path is None:
            raise BloomException("path must be specified when calling load()")

        if not os.path.isfile(path):
            raise BloomException(f"'{path}' must be a file")

        with gzip.open(path, "rb") as f:
            try:
                saved_bloom = json.loads(f.read().decode())
            except json.JSONDecodeError as e:
                raise BloomException(f"Invalid JSON: {e}")

        if (
            "program" not in saved_bloom
            or saved_bloom["program"] != __program__
        ):
            raise BloomException(f"Unrecognized file format '{path}'")
        if saved_bloom["type"] != self.type:
            raise BloomException(
                f"Input '{path}' contains incorrect bloom type"
            )

        self.bins = saved_bloom["bloom"]["bins"]
        self.hashes = saved_bloom["bloom"]["hashes"]
        self.bf = bytearray.fromhex(saved_bloom["bloom"]["bf"])
        self.bytes = self.bins // 8

    def __contains__(self, s: str) -> bool:
        return self.check(s)

    def __len__(self) -> int:
        return self.bins

    def __str__(self) -> str:
        return f"Bloom filter with {self.bins} bits"

    def _indexes(self, s: str):
        """Find array of tuple bloom indexes for input string"""
        s = self._utf8(s)
        for i in range(self.hashes):
            digest = self._hash(s, seed=i)
            yield self._digest2index(digest)

    def _digest2index(self, digest: int) -> Tuple[int, int]:
        """Convert a hash digest to an index tuple"""
        index = digest % self.bins
        return (index // 8, index % 8)

    def _saturation(self) -> float:
        """Calculate the proportion of bits in buffer equal to 1"""
        return sum(bin(byte).count("1") for byte in self.bf) / float(self.bins)

    @staticmethod
    def _hash(s: str, seed: int) -> int:
        """Hash function wrapper"""
        return mmh3.hash(s, seed=seed)

    @staticmethod
    def _hashes(error_ratio: float) -> int:
        """Calculate number of hashes required for a particular error ratio"""
        return int(math.ceil(-math.log(error_ratio) / math.log(2)))

    @staticmethod
    def _utf8(s: str) -> bytes:
        """Convert strings to utf-8 encoding"""
        return s.encode("utf-8") if isinstance(s, str) else s
