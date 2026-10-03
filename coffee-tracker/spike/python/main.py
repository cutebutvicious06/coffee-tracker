# Stage 1, step 0: SPIKE.
# Goal: see the real shape of the detection dict on the board,
# especially the bounding box numbers. No tracking logic yet.

import time

from arduino.app_utils import App
from arduino.app_bricks.video_objectdetection import VideoObjectDetection

PRINT_EVERY_SEC = 2.0  # Don't flood the console: print at most this often

detection_stream = VideoObjectDetection(confidence=0.5, debounce_sec=0.0)

last_print = 0.0
max_x = 0
max_y = 0


def print_raw_detections(detections: dict):
  global last_print, max_x, max_y

  # Track the biggest box corner seen, to learn the coordinate scale
  # (e.g. 640x480 camera pixels, or the model's smaller input size).
  for values in detections.values():
    for value in values:
      box = value.get("bounding_box_xyxy")
      if box:
        max_x = max(max_x, box[2])
        max_y = max(max_y, box[3])

  now = time.time()
  if now - last_print < PRINT_EVERY_SEC:
    return
  last_print = now

  print("RAW:", repr(detections))
  print("MAX x2/y2 seen so far:", max_x, max_y)


detection_stream.on_detect_all(print_raw_detections)

App.run()
