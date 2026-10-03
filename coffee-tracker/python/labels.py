# Cleans up raw detections before the tracker sees them.
# Pure functions: no bricks, no files, so they run (and test) anywhere.

import config


def normalize_detections(detections):
    """Map every CUP_LABELS label to "cup", keep "person", drop the rest.

    Each detection is copied with an extra "label" key holding the
    model's original label, so the debug panel can show "cup (vase)".
    Confidence and box are passed through unchanged.
    """
    result = {}
    for label, dets in detections.items():
        if label in config.CUP_LABELS:
            new_label = config.CUP_LABEL
        elif label == config.PERSON_LABEL:
            new_label = config.PERSON_LABEL
        else:
            continue
        for d in dets:
            result.setdefault(new_label, []).append(dict(d, label=label))
    return result


def count_labels(counts, detections):
    """Return a NEW dict: running count of every raw label (one per box)."""
    new = dict(counts)
    for label, dets in detections.items():
        new[label] = new.get(label, 0) + len(dets)
    return new
