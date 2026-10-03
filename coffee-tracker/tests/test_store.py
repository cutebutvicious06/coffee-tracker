# Run from the coffee-tracker/ folder:  python3 -m unittest discover tests

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import config  # noqa: E402
import store  # noqa: E402
from tracker import CupSighting  # noqa: E402


def sighting(zone="top left", t=100.0):
    return CupSighting(zone, (1, 2, 3, 4), 0.9, t)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "sub", "last_seen.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_round_trip(self):
        self.assertTrue(store.save(sighting(), self.path))
        self.assertEqual(store.load(self.path), sighting())

    def test_missing_file(self):
        self.assertIsNone(store.load(self.path))

    def test_broken_file(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as f:
            f.write("not json")
        self.assertIsNone(store.load(self.path))


class TestShouldSave(unittest.TestCase):
    def test_first_sighting(self):
        self.assertTrue(store.should_save(None, sighting()))

    def test_nothing_to_save(self):
        self.assertFalse(store.should_save(sighting(), None))

    def test_zone_change(self):
        self.assertTrue(store.should_save(sighting("top left"), sighting("top right", 101)))

    def test_same_zone_waits(self):
        old = sighting(t=100)
        self.assertFalse(store.should_save(old, sighting(t=105)))
        later = 100 + config.SAVE_EVERY_SEC
        self.assertTrue(store.should_save(old, sighting(t=later)))


if __name__ == "__main__":
    unittest.main()
