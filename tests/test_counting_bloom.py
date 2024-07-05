import unittest
import tempfile
import os

from src.profusion import CountingBloom


class TestCountingBloom(unittest.TestCase):
    def setUp(self):
        self.bloom = CountingBloom(
            capacity=1000,
            error_ratio=0.01,
            bin_size=10,
        )

    def test_initialization(self):
        self.assertIsInstance(self.bloom, CountingBloom)
        self.assertEqual(self.bloom.capacity, 1000)
        self.assertEqual(self.bloom.error_ratio, 0.01)
        self.assertEqual(self.bloom.bin_size, 10)

    def test_add_and_value(self):
        self.bloom.add("test", 3)
        self.assertEqual(self.bloom.value("test"), 3)
        self.bloom.add("test", 2)
        self.assertEqual(self.bloom.value("test"), 5)

    def test_check(self):
        self.bloom.add("test", 5)
        self.assertTrue(self.bloom.check("test", 5))
        self.assertTrue(self.bloom.check("test", 4))
        self.assertFalse(self.bloom.check("test", 6))

    def test_bin_size_limit(self):
        self.bloom.add("test", self.bloom.bin_size)
        self.assertEqual(self.bloom.value("test"), self.bloom.bin_size)
        self.bloom.add("test", 1)  # This should not increase the value further
        self.assertEqual(self.bloom.value("test"), self.bloom.bin_size)

    def test_multiple_elements(self):
        self.bloom.add("test1", 3)
        self.bloom.add("test2", 5)
        self.assertEqual(self.bloom.value("test1"), 3)
        self.assertEqual(self.bloom.value("test2"), 5)

    def test_non_existent_element(self):
        self.assertEqual(self.bloom.value("not_added"), 0)

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            self.bloom.add("save_test", 7)
            self.bloom.save(tmp.name)

            new_bloom = CountingBloom()
            new_bloom.load(tmp.name)

            self.assertEqual(self.bloom.bins, new_bloom.bins)
            self.assertEqual(self.bloom.hashes, new_bloom.hashes)
            self.assertEqual(self.bloom.bin_size, new_bloom.bin_size)
            self.assertEqual(self.bloom.bin_bytes, new_bloom.bin_bytes)
            self.assertEqual(self.bloom.bf, new_bloom.bf)
            self.assertEqual(new_bloom.value("save_test"), 7)

        os.unlink(tmp.name)

    def test_invalid_bin_size(self):
        with self.assertRaises(Exception):
            CountingBloom(bin_size=0)

    def test_int2bytes_and_bytes2int(self):
        original = 42
        bytes_repr = CountingBloom._int2bytes(original, 4)
        self.assertEqual(len(bytes_repr), 4)
        reconstructed = CountingBloom._bytes2int(bytes_repr)
        self.assertEqual(original, reconstructed)

    def test_increment_and_decrement_bin(self):
        index = 0
        self.bloom._increment_bin(index, 5)
        self.assertEqual(self.bloom._bin(index), 5)
        self.bloom._decrement_bin(index, 2)
        self.assertEqual(self.bloom._bin(index), 3)

    def test_bin_operations_at_limits(self):
        index = 0
        # Test upper limit
        self.assertTrue(self.bloom._increment_bin(index, self.bloom.bin_size))
        self.assertEqual(self.bloom._bin(index), self.bloom.bin_size)
        self.assertTrue(self.bloom._increment_bin(index, 1))  # Value unchanged
        self.assertEqual(self.bloom._bin(index), self.bloom.bin_size)

        # Reset bin
        self.bloom._set_bin(index, 0)

        # Test lower limit
        self.assertTrue(self.bloom._decrement_bin(index, 1))
        self.assertEqual(self.bloom._bin(index), 0)
        self.assertTrue(self.bloom._decrement_bin(index, 1))  # Value unchanged
        self.assertEqual(self.bloom._bin(index), 0)


if __name__ == "__main__":
    unittest.main()
