# All tunable numbers and unverified guesses live here, in one place.
# Anything marked TODO(verify-on-board) is a guess until the spike
# output (or real use) confirms it.

import os

# --- Timer -----------------------------------------------------------

# Cup must be missing this many continuous seconds (while I'm in view)
# before it counts as "lost".
N_SECONDS = 10.0  # TODO(verify-on-board): tune after real use

# A person detection keeps "person in view" true for this long.
# Needed because the brick sends nothing when nothing is detected,
# and detections flicker frame to frame.
PERSON_TIMEOUT_SEC = 2.0  # TODO(verify-on-board): tune for flicker

# A cup seen within this many seconds counts as "in view right now"
# (for the spoken answer and the status line).
CUP_VISIBLE_SEC = 2.0

# How often main.py re-checks the timer when no detections arrive.
TICK_SEC = 0.5

# --- Detection -------------------------------------------------------

CUP_LABEL = "cup"
PERSON_LABEL = "person"

# The brick passes everything at or above this; tracker.py applies the
# real thresholds below. Low floor = tracker gets to see weak cups.
CONF_FLOOR = 0.3

# A brand-new cup must reach this confidence to be accepted.
CUP_START_CONF = 0.5

# --- Smarter cup acceptance ------------------------------------------
# Each USE_ flag switches one feature off so you can compare.

# While a person is in view, accept a new cup from this confidence
# (hands partly cover the cup, so confidence drops).
USE_PERSON_BOOST = True
CUP_START_CONF_WITH_PERSON = 0.4

# The "anchor" is the box of the last confident cup (>= CUP_START_CONF).
# A cup whose centre is within ANCHOR_NEAR_PX of the anchor's centre
# only needs CUP_NEAR_ANCHOR_CONF.
USE_ANCHOR = True
CUP_NEAR_ANCHOR_CONF = 0.3
ANCHOR_NEAR_PX = 40  # TODO(verify-on-board): about half a cup's width?

# Anti-phantom: with no confident cup for this long, the anchor expires
# and weak cups near it stop counting.
USE_ANCHOR_TTL = True
ANCHOR_TTL_SECONDS = 30.0  # TODO(verify-on-board)

# Person must reach this to count as "in view".
PERSON_MIN_CONF = 0.5  # TODO(verify-on-board)

# Drop every label except cup and person before the tracker sees it.
FILTER_LABELS = True

# --- Frame and zones -------------------------------------------------

# Size of the coordinate space the boxes are reported in.
# Verified on board 2026-10-03 (spike, Brio 100): max box corner = 640, 480.
FRAME_W = 640
FRAME_H = 480

# Named zones as fractions of the frame: (left, top, right, bottom),
# each from 0.0 to 1.0. The first zone containing the cup's centre wins.
# Default: a 3x2 grid. Rename/resize to match your desk.
ZONES = {  # TODO(verify-on-board): rename to real places once you see the camera view
    "top left": (0.00, 0.00, 0.33, 0.50),
    "top middle": (0.33, 0.00, 0.67, 0.50),
    "top right": (0.67, 0.00, 1.00, 0.50),
    "bottom left": (0.00, 0.50, 0.33, 1.00),
    "bottom middle": (0.33, 0.50, 0.67, 1.00),
    "bottom right": (0.67, 0.50, 1.00, 1.00),
}
UNKNOWN_ZONE = "somewhere in view"

# --- Storage ---------------------------------------------------------

# JSON file holding the last cup sighting, so it survives restarts.
STORE_PATH = os.path.join(  # TODO(verify-on-board): is the app folder writable?
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "last_seen.json"
)

# Don't rewrite the file on every frame: only when the zone changes,
# or at most this often while the cup sits still.
SAVE_EVERY_SEC = 30.0
