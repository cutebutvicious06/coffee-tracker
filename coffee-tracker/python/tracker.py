# The brain of the app: pure timer/state logic.
# No bricks, no files, no clock: every function gets the detections and
# the current time as arguments and returns a NEW state. That makes it
# testable with fake detections and fake times on any computer.

from dataclasses import asdict, dataclass, field, replace
from typing import Optional

import config
from identity import is_me
from zones import zone_for_box


@dataclass(frozen=True)
class CupSighting:
    zone: str
    box: tuple  # (x1, y1, x2, y2) in pixels
    confidence: float
    time: float  # seconds since 1970 (time.time())


@dataclass(frozen=True)
class State:
    started_at: float
    last_cup: Optional[CupSighting] = None
    last_me_time: Optional[float] = None
    me_in_view: bool = False
    cup_absent_sec: float = 0.0
    lost: bool = False
    last_raw: dict = field(default_factory=dict)  # for the debug panel
    last_raw_time: Optional[float] = None


def new_state(now, last_cup=None):
    """Fresh state at app start. last_cup can come from the JSON store."""
    return State(started_at=now, last_cup=last_cup)


def filter_labels(detections):
    """Keep only cup and person (if FILTER_LABELS is on)."""
    if not config.FILTER_LABELS:
        return detections
    keep = (config.CUP_LABEL, config.PERSON_LABEL)
    return {label: dets for label, dets in detections.items() if label in keep}


def confident_persons(detections):
    """Person detections at or above PERSON_MIN_CONF."""
    return [
        d for d in detections.get(config.PERSON_LABEL, [])
        if d.get("confidence", 0.0) >= config.PERSON_MIN_CONF
    ]


def best_cup(detections):
    """Highest-confidence cup detection, or None if no cup."""
    cups = [
        d for d in detections.get(config.CUP_LABEL, [])
        if d.get("confidence", 0.0) >= config.CUP_START_CONF
    ]
    if not cups:
        return None
    return max(cups, key=lambda d: d.get("confidence", 0.0))


def update(state, detections, now):
    """Return the new state after seeing `detections` at time `now`.

    Call this for every detection callback AND regularly with {} --
    the brick sends nothing when it sees nothing, so an empty dict is
    how "not seen" reaches the timer.
    """
    detections = filter_labels(detections)

    # 1. Cup: remember where/when, whether or not I'm in view.
    last_cup = state.last_cup
    cup = best_cup(detections)
    if cup is not None:
        box = tuple(cup["bounding_box_xyxy"])
        last_cup = CupSighting(
            zone=zone_for_box(box),
            box=box,
            confidence=cup.get("confidence", 0.0),
            time=now,
        )

    # 2. Me: in view if seen within the last PERSON_TIMEOUT_SEC.
    persons = confident_persons(detections)
    last_me_time = now if is_me({config.PERSON_LABEL: persons}) else state.last_me_time
    me_in_view = (
        last_me_time is not None and now - last_me_time <= config.PERSON_TIMEOUT_SEC
    )

    # 3. Absence: counted from the last sighting, but never from before
    #    the app started (a sighting loaded from yesterday shouldn't make
    #    the cup "lost" the instant the camera wakes up).
    if last_cup is None:
        absent_from = state.started_at
    else:
        absent_from = max(last_cup.time, state.started_at)
    cup_absent_sec = 0.0 if cup is not None else max(now - absent_from, 0.0)

    # 4. Lost only when I'm here AND the cup has been gone N seconds.
    lost = me_in_view and cup_absent_sec >= config.N_SECONDS

    new = replace(
        state,
        last_cup=last_cup,
        last_me_time=last_me_time,
        me_in_view=me_in_view,
        cup_absent_sec=cup_absent_sec,
        lost=lost,
    )
    if detections:
        new = replace(new, last_raw=detections, last_raw_time=now)
    return new


def cup_in_view(state, now):
    return (
        state.last_cup is not None
        and now - state.last_cup.time <= config.CUP_VISIBLE_SEC
    )


def status_text(state, now):
    """One short line for the top of the page."""
    if state.lost:
        return "LOST: your coffee has been gone for %d s" % state.cup_absent_sec
    if cup_in_view(state, now):
        return "Coffee in view (%s)" % state.last_cup.zone
    if state.me_in_view:
        return "Coffee missing for %d s" % state.cup_absent_sec
    return "Nobody in view"


def ago_text(seconds):
    """12 -> 'just now', 300 -> '5 minutes ago'."""
    seconds = int(seconds)
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return "1 minute ago" if minutes == 1 else "%d minutes ago" % minutes
    hours = minutes // 60
    return "1 hour ago" if hours == 1 else "%d hours ago" % hours


def answer_text(state, now):
    """The sentence shown and spoken after 'Hey Arduino'."""
    if state.last_cup is None:
        return "I haven't seen your coffee yet."
    if cup_in_view(state, now):
        return "Your coffee is right there, %s." % state.last_cup.zone
    return "Your coffee was last seen %s, %s." % (
        state.last_cup.zone,
        ago_text(now - state.last_cup.time),
    )


def to_dict(state, now):
    """Everything the web page needs, as plain JSON-friendly data."""
    d = asdict(state)
    d["status"] = status_text(state, now)
    d["now"] = now
    return d
