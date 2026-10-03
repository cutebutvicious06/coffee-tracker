# The brain of the app: pure timer/state logic.
# No bricks, no files, no clock: every function gets the detections and
# the current time as arguments and returns a NEW state. That makes it
# testable with fake detections and fake times on any computer.

import math
from dataclasses import asdict, dataclass, field, replace
from typing import Optional

import config
from identity import is_me
from zones import box_center, zone_for_box


@dataclass(frozen=True)
class CupSighting:
    zone: str
    box: tuple  # (x1, y1, x2, y2) in pixels
    confidence: float
    time: float  # seconds since 1970 (time.time())


@dataclass(frozen=True)
class State:
    started_at: float
    last_cup: Optional[CupSighting] = None  # last ACCEPTED cup
    last_me_time: Optional[float] = None
    me_in_view: bool = False
    score: float = 0.0  # evidence score for the cup
    last_update_time: Optional[float] = None
    seen: bool = False  # is the cup currently "seen"?
    last_seen_time: Optional[float] = None
    cup_absent_sec: float = 0.0
    lost: bool = False
    anchor_box: Optional[tuple] = None  # last confident cup box
    anchor_time: Optional[float] = None
    cup_decisions: tuple = ()  # per-cup verdicts from the last frame with cups
    cup_decisions_time: Optional[float] = None
    last_raw: dict = field(default_factory=dict)  # for the debug panel
    last_raw_time: Optional[float] = None


def new_state(now, last_cup=None):
    """Fresh state at app start. last_cup can come from the JSON store.

    The anchor is NOT restored from the store: only a live confident
    cup may set it (anti-phantom).
    """
    return State(started_at=now, last_cup=last_cup)


# --- Small helpers -----------------------------------------------------

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


def center_distance(box_a, box_b):
    ax, ay = box_center(box_a)
    bx, by = box_center(box_b)
    return math.hypot(ax - bx, ay - by)


def anchor_status(state, now):
    """'none', 'active' or 'expired'."""
    if state.anchor_box is None:
        return "none"
    if config.USE_ANCHOR_TTL and now - state.anchor_time > config.ANCHOR_TTL_SECONDS:
        return "expired"
    return "active"


# --- Cup acceptance ----------------------------------------------------

def judge_cup(cup, state, me_in_view, now):
    """Decide about ONE cup box.

    Returns a dict: confidence, box, accepted, strength ('strong',
    'weak' or None), reason (text for the debug panel), distance to
    the anchor (or None).
    """
    conf = cup.get("confidence", 0.0)
    box = tuple(cup["bounding_box_xyxy"])

    # Normal threshold, lowered while a person is in view.
    start = config.CUP_START_CONF
    start_why = ""
    if config.USE_PERSON_BOOST and me_in_view:
        start = min(start, config.CUP_START_CONF_WITH_PERSON)
        start_why = ", person in view"

    distance = None
    anchor = anchor_status(state, now) if config.USE_ANCHOR else "off"
    if state.anchor_box is not None and config.USE_ANCHOR:
        distance = round(center_distance(box, state.anchor_box))
    near = anchor == "active" and distance <= config.ANCHOR_NEAR_PX

    def verdict(accepted, strength, reason):
        return {
            "confidence": conf,
            "box": box,
            "accepted": accepted,
            "strength": strength,
            "reason": reason,
            "anchor_distance": distance,
        }

    if conf >= start:
        return verdict(True, "strong", "strong: %.2f >= %.2f%s" % (conf, start, start_why))
    if near and conf >= config.CUP_NEAR_ANCHOR_CONF:
        return verdict(
            True, "weak",
            "weak: %.2f >= %.2f, %d px from anchor" % (conf, config.CUP_NEAR_ANCHOR_CONF, distance),
        )

    # Rejected: explain why the anchor didn't help.
    if anchor == "off":
        why = "anchor off"
    elif anchor == "none":
        why = "no anchor"
    elif anchor == "expired":
        why = "anchor expired"
    elif not near:
        why = "%d px from anchor" % distance
    else:
        why = "below %.2f even near anchor" % config.CUP_NEAR_ANCHOR_CONF
    return verdict(False, None, "rejected: %.2f < %.2f%s (%s)" % (conf, start, start_why, why))


def pick_best(verdicts):
    """Best accepted cup: strong beats weak, then higher confidence."""
    accepted = [v for v in verdicts if v["accepted"]]
    if not accepted:
        return None
    return max(accepted, key=lambda v: (v["strength"] == "strong", v["confidence"]))


def update_score(state, best, now):
    """New evidence score: add for a hit, drain by time for a miss.

    Draining by elapsed SECONDS (not per call) matters because update()
    is called irregularly: every frame with detections, plus a tick every
    TICK_SEC when the brick sends nothing.
    """
    score = state.score
    if best is not None:
        score += config.HIT_STRONG if best["strength"] == "strong" else config.HIT_WEAK
    elif state.last_update_time is not None:
        score -= config.DECAY_PER_SEC * (now - state.last_update_time)
    return min(max(score, 0.0), config.SCORE_MAX)


# --- The main update ---------------------------------------------------

def update(state, detections, now):
    """Return the new state after seeing `detections` at time `now`.

    Call this for every detection callback AND regularly with {} --
    the brick sends nothing when it sees nothing, so an empty dict is
    how "not seen" reaches the timer.
    """
    detections = filter_labels(detections)

    # 1. Me first: the person boost needs to know if I'm here.
    persons = confident_persons(detections)
    last_me_time = now if is_me({config.PERSON_LABEL: persons}) else state.last_me_time
    me_in_view = (
        last_me_time is not None and now - last_me_time <= config.PERSON_TIMEOUT_SEC
    )

    # 2. Judge every cup box, keep the best accepted one.
    cups = detections.get(config.CUP_LABEL, [])
    verdicts = [judge_cup(c, state, me_in_view, now) for c in cups]
    best = pick_best(verdicts)

    last_cup = state.last_cup
    anchor_box, anchor_time = state.anchor_box, state.anchor_time
    if best is not None:
        # Position/time: updated by any accepted cup, me in view or not.
        last_cup = CupSighting(
            zone=zone_for_box(best["box"]),
            box=best["box"],
            confidence=best["confidence"],
            time=now,
        )
        # Anchor: only a hit at the full CUP_START_CONF may set it,
        # so weak (or person-boosted) hits can't keep a phantom alive.
        if best["confidence"] >= config.CUP_START_CONF:
            anchor_box, anchor_time = best["box"], now

    # 3. Is the cup "seen"?
    score = update_score(state, best, now)
    if config.USE_EVIDENCE_SCORE:
        seen = score >= config.SEEN_SCORE
        last_seen_time = now if seen else state.last_seen_time
    else:
        # Simple version: accepted within the last CUP_VISIBLE_SEC.
        last_seen_time = now if best is not None else state.last_seen_time
        seen = last_seen_time is not None and now - last_seen_time < config.CUP_VISIBLE_SEC

    # 4. Absence: counted from the last moment the cup was seen, but
    #    never from before the app started (a sighting loaded from
    #    yesterday shouldn't make the cup "lost" the instant we start).
    absent_from = state.started_at
    if last_seen_time is not None:
        absent_from = max(last_seen_time, state.started_at)
    cup_absent_sec = 0.0 if seen else max(now - absent_from, 0.0)

    # 5. Lost only when I'm here AND the cup has been gone N seconds.
    lost = me_in_view and cup_absent_sec >= config.N_SECONDS

    new = replace(
        state,
        last_cup=last_cup,
        last_me_time=last_me_time,
        me_in_view=me_in_view,
        score=score,
        last_update_time=now,
        seen=seen,
        last_seen_time=last_seen_time,
        cup_absent_sec=cup_absent_sec,
        lost=lost,
        anchor_box=anchor_box,
        anchor_time=anchor_time,
    )
    if verdicts:
        new = replace(new, cup_decisions=tuple(verdicts), cup_decisions_time=now)
    if detections:
        new = replace(new, last_raw=detections, last_raw_time=now)
    return new


# --- Text for the page and the voice answer ----------------------------

def status_text(state, now):
    """One short line for the top of the page."""
    if state.lost:
        return "LOST: your coffee has been gone for %d s" % state.cup_absent_sec
    if state.seen:
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
    if state.seen:
        return "Your coffee is right there, %s." % state.last_cup.zone
    return "Your coffee was last seen %s, %s." % (
        state.last_cup.zone,
        ago_text(now - state.last_cup.time),
    )


def to_dict(state, now):
    """Everything the web page needs, as plain JSON-friendly data."""
    d = asdict(state)
    d["status"] = status_text(state, now)
    d["anchor_status"] = anchor_status(state, now) if config.USE_ANCHOR else "off"
    d["anchor_age"] = None if state.anchor_time is None else now - state.anchor_time
    d["score_max"] = config.SCORE_MAX
    d["seen_score"] = config.SEEN_SCORE
    d["flags"] = {
        name: getattr(config, name)
        for name in ("FILTER_LABELS", "USE_PERSON_BOOST", "USE_ANCHOR",
                     "USE_ANCHOR_TTL", "USE_EVIDENCE_SCORE")
    }
    d["now"] = now
    return d
