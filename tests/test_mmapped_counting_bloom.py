import unittest
import os
import tempfile

from src.profusion import MMCountingBloom, BloomException


class TestMMCountingBloom(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bloom = MMCountingBloom(
            "test_bloom", dir=self.temp_dir, capacity=1000, error_ratio=0.01
        )

    def tearDown(self):
        del self.bloom
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_initialization(self):
        self.assertEqual(self.bloom.name, "test_bloom")
        self.assertEqual(self.bloom.type, "mmapped counting bloom")
        self.assertEqual(self.bloom.dir, self.temp_dir)
        self.assertEqual(self.bloom.capacity, 1000)
        self.assertEqual(self.bloom.error_ratio, 0.01)

    def test_add_and_check(self):
        self.bloom.add("test_element")
        self.assertTrue(self.bloom.check("test_element"))
        self.assertFalse(self.bloom.check("non_existent_element"))

    def test_value(self):
        self.bloom.add("test_element", amount=3)
        self.assertEqual(self.bloom.value("test_element"), 3)
        self.assertEqual(self.bloom.value("non_existent_element"), 0)

    def test_zero(self):
        self.bloom.add("test_element", amount=5)
        self.bloom.zero()
        self.assertEqual(self.bloom.value("test_element"), 0)

    def test_contains(self):
        self.bloom.add("test_element")
        self.assertIn("test_element", self.bloom)
        self.assertNotIn("non_existent_element", self.bloom)

    def test_invalid_parameters(self):
        with self.assertRaises(Exception):
            MMCountingBloom("invalid", bin_size=0)
        with self.assertRaises(Exception):
            MMCountingBloom("invalid", bin_size=256)
        with self.assertRaises(Exception):
            MMCountingBloom("invalid", capacity=0)
        with self.assertRaises(Exception):
            MMCountingBloom("invalid", error_ratio=0)
        with self.assertRaises(Exception):
            MMCountingBloom("invalid", error_ratio=1)

    def test_add_multiple_times(self):
        self.bloom.add("test_element", amount=3)
        self.bloom.add("test_element", amount=2)
        self.assertEqual(self.bloom.value("test_element"), 5)

    def test_check_with_trigger(self):
        self.bloom.add("test_element", amount=3)
        self.assertTrue(self.bloom.check("test_element", trigger=2))
        self.assertTrue(self.bloom.check("test_element", trigger=3))
        self.assertFalse(self.bloom.check("test_element", trigger=4))

    def test_bin_size_limit(self):
        max_bin_size = self.bloom.bin_size
        self.bloom.add("test_element", amount=max_bin_size + 10)
        self.assertEqual(self.bloom.value("test_element"), max_bin_size)


if __name__ == "__main__":
    unittest.main()
