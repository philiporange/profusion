import unittest
import sys

from tests.test_bloom import TestBloom
from tests.test_counting_bloom import TestCountingBloom
from tests.test_scalable_bloom import TestScalableBloom


def run_tests():
    # Create a test suite combining all test cases
    test_suite = unittest.TestSuite()

    # Add test cases for each Bloom filter implementation
    test_suite.addTest(unittest.makeSuite(TestBloom))
    test_suite.addTest(unittest.makeSuite(TestCountingBloom))
    test_suite.addTest(unittest.makeSuite(TestScalableBloom))

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Return the number of failures and errors
    return len(result.failures) + len(result.errors)


if __name__ == '__main__':
    sys.exit(run_tests())
