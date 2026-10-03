# Turns a bounding box into a zone name like "top left".
# Pure functions: no bricks, no files, so they run (and test) anywhere.

import config


def box_center(box):
    """(x1, y1, x2, y2) -> (cx, cy), the middle of the box."""
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def zone_for_box(box, zones=None, frame_w=None, frame_h=None):
    """Return the name of the zone that contains the box's centre.

    Box is in pixels; zones are fractions of the frame (0.0-1.0).
    Returns config.UNKNOWN_ZONE if no zone matches.
    """
    zones = config.ZONES if zones is None else zones
    frame_w = config.FRAME_W if frame_w is None else frame_w
    frame_h = config.FRAME_H if frame_h is None else frame_h

    cx, cy = box_center(box)
    # Convert pixels to fractions, clamped so boxes slightly outside
    # the frame (or a wrong FRAME_W guess) still land in an edge zone.
    fx = min(max(cx / frame_w, 0.0), 1.0)
    fy = min(max(cy / frame_h, 0.0), 1.0)

    for name, (left, top, right, bottom) in zones.items():
        if left <= fx <= right and top <= fy <= bottom:
            return name
    return config.UNKNOWN_ZONE
