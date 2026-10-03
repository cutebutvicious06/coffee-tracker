# Wiring only: connects the bricks to tracker.py / store.py.
# All decisions live in tracker.py so they can be tested off the board.

import threading
import time

from arduino.app_utils import App
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from arduino.app_bricks.keyword_spotting import KeywordSpotting

import config
import labels
import store
import tracker

ui = WebUI()
detection_stream = VideoObjectDetection(confidence=config.CONFIDENCE, debounce_sec=0.0)
spotter = KeywordSpotting()  # TODO(verify-on-board): does the app still start with no mic plugged in?

# Detection callbacks run on brick threads, the loop below on the main
# thread. The lock stops them updating the state at the same time.
lock = threading.Lock()
state = tracker.new_state(time.time(), last_cup=store.load())
saved = state.last_cup


def apply(detections):
    global state, saved
    with lock:
        state = tracker.update(state, detections, time.time())
        if store.should_save(saved, state.last_cup) and store.save(state.last_cup):
            saved = state.last_cup


label_counts = {}  # every raw label seen, for the debug panel


def on_detections(detections: dict):
    global label_counts
    with lock:
        label_counts = labels.count_labels(label_counts, detections)
    apply(labels.normalize_detections(detections))


def send_answer():
    text = tracker.answer_text(state, time.time())
    ui.send_message("answer", {"text": text})


def on_keyword():
    send_answer()


def on_ask(sid, data):
    # "Ask" button on the page: same answer, handy for testing without a mic.
    send_answer()


detection_stream.on_detect_all(on_detections)
spotter.on_detect("hey_arduino", on_keyword)
ui.on_message("ask", on_ask)


def loop():
    # The brick sends nothing when it sees nothing, so tick the timer
    # with an empty frame, then push the latest state to the page.
    apply({})
    message = tracker.to_dict(state, time.time())
    message["label_counts"] = label_counts
    message["cup_labels"] = config.CUP_LABELS
    ui.send_message("state", message)
    time.sleep(config.TICK_SEC)


App.run(user_loop=loop)
