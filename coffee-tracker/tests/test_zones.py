# Run from the coffee-tracker/ folder:  python3 -m unittest discover tests

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import config  # noqa: E402
from zones import box_center, zone_for_box  # noqa: E402

GRID = {
    "left": (0.0, 0.0, 0.5, 1.0),
    "right": (0.5, 0.0, 1.0, 1.0),
}


class TestZones(unittest.TestCase):
    def test_center(self):
        self.assertEqual(box_center((10, 20, 30, 60)), (20, 40))

    def test_left_and_right(self):
        self.assertEqual(zone_for_box((0, 0, 100, 100), GRID, 640, 480), "left")
        self.assertEqual(zone_for_box((500, 0, 600, 100), GRID, 640, 480), "right")

    def test_box_outside_frame_is_clamped(self):
        # Centre at x=700 on a 640-wide frame -> clamped to the right edge
        self.assertEqual(zone_for_box((650, 0, 750, 10), GRID, 640, 480), "right")

    def test_no_matching_zone(self):
        only_left = {"left": (0.0, 0.0, 0.5, 1.0)}
        self.assertEqual(
            zone_for_box((500, 0, 600, 100), only_left, 640, 480), config.UNKNOWN_ZONE
        )

    def test_default_config_covers_whole_frame(self):
        # Every point of the default grid should land in a named zone.
        for x in range(0, config.FRAME_W + 1, 40):
            for y in range(0, config.FRAME_H + 1, 40):
                zone = zone_for_box((x, y, x, y))
                self.assertIn(zone, config.ZONES, f"({x},{y}) -> {zone}")


if __name__ == "__main__":
    unittest.main()
