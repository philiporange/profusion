import unittest
import tempfile
import os

from src.profusion import Bloom, BloomException


class TestBloom(unittest.TestCase):
    def setUp(self):
        self.bloom = Bloom(capacity=1000, error_ratio=0.01)

    def test_initialization(self):
        self.assertIsInstance(self.bloom, Bloom)
        self.assertEqual(self.bloom.capacity, 1000)
        self.assertEqual(self.bloom.error_ratio, 0.01)

    def test_add_and_check(self):
        self.bloom.add("test")
        self.assertTrue(self.bloom.check("test"))
        self.assertFalse(self.bloom.check("not_added"))

    def test_check_then_add(self):
        self.assertFalse(self.bloom.check_then_add("new_item"))
        self.assertTrue(self.bloom.check_then_add("new_item"))

    def test_contains(self):
        self.bloom.add("contained_item")
        self.assertIn("contained_item", self.bloom)
        self.assertNotIn("not_contained_item", self.bloom)

    def test_len(self):
        self.assertEqual(len(self.bloom), self.bloom.bins)

    def test_str(self):
        expected = f"Bloom filter with {self.bloom.bins} bits"
        self.assertEqual(str(self.bloom), expected)

    def test_saturation(self):
        initial_saturation = self.bloom._saturation()
        for i in range(100):
            self.bloom.add(f"item_{i}")
        final_saturation = self.bloom._saturation()
        self.assertGreater(final_saturation, initial_saturation)

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            self.bloom.add("save_test")
            self.bloom.save(tmp.name)

            new_bloom = Bloom()
            new_bloom.load(tmp.name)

            self.assertEqual(self.bloom.bins, new_bloom.bins)
            self.assertEqual(self.bloom.hashes, new_bloom.hashes)
            self.assertEqual(self.bloom.bf, new_bloom.bf)
            self.assertTrue(new_bloom.check("save_test"))

        os.unlink(tmp.name)

    def test_invalid_capacity(self):
        with self.assertRaises(BloomException):
            Bloom(capacity=0)

    def test_invalid_error_ratio(self):
        with self.assertRaises(BloomException):
            Bloom(error_ratio=0)
        with self.assertRaises(BloomException):
            Bloom(error_ratio=1)


if __name__ == "__main__":
    unittest.main()
