# Reference examples — summaries

Source: `reference/` and
`useme/*.zip`. Edge AI Assistant exists **only** as a zip in `useme/`.

All examples target the **Arduino UNO Q** (Linux side runs Python, MCU side runs
an Arduino sketch). Camera/mic examples need **Network Mode** + a powered USB-C hub.

---

## 1. Detect Objects on Camera
- **Does:** Live USB-camera feed, detects general objects (cat, cup, cell phone,
  clock, dog, potted plant…), logs label + confidence in a web page.
- **Bricks:** `arduino:video_object_detection` (default model), `arduino:web_ui`.
- **Python ↔ sketch:** No sketch. Python only.
- **Python ↔ browser:**
  - `VideoObjectDetection(confidence=0.5, debounce_sec=0.0)`
  - `on_detect_all(cb)` → `cb(detections: dict)`; shape is
    `{label: [ {"confidence": ...}, ... ]}` (a list per label).
  - `ui.send_message("detection", {...})` pushes to the browser over WebSocket.
  - `ui.on_message("override_th", ...)` receives the slider value.
  - The **video itself** (with boxes drawn) is served by the brick on port
    **4912** at `/embed`; the page shows it in an `<iframe>`.

## 2. Face Detector on Camera
- **Does:** Same as #1 but detects **faces** (not *whose* face).
- **Bricks:** `arduino:video_object_detection` with `model: face-detection`,
  `arduino:web_ui`.
- **Python ↔ sketch:** No sketch.
- **Notable:** Shows `on_detect("face", cb)` — a per-label callback with no
  arguments, alongside `on_detect_all`. The model is chosen in `app.yaml`,
  not in Python.

## 3. Object Hunting
- **Does:** Game: find book, bottle, chair, cup, cell phone on camera.
- **Bricks:** `arduino:video_object_detection` (default model), `arduino:web_ui`.
- **Python ↔ sketch:** No sketch.
- **Notable:** Python just forwards labels; all game logic lives in
  `assets/app.js`. Treats `detections` values loosely (only uses the key).

## 4. Hey Arduino
- **Does:** Say "Hey Arduino" → heart animation on the board's LED matrix.
- **Bricks:** `arduino:keyword_spotting` (one pre-trained keyword: `hey_arduino`).
- **Python ↔ sketch (the only example with a sketch):**
  - Python: `spotter.on_detect("hey_arduino", cb)`; `cb` runs
    `Bridge.call("keyword_detected")`.
  - Sketch: `Bridge.begin(); Bridge.provide("keyword_detected", wake_up);`
    (`Arduino_RouterBridge.h`). `wake_up()` plays the animation.
  - So: **Python calls a named function that the sketch registered.**
- **Files:** `sketch/sketch.ino`, `sketch/heart_frames.h`,
  `sketch/sketch.yaml` (platform `arduino:zephyr`). No web UI.

## 5. Edge AI Assistant (zip only)
- **Does:** Chatbot running a local LLM, web chat UI.
- **Bricks:** `arduino:llm` (`model: llamacpp:gemma-3-1b-it-Q4_0`),
  `arduino:web_ui`.
- **Python ↔ sketch:** No sketch.
- **Notable:** Multiple Python files (`main.py` imports `prompts.py`, reads
  `system_prompt.txt`). Streams tokens with `llm.chat_stream()` →
  `ui.send_message("response", chunk)`.

---

## Common patterns
- Every `main.py` ends with `App.run()` (keeps bricks + callbacks alive).
- Bricks are objects you create in Python (`WebUI()`, `VideoObjectDetection()`,
  `KeywordSpotting()`, `LargeLanguageModel()`), **and** declared in `app.yaml`.
- Browser side always uses `libs/arduino.js` + `socket.io` → `new WebUI()`,
  `ui.on_message(...)`, `ui.send_message(...)`. Web UI is on port **7000**.
- **No example uses bounding-box coordinates** in Python, but the brick
  provides them. Verified on the board (spike, 2026-10-03):
  `{label: [{"confidence": 0.81, "bounding_box_xyxy": (511, 357, 640, 480)}]}`
  — boxes are in camera pixels, 640x480.
