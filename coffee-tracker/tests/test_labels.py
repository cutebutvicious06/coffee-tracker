# Run from the coffee-tracker/ folder:  python3 -m unittest discover tests

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from labels import count_labels, normalize_detections  # noqa: E402


def det(confidence=0.9, box=(1, 2, 3, 4)):
    return {"confidence": confidence, "bounding_box_xyxy": box}


class TestNormalize(unittest.TestCase):
    def test_vase_becomes_cup(self):
        out = normalize_detections({"vase": [det()]})
        self.assertEqual(list(out), ["cup"])
        self.assertEqual(out["cup"][0]["label"], "vase")

    def test_potted_plant_is_dropped(self):
        self.assertEqual(normalize_detections({"potted plant": [det()]}), {})

    def test_person_passes_through(self):
        out = normalize_detections({"person": [det()]})
        self.assertEqual(out["person"][0]["label"], "person")

    def test_confidence_and_box_preserved(self):
        out = normalize_detections({"bottle": [det(0.37, (10, 20, 30, 40))]})
        self.assertEqual(out["cup"][0]["confidence"], 0.37)
        self.assertEqual(out["cup"][0]["bounding_box_xyxy"], (10, 20, 30, 40))

    def test_aliases_merge_into_one_cup_list(self):
        out = normalize_detections({"cup": [det(0.8)], "bowl": [det(0.4)], "chair": [det()]})
        self.assertEqual([d["label"] for d in out["cup"]], ["cup", "bowl"])
        self.assertNotIn("chair", out)

    def test_input_is_not_changed(self):
        raw = {"vase": [det()]}
        normalize_detections(raw)
        self.assertNotIn("label", raw["vase"][0])


class TestCountLabels(unittest.TestCase):
    def test_counts_every_box_and_keeps_old_counts(self):
        counts = count_labels({}, {"chair": [det(), det()], "vase": [det()]})
        counts = count_labels(counts, {"chair": [det()]})
        self.assertEqual(counts, {"chair": 3, "vase": 1})

    def test_does_not_change_old_dict(self):
        old = {"cup": 1}
        count_labels(old, {"cup": [det()]})
        self.assertEqual(old, {"cup": 1})


if __name__ == "__main__":
    unittest.main()
