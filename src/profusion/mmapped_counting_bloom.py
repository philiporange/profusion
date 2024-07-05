import math
import mmap
import os
import fcntl
import hashlib
from typing import Any, Iterator, ContextManager

from . import Bloom, BloomException


BIN_SIZE = 255
DIR = "/dev/shm"
CAPACITY = 1e6
ERROR_RATIO = 1e-15


class MMCountingBloom(Bloom):
    """Memory-mapped Counting Bloom filter implementation"""

    def __init__(self, name: str, **kwargs: Any) -> None:
        self.type = "mmapped counting bloom"
        self.bin_size: int = kwargs.get("bin_size", BIN_SIZE)
        self.capacity: float = kwargs.get("capacity", CAPACITY)
        self.dir: str = kwargs.get("dir", DIR)
        self.error_ratio: float = kwargs.get("error_ratio", ERROR_RATIO)
        self.name: str = name

        self._validate_params()

        # Calculate bloom filter parameters
        self.bins: int = max(
            1,
            int(
                -(self.capacity * math.log(self.error_ratio))
                / (math.log(2) ** 2)
            ),
        )
        self.hashes: int = max(
            1, int((self.bins / self.capacity) * math.log(2))
        )

        # Use a fixed bin size of 1 byte
        self.bin_bytes: int = 1

        # Calculate total bytes needed for the bloom filter
        self.bytes: int = self.bins * self.bin_bytes

        self._setup_mmap()

    def _validate_params(self) -> None:
        """Validate initialization parameters"""
        if self.bin_size <= 0 or self.bin_size > 255:
            raise BloomException("bin_size must be > 0 and <= 255")
        if self.capacity <= 0:
            raise BloomException("capacity must be > 0")
        if not 0 < self.error_ratio < 1:
            raise BloomException("0 < error_ratio < 1")

    def _setup_mmap(self) -> None:
        """Set up memory-mapped file"""
        fn = f"{self.name}.mmcb"
        self.path = os.path.join(self.dir, fn)

        if (
            not os.path.isfile(self.path)
            or os.path.getsize(self.path) != self.bytes
        ):
            with open(self.path, "wb") as fp:
                fp.write(b"\0" * self.bytes)

        self.fp = open(self.path, "r+b")
        self.bf = mmap.mmap(self.fp.fileno(), 0)

    def add(self, s: str, amount: int = 1) -> bool:
        """Add amount to element"""
        with self._lock():
            increments = []
            for index in self._indexes(s):
                if not 0 <= index < self.bins:
                    raise BloomException("Index out of range")

                increments.append(self._increment_bin(index, amount))
            return all(increments)

    def value(self, s: str) -> int:
        """Get value of element"""
        with self._lock():
            values = []
            for index in self._indexes(s):
                if 0 <= index < self.bins:
                    values.append(self._bin(index))
                else:
                    raise BloomException(
                        f"Index {index} out of range. Bins: {self.bins}"
                    )

            return min(values) if values else 0

    def check(self, s: str, trigger: int = 1) -> bool:
        """Check if value of element is at least trigger."""
        return self.value(s) >= trigger

    def zero(self) -> None:
        """Reset all counts"""
        with self._lock():
            self.bf.seek(0)
            self.bf.write(b"\0" * self.bytes)

    def _indexes(self, s: str) -> Iterator[int]:
        """Find list of index tuples for bloom filter"""
        s = self._utf8(s)
        for i in range(self.hashes):
            yield self._hash(s, i) % self.bins

    def _bin(self, index: int) -> int:
        """Get value of bin"""
        return self.bf[index]

    def _increment_bin(self, index: int, amount: int) -> bool:
        """Increase value of bin by amount, return True if full"""
        current_value = self.bf[index]
        if current_value == self.bin_size:
            return True
        new_value = min(current_value + amount, self.bin_size)
        self.bf[index] = new_value
        return new_value == self.bin_size

    def _decrement_bin(self, index: int, amount: int) -> bool:
        """Decrease value of bin by amount, return True if empty"""
        current_value = self.bf[index]
        if current_value == 0:
            return True
        new_value = max(current_value - amount, 0)
        self.bf[index] = new_value
        return new_value == 0

    def _lock(self) -> ContextManager:
        """Context manager for file locking"""

        class FileLock:
            def __init__(self, file):
                self.file = file

            def __enter__(self):
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX)

            def __exit__(self, exc_type, exc_val, exc_tb):
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)

        return FileLock(self.fp)

    def _hash(self, s: bytes, i: int) -> int:
        """Generate hash value for a given string and salt"""
        return int(hashlib.sha256(s + str(i).encode()).hexdigest(), 16)

    def __contains__(self, s: str) -> bool:
        return self.check(s)

    @staticmethod
    def _utf8(s: str) -> bytes:
        """Convert string to UTF-8 bytes"""
        return s.encode("utf-8")

    def __del__(self) -> None:
        """Ensure proper cleanup of resources"""
        if hasattr(self, "bf"):
            self.bf.close()
        if hasattr(self, "fp"):
            self.fp.close()
