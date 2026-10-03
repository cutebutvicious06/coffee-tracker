# Decides whether "me" is in the frame.
# STUB: for now any person counts as me. Real recognition (Stage 2)
# replaces only this function; the tracker doesn't need to change.

import config


def is_me(detections):
    """True if the detections contain me. Currently: any person."""
    return len(detections.get(config.PERSON_LABEL, [])) > 0
