# Run from the coffee-tracker/ folder:  python3 -m unittest discover tests
#
# Fake detections use the same shape as the real brick:
#   {label: [{"confidence": float, "bounding_box_xyxy": (x1, y1, x2, y2)}]}

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import config  # noqa: E402
import tracker  # noqa: E402
from identity import is_me  # noqa: E402

N = config.N_SECONDS
T0 = 1000.0  # fake "app started" time

TOP_LEFT_BOX = (10, 10, 60, 60)
BOTTOM_RIGHT_BOX = (580, 420, 630, 470)


def det(label, box=(0, 0, 10, 10), confidence=0.9):
    return {"confidence": confidence, "bounding_box_xyxy": box}


def frame(person=False, cup_box=None):
    """Build a fake detections dict for one frame."""
    d = {}
    if person:
        d["person"] = [det("person", (200, 0, 400, 480))]
    if cup_box is not None:
        d["cup"] = [det("cup", cup_box)]
    return d


def run(state, frames):
    """Feed a list of (time, detections) through the tracker."""
    for t, d in frames:
        state = tracker.update(state, d, t)
    return state


class TestIsMe(unittest.TestCase):
    def test_any_person_is_me(self):
        self.assertTrue(is_me(frame(person=True)))

    def test_no_person(self):
        self.assertFalse(is_me({}))
        self.assertFalse(is_me(frame(cup_box=TOP_LEFT_BOX)))


class TestCupPosition(unittest.TestCase):
    def test_cup_seen_without_me_is_still_recorded(self):
        s = tracker.update(tracker.new_state(T0), frame(cup_box=TOP_LEFT_BOX), T0 + 1)
        self.assertEqual(s.last_cup.zone, "top left")
        self.assertEqual(s.last_cup.time, T0 + 1)
        self.assertFalse(s.me_in_view)

    def test_cup_moves(self):
        s = run(tracker.new_state(T0), [
            (T0 + 1, frame(cup_box=TOP_LEFT_BOX)),
            (T0 + 2, frame(cup_box=BOTTOM_RIGHT_BOX)),
        ])
        self.assertEqual(s.last_cup.zone, "bottom right")

    def test_highest_confidence_cup_wins(self):
        d = {"cup": [det("cup", TOP_LEFT_BOX, 0.6), det("cup", BOTTOM_RIGHT_BOX, 0.95)]}
        s = tracker.update(tracker.new_state(T0), d, T0 + 1)
        self.assertEqual(s.last_cup.zone, "bottom right")

    def test_empty_update_keeps_last_position(self):
        s = run(tracker.new_state(T0), [
            (T0 + 1, frame(cup_box=TOP_LEFT_BOX)),
            (T0 + 50, {}),
        ])
        self.assertEqual(s.last_cup.zone, "top left")
        self.assertEqual(s.last_cup.time, T0 + 1)


class TestLost(unittest.TestCase):
    def test_lost_after_n_seconds_with_me_in_view(self):
        s = run(tracker.new_state(T0), [
            (T0 + 1, frame(cup_box=TOP_LEFT_BOX)),
            (T0 + 1 + N, frame(person=True)),
        ])
        self.assertTrue(s.lost)

    def test_not_lost_just_before_n_seconds(self):
        s = run(tracker.new_state(T0), [
            (T0 + 1, frame(cup_box=TOP_LEFT_BOX)),
            (T0 + 1 + N - 0.1, frame(person=True)),
        ])
        self.assertFalse(s.lost)

    def test_not_lost_when_nobody_in_view(self):
        # "No callback" = empty dict = nobody seen.
        s = run(tracker.new_state(T0), [
            (T0 + 1, frame(cup_box=TOP_LEFT_BOX)),
            (T0 + 1 + N * 5, {}),
        ])
        self.assertFalse(s.me_in_view)
        self.assertFalse(s.lost)

    def test_no_callback_counts_as_not_seen(self):
        # I stay in view (person every second), the cup's frames simply stop.
        frames = [(T0 + 1, frame(person=True, cup_box=TOP_LEFT_BOX))]
        frames += [(T0 + 1 + i, frame(person=True)) for i in range(1, int(N) + 1)]
        s = run(tracker.new_state(T0), frames)
        self.assertTrue(s.lost)

    def test_me_stays_in_view_between_flickers(self):
        # Person seen, then only empty ticks, within PERSON_TIMEOUT_SEC.
        s = run(tracker.new_state(T0), [
            (T0 + 1, frame(cup_box=TOP_LEFT_BOX)),
            (T0 + N, frame(person=True)),
            (T0 + N + 1.5, {}),
        ])
        self.assertTrue(s.me_in_view)
        self.assertTrue(s.lost)

    def test_me_leaves_view_clears_lost(self):
        s = run(tracker.new_state(T0), [
            (T0 + 1, frame(cup_box=TOP_LEFT_BOX)),
            (T0 + 1 + N, frame(person=True)),
            (T0 + 1 + N + config.PERSON_TIMEOUT_SEC + 1, {}),
        ])
        self.assertFalse(s.lost)

    def test_cup_back_resets_timer(self):
        s = run(tracker.new_state(T0), [
            (T0 + 1, frame(cup_box=TOP_LEFT_BOX)),
            (T0 + 1 + N - 1, frame(person=True, cup_box=TOP_LEFT_BOX)),
            (T0 + 1 + N + 1, frame(person=True)),
        ])
        self.assertFalse(s.lost)
        self.assertAlmostEqual(s.cup_absent_sec, 2.0)

    def test_never_seen_cup_counts_from_app_start(self):
        s = tracker.update(tracker.new_state(T0), frame(person=True), T0 + N)
        self.assertTrue(s.lost)

    def test_old_stored_sighting_counts_from_app_start(self):
        yesterday = tracker.CupSighting("top left", TOP_LEFT_BOX, 0.9, T0 - 86400)
        state = tracker.new_state(T0, last_cup=yesterday)
        s = tracker.update(state, frame(person=True), T0 + 1)
        self.assertFalse(s.lost)
        self.assertAlmostEqual(s.cup_absent_sec, 1.0)


class TestLabelsAndPerson(unittest.TestCase):
    def test_other_labels_are_dropped(self):
        d = frame(cup_box=TOP_LEFT_BOX)
        d["chair"] = [det("chair", (0, 0, 5, 5))]
        s = tracker.update(tracker.new_state(T0), d, T0 + 1)
        self.assertNotIn("chair", s.last_raw)

    def test_only_chairs_counts_as_empty(self):
        s = tracker.update(tracker.new_state(T0), {"chair": [det("chair")]}, T0 + 1)
        self.assertEqual(s.last_raw, {})

    def test_cup_below_start_conf_is_ignored(self):
        d = {"cup": [det("cup", TOP_LEFT_BOX, config.CUP_START_CONF - 0.01)]}
        s = tracker.update(tracker.new_state(T0), d, T0 + 1)
        self.assertIsNone(s.last_cup)

    def test_weak_person_is_not_in_view(self):
        d = {"person": [det("person", confidence=config.PERSON_MIN_CONF - 0.01)]}
        s = tracker.update(tracker.new_state(T0), d, T0 + 1)
        self.assertFalse(s.me_in_view)


class TestTexts(unittest.TestCase):
    def test_answer_never_seen(self):
        s = tracker.new_state(T0)
        self.assertEqual(tracker.answer_text(s, T0), "I haven't seen your coffee yet.")

    def test_answer_in_view(self):
        s = tracker.update(tracker.new_state(T0), frame(cup_box=TOP_LEFT_BOX), T0 + 1)
        self.assertIn("right there, top left", tracker.answer_text(s, T0 + 1.5))

    def test_answer_minutes_ago(self):
        s = tracker.update(tracker.new_state(T0), frame(cup_box=TOP_LEFT_BOX), T0 + 1)
        self.assertEqual(
            tracker.answer_text(s, T0 + 1 + 300),
            "Your coffee was last seen top left, 5 minutes ago.",
        )

    def test_ago_text(self):
        self.assertEqual(tracker.ago_text(5), "just now")
        self.assertEqual(tracker.ago_text(60), "1 minute ago")
        self.assertEqual(tracker.ago_text(7200), "2 hours ago")

    def test_status_lost(self):
        s = tracker.update(tracker.new_state(T0), frame(person=True), T0 + N)
        self.assertTrue(tracker.status_text(s, T0 + N).startswith("LOST"))

    def test_to_dict_is_json_friendly(self):
        import json
        s = tracker.update(tracker.new_state(T0), frame(person=True, cup_box=TOP_LEFT_BOX), T0 + 1)
        json.dumps(tracker.to_dict(s, T0 + 1))  # must not raise


if __name__ == "__main__":
    unittest.main()
