# Coffee Tracker app

## Run order on the board
1. Hardware: USB webcam + USB mic on a **powered** USB-C hub, App Lab in **Network Mode**.
2. Run `spike/` first (it's its own small app). Paste the `RAW:` and `MAX x2/y2` lines.
3. Update `python/config.py` (FRAME_W/H, ZONES) from the spike output.
4. Run this app. Open `<board-name>.local:7000`, click **Enable voice** once.

## Files
| File | Job |
|---|---|
| `app.yaml` | Declares the 3 bricks: video_object_detection, web_ui, keyword_spotting |
| `python/config.py` | Every tunable number and guess. Search `TODO(verify-on-board)` |
| `python/main.py` | Wiring only: bricks -> tracker -> page |
| `python/tracker.py` | Pure timer/state logic + status/answer text |
| `python/identity.py` | `is_me()` stub (any person = me) |
| `python/zones.py` | Box -> zone name |
| `python/store.py` | Last sighting <-> `data/last_seen.json` |
| `assets/` | Web page (video, status, last seen, answer + speech, debug) |
| `tests/` | Tests with fake detections, no board needed |

## Tests (on your Mac, no board, nothing to install)
```
cd coffee-tracker
python3 -m unittest discover tests -v
```
