import os
import tempfile
import unittest

from src.profusion import ScalableBloom


class TestScalableBloom(unittest.TestCase):
    def setUp(self):
        self.bloom = ScalableBloom(
            initial_size=1000,
            max_error=0.01,
            error_decay_rate=0.5,
            growth_factor=2,
        )

    def test_initialization(self):
        self.assertIsInstance(self.bloom, ScalableBloom)
        self.assertEqual(self.bloom.initial_size, 1000)
        self.assertEqual(self.bloom.max_error, 0.01)
        self.assertEqual(self.bloom.error_decay_rate, 0.5)
        self.assertEqual(self.bloom.growth_factor, 2)

    def test_add_and_check(self):
        self.bloom.add("test")
        self.assertTrue(self.bloom.check("test"))
        self.assertFalse(self.bloom.check("not_added"))

    def test_check_then_add(self):
        self.assertFalse(self.bloom.check_then_add("new_item"))
        self.assertTrue(self.bloom.check_then_add("new_item"))

    def test_scaling(self):
        initial_blooms = self.bloom.blooms
        initial_threshold = self.bloom.threshold

        # Add elements until scaling occurs
        for i in range(int(initial_threshold * 2)):
            self.bloom.add(f"item_{i}")

        self.assertGreater(self.bloom.blooms, initial_blooms)
        self.assertGreater(self.bloom.threshold, initial_threshold)

    def test_multiple_scalings(self):
        initial_blooms = self.bloom.blooms

        # Force multiple scalings
        for i in range(int(self.bloom.threshold * 5)):
            self.bloom.add(f"item_{i}")

        self.assertGreater(self.bloom.blooms, initial_blooms + 1)

    def test_error_rate_decay(self):
        initial_error = self.bloom.initial_error

        # Force scaling
        for i in range(int(self.bloom.threshold * 2)):
            self.bloom.add(f"item_{i}")

        # Check that the error rate for the new filter is lower
        new_error = self.bloom.initial_error
        new_error *= self.bloom.error_decay_rate**self.bloom.blooms
        self.assertLess(new_error, initial_error)

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            self.bloom.add("save_test")
            self.bloom.save(tmp.name)

            new_bloom = ScalableBloom()
            new_bloom.load(tmp.name)

            self.assertEqual(self.bloom.blooms, new_bloom.blooms)
            self.assertEqual(self.bloom.elements, new_bloom.elements)
            self.assertEqual(self.bloom.threshold, new_bloom.threshold)
            self.assertEqual(self.bloom.bins_list, new_bloom.bins_list)
            self.assertEqual(self.bloom.hashes, new_bloom.hashes)
            self.assertEqual(self.bloom.bfs, new_bloom.bfs)
            self.assertTrue(new_bloom.check("save_test"))

        os.unlink(tmp.name)

    def test_capacity(self):
        total_capacity = 0
        for i in range(self.bloom.blooms):
            total_capacity += self.bloom._capacity(i)
        self.assertAlmostEqual(total_capacity, self.bloom.threshold, delta=1)

    def test_saturation(self):
        initial_saturation = self.bloom._saturation()
        for i in range(1000):
            self.bloom.add(f"item_{i}")
        final_saturation = self.bloom._saturation()
        self.assertGreater(final_saturation, initial_saturation)

    def test_indexes(self):
        test_string = "test_string"
        indexes = list(self.bloom._indexes(test_string))
        self.assertEqual(len(indexes), self.bloom.blooms)
        for bloom_indexes in indexes:
            self.assertEqual(len(list(bloom_indexes)), self.bloom.hashes[-1])


if __name__ == "__main__":
    unittest.main()
