import os
import json
import binascii
import gzip
import math
from typing import Any, List

from . import __version__, __program__
from . import Bloom, BloomException


MAX_ERROR = 1e-15
ERROR_DECAY_RATE = 0.5
INITIAL_SIZE = 128 << 10  # 16KiB
GROWTH_FACTOR = 4


class ScalableBloom(Bloom):
    """Scalable Bloom filter implementation"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.type = "scalable bloom"
        self.blooms = 0
        self.elements = 0
        self.threshold = 0
        self.bins_list: List[int] = []
        self.hashes: List[int] = []
        self.bfs: List[bytearray] = []

        self.max_error = kwargs.get("max_error", MAX_ERROR)
        self.error_decay_rate = kwargs.get(
            "error_decay_rate",
            ERROR_DECAY_RATE,
        )
        self.initial_size = kwargs.get("initial_size", INITIAL_SIZE)
        self.growth_factor = kwargs.get("growth_factor", GROWTH_FACTOR)

        self._validate_params()

        self.initial_error = (1.0 - self.error_decay_rate) * self.max_error

        if self.path is not None:
            self.load(self.path)
        else:
            self.new_bloom()

    def _validate_params(self) -> None:
        """Validate initialization parameters"""
        if not 0 < self.max_error < 1:
            raise BloomException("0 < max_error < 1")
        if not 0 < self.error_decay_rate < 1:
            raise BloomException("0 < error_decay_rate < 1")
        if self.growth_factor < 1:
            raise BloomException("growth_factor must be >= 1")
        if self.initial_size <= 0:
            raise BloomException("initial_size must be > 0")

    def new_bloom(self) -> None:
        """Add new internal filter to scalable bloom filter"""
        bins = int(self.initial_size * self.growth_factor**self.blooms)
        error = self.initial_error * self.error_decay_rate**self.blooms
        hashes = self._hashes(error)

        bytes_count = (bins // 8) + 1
        bf = bytearray(b"\0" * bytes_count)
        self.bfs.append(bf)
        self.bins_list.append(bins)
        self.hashes.append(hashes)

        self.blooms += 1
        self.threshold += self._capacity(self.blooms - 1)

    def add(self, s: str) -> None:
        """Add element to filter"""
        self.elements += 1
        current_bloom = self.blooms - 1

        indexes_list = self._indexes(s, current_bloom)
        for indexes in indexes_list:
            for byte_index, bit_index in indexes:
                self.bfs[current_bloom][byte_index] |= 1 << bit_index

        if self.elements > self.threshold:
            self.new_bloom()

    def check(self, s: str) -> bool:
        """Check if element is in filter."""
        indexes_list = list(self._indexes(s))
        return any(
            all(
                (self.bfs[bloom][byte_index] >> bit_index) & 1
                for byte_index, bit_index in indexes
            )
            for bloom, indexes in enumerate(indexes_list)
            if indexes
        )  # Only check non-empty index lists

    def check_then_add(self, s: str) -> bool:
        """If element isn't already in filter, add it"""
        if self.check(s):
            return True

        self.add(s)
        return False

    def save(self, path: str = None) -> None:
        if path is not None:
            self.path = path

        if self.path is None:
            raise BloomException("No path specified")

        saved_bloom = {
            "version": __version__,
            "program": __program__,
            "type": self.type,
            "bloom": {
                "blooms": self.blooms,
                "threshold": self.threshold,
                "elements": self.elements,
                "max_error": self.max_error,
                "error_decay_rate": self.error_decay_rate,
                "initial_size": self.initial_size,
                "growth_factor": self.growth_factor,
                "blooms_list": self.bins_list,
                "hashes": self.hashes,
                "bfs": [binascii.hexlify(bf).decode() for bf in self.bfs],
            },
        }

        with gzip.open(self.path, "wb") as fp:
            fp.write(json.dumps(saved_bloom).encode("utf-8"))

    def load(self, path: str) -> None:
        if not os.path.isfile(path):
            raise BloomException(f"'{path}' must be a file")

        with gzip.open(path, "rb") as fp:
            properties = json.loads(fp.read().decode("utf-8"))

        if properties["type"] != self.type:
            raise BloomException(f"Invalid type: {properties['type']}")

        self.blooms = properties["bloom"]["blooms"]
        self.threshold = properties["bloom"]["threshold"]
        self.elements = properties["bloom"]["elements"]
        self.max_error = properties["bloom"]["max_error"]
        self.error_decay_rate = properties["bloom"]["error_decay_rate"]
        self.initial_size = properties["bloom"]["initial_size"]
        self.growth_factor = properties["bloom"]["growth_factor"]
        self.bins_list = properties["bloom"]["blooms_list"]
        self.hashes = properties["bloom"]["hashes"]
        self.bfs = [
            bytearray(binascii.unhexlify(bf))
            for bf in properties["bloom"]["bfs"]
        ]
        self.path = path

    def __contains__(self, s: str) -> bool:
        return self.check(s)

    def _indexes(self, s: str, bloom: int = -1):
        """Find list of index tuples for bloom filter"""
        s = self._utf8(s)
        max_hashes = max(self.hashes) if self.hashes else 0
        digests = [self._hash(s, i) for i in range(max_hashes)]

        begin = 0 if bloom == -1 else bloom
        end = self.blooms if bloom == -1 else bloom + 1

        for i in range(begin, end):
            yield [
                (
                    digest % self.bins_list[i] // 8,
                    digest % self.bins_list[i] % 8,
                )
                for digest in digests[: self.hashes[i]]
            ]

    def _capacity(self, bloom: int = -1) -> int:
        """Calculate maximum number of elements a bloom can accommodate"""
        log2 = math.log(2)
        if bloom == -1:
            total = 0
            for i in range(self.blooms):
                total += self.bins_list[i] * log2 / self.hashes[i]
            return int(total)
        elif bloom < self.blooms:
            return int(self.bins_list[bloom] * log2 / self.hashes[bloom])
        else:
            raise BloomException(f"Bloom '{bloom}' doesn't exist")

    def _saturation(self, bloom: int = -1) -> float:
        """Calculate the proportion of bits in bloom equal to 1"""
        begin = 0 if bloom == -1 else bloom
        end = self.blooms if bloom == -1 else bloom + 1

        total_bits = sum(self.bins_list[i] for i in range(begin, end))
        set_bits = 0
        for i in range(begin, end):
            set_bits += sum(bin(byte).count("1") for byte in self.bfs[i])

        return set_bits / total_bits