#!/usr/bin/env python3
"""Hermetic unittest runner (stdlib only)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    suite = unittest.TestLoader().discover(
        start_dir=os.path.dirname(os.path.abspath(__file__)),
        pattern="test_*.py",
        top_level_dir=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print("tests run: %d, failures: %d, errors: %d"
          % (result.testsRun, len(result.failures), len(result.errors)))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
