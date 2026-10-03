# Saves/loads the last cup sighting as a small JSON file, so the answer
# survives an app restart. Never crashes the app: if the file can't be
# read or written, it logs and carries on.

import json
import os

import config
from tracker import CupSighting


def should_save(saved, current):
    """Decide if `current` is worth writing to disk.

    Saves when there's a new zone, or every SAVE_EVERY_SEC while the cup
    sits still. Writing every frame would wear out the board's storage.
    """
    if current is None:
        return False
    if saved is None:
        return True
    if current.zone != saved.zone:
        return True
    return current.time - saved.time >= config.SAVE_EVERY_SEC


def save(sighting, path=None):
    path = config.STORE_PATH if path is None else path
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(
                {
                    "zone": sighting.zone,
                    "box": list(sighting.box),
                    "confidence": sighting.confidence,
                    "time": sighting.time,
                },
                f,
            )
        os.replace(tmp, path)  # write-then-rename: no half-written file on power loss
        return True
    except OSError as e:
        print("store: could not save %s: %s" % (path, e))
        return False


def load(path=None):
    """Return the saved CupSighting, or None if missing/broken."""
    path = config.STORE_PATH if path is None else path
    try:
        with open(path) as f:
            d = json.load(f)
        return CupSighting(
            zone=d["zone"],
            box=tuple(d["box"]),
            confidence=d["confidence"],
            time=d["time"],
        )
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("store: ignoring unreadable %s: %s" % (path, e))
        return None
