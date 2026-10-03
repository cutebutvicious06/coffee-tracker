// Browser side: shows what Python sends. No tracking logic here.
//   "state"  -> every TICK_SEC: status, last cup sighting, raw boxes
//   "answer" -> after "Hey Arduino" or the Ask button: show + speak it

const $ = id => document.getElementById(id);

// --- Live video --------------------------------------------------------
// The detection brick serves its own video page (with boxes drawn) on
// port 4912. Retry every second until it's up, like the reference apps.
const videoFrame = $('videoFrame');
const videoUrl = `http://${window.location.hostname}:4912/embed`;
const videoRetry = setInterval(() => { videoFrame.src = videoUrl; }, 1000);
videoFrame.onload = () => {
  clearInterval(videoRetry);
  $('videoPlaceholder').hidden = true;
  videoFrame.hidden = false;
};

// --- Connection to Python ---------------------------------------------
const ui = new WebUI();
ui.on_connect(() => { $('error').hidden = true; });
ui.on_disconnect(() => {
  $('error').textContent = 'Connection to the board lost.';
  $('error').hidden = false;
});
ui.on_message('state', showState);
ui.on_message('answer', showAnswer);

function showState(s) {
  $('status').textContent = s.status;
  $('status').classList.toggle('lost', s.lost);

  if (s.last_cup) {
    $('lastZone').textContent = s.last_cup.zone;
    const when = new Date(s.last_cup.time * 1000).toLocaleTimeString();
    const ago = Math.round(s.now - s.last_cup.time);
    $('lastTime').textContent = `${when} (${ago} s ago)`;
  }

  showDebug(s);
  if (s.last_raw_time) {
    const age = (s.now - s.last_raw_time).toFixed(1);
    // One line per detection: label, confidence, box (x1, y1, x2, y2)
    const lines = [];
    for (const [label, dets] of Object.entries(s.last_raw)) {
      for (const d of dets) {
        lines.push(`${label}  ${d.confidence.toFixed(2)}  [${d.bounding_box_xyxy.join(', ')}]`);
      }
    }
    $('debugRaw').textContent = `last detections (${age} s ago):\n` + lines.join('\n');
  }
}

// --- Debug panel -------------------------------------------------------
function showDebug(s) {
  $('debugSummary').textContent =
    `score: ${s.score.toFixed(2)} / ${s.score_max} (seen at ${s.seen_score}) | seen: ${s.seen}` +
    ` | me in view: ${s.me_in_view} | cup absent: ${s.cup_absent_sec.toFixed(1)} s | lost: ${s.lost}`;

  let anchor = `anchor: ${s.anchor_status}`;
  if (s.anchor_box) {
    anchor += ` | box [${s.anchor_box.join(', ')}] | last confident cup ${s.anchor_age.toFixed(1)} s ago`;
  }
  $('debugAnchor').textContent = anchor;

  $('debugFlags').textContent = Object.entries(s.flags)
    .map(([name, on]) => `${name}=${on ? 'on' : 'OFF'}`).join('  ');

  const tbody = $('cupTable').querySelector('tbody');
  tbody.innerHTML = '';
  if (s.cup_decisions_time) {
    const age = (s.now - s.cup_decisions_time).toFixed(1);
    $('cupTitle').textContent = `Cups in last frame with cups (${age} s ago)`;
    for (const c of s.cup_decisions) {
      const row = document.createElement('tr');
      row.className = c.accepted ? c.strength : 'rejected';
      const cells = [
        c.confidence.toFixed(2),
        c.accepted ? c.strength : 'rejected',
        c.reason,
        c.anchor_distance === null ? '-' : c.anchor_distance,
      ];
      for (const text of cells) {
        const td = document.createElement('td');
        td.textContent = text;
        row.appendChild(td);
      }
      tbody.appendChild(row);
    }
  }
}

// --- Answer + speech ---------------------------------------------------
// Browsers block speech until the user has clicked something on the
// page, so voice needs one click on "Enable voice" first.
let voiceOn = false;

$('voiceBtn').onclick = () => {
  voiceOn = true;
  $('voiceBtn').textContent = 'Voice on';
  $('voiceBtn').disabled = true;
  speak('Voice on.');
};
$('askBtn').onclick = () => ui.send_message('ask', {});

function showAnswer(msg) {
  $('answer').textContent = msg.text;
  if (voiceOn) speak(msg.text);
}

function speak(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel(); // don't queue up old answers
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}
