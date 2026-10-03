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

# How often main.py re-checks the timer when no detections arrive.
TICK_SEC = 0.5

# --- Detection -------------------------------------------------------

CONFIDENCE = 0.5
CUP_LABEL = "cup"
PERSON_LABEL = "person"

# --- Frame and zones -------------------------------------------------

# Size of the coordinate space the boxes are reported in.
FRAME_W = 640  # TODO(verify-on-board): spike "MAX x2/y2" tells us
FRAME_H = 480  # TODO(verify-on-board): may be the model input size instead

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
