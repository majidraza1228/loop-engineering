#!/usr/bin/env python3
"""
demo_server.py — Loop engineering live demo.
Serves the UI and streams real loop output via SSE.

Usage:
  OPENAI_API_KEY=sk-... python demo_server.py
  open http://localhost:5050
"""

from __future__ import annotations
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, Response, request

ROOT = Path(__file__).parent
app = Flask(__name__)

_proc: subprocess.Popen | None = None
_q: queue.Queue = queue.Queue()
_lock = threading.Lock()


def _drain(proc: subprocess.Popen):
    for line in proc.stdout:
        _q.put(line.rstrip())
    _q.put(None)


@app.get("/")
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.post("/api/run")
def api_run():
    global _proc
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "once")
    report_only = data.get("reportOnly", True)

    with _lock:
        if _proc and _proc.poll() is None:
            return {"error": "already running"}, 409

        env = os.environ.copy()
        env["USE_LOCAL"] = "false"
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [sys.executable, "starters/minimal-loop/run.py", f"--mode={mode}"]
        if report_only:
            cmd.append("--report-only")

        _proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=ROOT, env=env, bufsize=1,
        )
        threading.Thread(target=_drain, args=(_proc,), daemon=True).start()

    return {"status": "started"}


@app.get("/api/stream")
def api_stream():
    def generate():
        while True:
            item = _q.get()
            if item is None:
                yield "event: done\ndata: \n\n"
                return
            yield f"data: {json.dumps(item)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/state")
def api_state():
    p = ROOT / "STATE.md"
    return p.read_text() if p.exists() else "# Loop State\n\n(not yet run)"


@app.post("/api/reset")
def api_reset():
    global _proc
    with _lock:
        if _proc and _proc.poll() is None:
            _proc.terminate()
        _proc = None
    while not _q.empty():
        try:
            _q.get_nowait()
        except Exception:
            break
    return {"status": "ok"}


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Loop Engineering — Live Demo</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
<style>
:root {
  --color-background-primary:   #1e1e2e;
  --color-background-secondary: #2a2a3e;
  --color-background-warning:   #3a2e1a;
  --color-background-success:   #1a2e1a;
  --color-background-danger:    #2e1a1a;
  --color-background-info:      #1a2234;
  --color-text-primary:         #e0e0f0;
  --color-text-secondary:       #a0a0c0;
  --color-text-tertiary:        #606080;
  --color-text-warning:         #EF9F27;
  --color-text-success:         #5DCAA5;
  --color-text-danger:          #F09595;
  --color-text-info:            #85B7EB;
  --color-border-secondary:     #3a3a5e;
  --color-border-tertiary:      #2e2e4e;
  --border-radius-lg: 10px;
  --border-radius-md: 6px;
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', Menlo, monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font-sans); background: #12121e; color: var(--color-text-primary); padding: 2rem; }
.container { max-width: 1100px; margin: 0 auto; }
h1 { font-size: 18px; font-weight: 500; margin-bottom: 4px; }
.subtitle { font-size: 13px; color: var(--color-text-tertiary); margin-bottom: 1.5rem; }

.shell { border: 0.5px solid var(--color-border-secondary); border-radius: var(--border-radius-lg); overflow: hidden; margin: 1rem 0; }
.shell-bar { background: var(--color-background-secondary); padding: 8px 14px; display: flex; align-items: center; gap: 8px; border-bottom: 0.5px solid var(--color-border-tertiary); }
.dot { width: 10px; height: 10px; border-radius: 50%; }
.d-red { background: #E24B4A; } .d-amber { background: #EF9F27; } .d-green { background: #639922; }
.shell-title { font-size: 12px; color: var(--color-text-tertiary); margin-left: 4px; }
.terminal { background: #111; padding: 14px 16px; min-height: 240px; max-height: 380px; overflow-y: auto; font-family: var(--font-mono); font-size: 12px; line-height: 1.7; }
.line { display: block; margin: 1px 0; white-space: pre-wrap; word-break: break-all; }
.c-dim  { color: #555; }
.c-norm { color: #ccc; }
.c-green { color: #5DCAA5; }
.c-amber { color: #EF9F27; }
.c-red   { color: #F09595; }
.c-blue  { color: #85B7EB; }
.c-bold  { color: #fff; font-weight: 500; }

.panels { display: grid; grid-template-columns: 1fr 1.4fr; gap: 12px; }
.card { background: var(--color-background-primary); border: 0.5px solid var(--color-border-tertiary); border-radius: var(--border-radius-lg); padding: 1rem 1.25rem; }
.card-label { font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: .05em; color: var(--color-text-tertiary); margin-bottom: 8px; }

.step-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 0.5px solid var(--color-border-tertiary); font-size: 13px; }
.step-row:last-child { border-bottom: none; }
.step-icon { width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; flex-shrink: 0; }
.si-wait { background: var(--color-background-secondary); color: var(--color-text-tertiary); }
.si-run  { background: var(--color-background-warning);   color: var(--color-text-warning); }
.si-done { background: var(--color-background-success);   color: var(--color-text-success); }
.si-fail { background: var(--color-background-danger);    color: var(--color-text-danger); }
.step-name { flex: 1; color: var(--color-text-secondary); }
.step-name.active { color: var(--color-text-primary); font-weight: 500; }
.step-badge { font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 500; }
.sb-pending { background: var(--color-background-secondary); color: var(--color-text-tertiary); }
.sb-running { background: var(--color-background-warning);   color: var(--color-text-warning); }
.sb-done    { background: var(--color-background-success);   color: var(--color-text-success); }
.sb-fail    { background: var(--color-background-danger);    color: var(--color-text-danger); }
.sb-skip    { background: var(--color-background-secondary); color: var(--color-text-tertiary); }

.controls { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; align-items: center; }
.btn { padding: 7px 16px; font-size: 13px; border: 0.5px solid var(--color-border-secondary); border-radius: var(--border-radius-md); background: transparent; color: var(--color-text-primary); cursor: pointer; transition: background .12s; display: flex; align-items: center; gap: 6px; font-family: var(--font-sans); }
.btn:hover { background: var(--color-background-secondary); }
.btn:disabled { opacity: .4; cursor: not-allowed; }
.btn-primary { border-color: var(--color-border-info); color: var(--color-text-info); }
.btn-primary:hover { background: var(--color-background-info); }

.score-bar-wrap { height: 6px; background: var(--color-background-secondary); border-radius: 3px; overflow: hidden; margin-top: 4px; }
.score-bar { height: 6px; border-radius: 3px; transition: width .4s; background: #5DCAA5; }
.verdict { border-radius: var(--border-radius-md); padding: 8px 12px; font-size: 12px; margin-top: 8px; display: none; }
.verdict-pass { background: var(--color-background-success); color: var(--color-text-success); }
.verdict-fail { background: var(--color-background-danger);  color: var(--color-text-danger); }
.pr-badge { display: none; align-items: center; gap: 5px; font-size: 12px; padding: 4px 10px; border-radius: 12px; background: var(--color-background-info); color: var(--color-text-info); font-weight: 500; margin-top: 6px; }

#loop-status { font-size: 12px; padding: 3px 10px; border-radius: 12px; background: var(--color-background-secondary); color: var(--color-text-secondary); }
select.btn { padding: 6px 12px; }
</style>
</head>
<body>
<div class="container">

<h1>Loop Engineering — Live Demo</h1>
<p class="subtitle">Real agent loop running against this repo · powered by OpenAI</p>

<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
  <div id="loop-status">idle</div>
</div>

<div class="panels">

  <div class="card">
    <div class="card-label">Loop steps</div>
    <div id="steps-list">
      <div class="step-row">
        <div class="step-icon si-wait" id="ic-auto"><i class="ti ti-clock-play"></i></div>
        <span class="step-name" id="sn-auto">Automation fires</span>
        <span class="step-badge sb-pending" id="sb-auto">pending</span>
      </div>
      <div class="step-row">
        <div class="step-icon si-wait" id="ic-triage"><i class="ti ti-list-search"></i></div>
        <span class="step-name" id="sn-triage">Triage skill runs</span>
        <span class="step-badge sb-pending" id="sb-triage">pending</span>
      </div>
      <div class="step-row">
        <div class="step-icon si-wait" id="ic-wt"><i class="ti ti-git-branch"></i></div>
        <span class="step-name" id="sn-wt">Worktree created</span>
        <span class="step-badge sb-pending" id="sb-wt">pending</span>
      </div>
      <div class="step-row">
        <div class="step-icon si-wait" id="ic-maker"><i class="ti ti-code"></i></div>
        <span class="step-name" id="sn-maker">Maker agent writes fix</span>
        <span class="step-badge sb-pending" id="sb-maker">pending</span>
      </div>
      <div class="step-row">
        <div class="step-icon si-wait" id="ic-checker"><i class="ti ti-shield-check"></i></div>
        <span class="step-name" id="sn-checker">Checker agent reviews</span>
        <span class="step-badge sb-pending" id="sb-checker">pending</span>
      </div>
      <div class="step-row">
        <div class="step-icon si-wait" id="ic-memory"><i class="ti ti-database"></i></div>
        <span class="step-name" id="sn-memory">STATE.md updated</span>
        <span class="step-badge sb-pending" id="sb-memory">pending</span>
      </div>
      <div class="step-row">
        <div class="step-icon si-wait" id="ic-pr"><i class="ti ti-git-pull-request"></i></div>
        <span class="step-name" id="sn-pr">PR + Slack notify</span>
        <span class="step-badge sb-pending" id="sb-pr">pending</span>
      </div>
    </div>
  </div>

  <div style="display:flex;flex-direction:column;gap:12px">

    <div class="shell">
      <div class="shell-bar">
        <div class="dot d-red"></div><div class="dot d-amber"></div><div class="dot d-green"></div>
        <span class="shell-title">terminal — starters/minimal-loop/run.py</span>
      </div>
      <div class="terminal" id="terminal">
        <span class="line c-dim">$ python starters/minimal-loop/run.py --mode once</span>
        <span class="line c-dim">Press "Run loop" to start...</span>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="card" style="padding:.875rem 1rem">
        <div class="card-label">Checker score</div>
        <div style="font-size:22px;font-weight:500;color:var(--color-text-primary)" id="score-num">—</div>
        <div class="score-bar-wrap"><div class="score-bar" id="score-bar" style="width:0%"></div></div>
        <div id="verdict-box" class="verdict"></div>
      </div>
      <div class="card" style="padding:.875rem 1rem">
        <div class="card-label">Memory / PR</div>
        <div style="font-size:12px;color:var(--color-text-secondary);line-height:1.6" id="memory-summary">STATE.md not yet updated</div>
        <div id="pr-badge" class="pr-badge"><i class="ti ti-git-pull-request"></i> PR opened</div>
      </div>
    </div>

  </div>
</div>

<div class="shell" style="margin-top:12px">
  <div class="shell-bar">
    <div class="dot d-red"></div><div class="dot d-amber"></div><div class="dot d-green"></div>
    <span class="shell-title">STATE.md — loop memory</span>
  </div>
  <div style="padding:12px 16px;max-height:160px;overflow-y:auto">
    <pre style="font-family:var(--font-mono);font-size:11px;line-height:1.7;color:var(--color-text-secondary);white-space:pre-wrap;overflow-y:auto" id="state-md">Loading...</pre>
  </div>
</div>

<div class="controls">
  <select id="mode-select" class="btn" onchange="updateModeLabel()">
    <option value="triage-only">Triage only (safe, read-only)</option>
    <option value="full">Full cycle (triage + auto-fix)</option>
  </select>
  <button class="btn btn-primary" id="btn-run" onclick="startLoop()">
    <i class="ti ti-player-play"></i> Run loop
  </button>
  <button class="btn" id="btn-reset" onclick="resetLoop()" disabled>
    <i class="ti ti-refresh"></i> Reset
  </button>
</div>

</div>
<script>
const term   = document.getElementById('terminal');
const stateEl = document.getElementById('state-md');
let es = null, running = false;
let stepState = {}, triageStarted = false;

const STEP_IDS = ['auto','triage','wt','maker','checker','memory','pr'];
const STEP_ICONS = {
  auto:'ti-clock-play', triage:'ti-list-search', wt:'ti-git-branch',
  maker:'ti-code', checker:'ti-shield-check', memory:'ti-database', pr:'ti-git-pull-request'
};

// ── steps ─────────────────────────────────────────────────────────────────────

function setStep(id, state) {
  const ic = document.getElementById(`ic-${id}`);
  const sb = document.getElementById(`sb-${id}`);
  const sn = document.getElementById(`sn-${id}`);
  if (!ic || stepState[id] === 'done' || stepState[id] === 'fail') return;
  stepState[id] = state;
  if (state === 'running') {
    ic.className = 'step-icon si-run';
    ic.innerHTML = '<i class="ti ti-loader-2"></i>';
    sb.className = 'step-badge sb-running'; sb.textContent = 'running';
    sn.className = 'step-name active';
  } else if (state === 'done') {
    ic.className = 'step-icon si-done';
    ic.innerHTML = '<i class="ti ti-check"></i>';
    sb.className = 'step-badge sb-done'; sb.textContent = 'done';
    sn.className = 'step-name';
  } else if (state === 'fail') {
    ic.className = 'step-icon si-fail';
    ic.innerHTML = '<i class="ti ti-x"></i>';
    sb.className = 'step-badge sb-fail'; sb.textContent = 'failed';
    sn.className = 'step-name';
  } else if (state === 'skip') {
    ic.innerHTML = `<i class="ti ${STEP_ICONS[id]}"></i>`;
    sb.className = 'step-badge sb-skip'; sb.textContent = 'skipped';
    sn.className = 'step-name';
  }
}

function setStatus(text, color='secondary') {
  const el = document.getElementById('loop-status');
  el.textContent = text;
  el.style.background = `var(--color-background-${color})`;
  el.style.color = `var(--color-text-${color})`;
}

// ── line → color ──────────────────────────────────────────────────────────────

function colorOf(line) {
  if (!line.trim()) return 'c-dim';
  if (line.startsWith('===') || line.includes('LOOP CYCLE')) return 'c-bold';
  if (line.includes('[triage]') || line.startsWith('Findings')) return 'c-amber';
  if (line.includes('[maker]'))   return 'c-blue';
  if (line.includes('[checker]') && line.includes('pass'))  return 'c-green';
  if (line.includes('[checker]') && line.includes('fail'))  return 'c-red';
  if (line.includes('[checker]')) return 'c-amber';
  if (line.includes('[github]') || line.includes('[slack]') || line.includes('[debug]')) return 'c-dim';
  if (line.includes('[minimal-loop]') || line.includes('[loop]')) return 'c-norm';
  if (line.trim().startsWith('- ')) return 'c-norm';
  return 'c-norm';
}

// ── line → step transitions ───────────────────────────────────────────────────

function processLine(line) {
  // automation + triage start
  if ((line.includes('[minimal-loop]') || line.includes('[debug]')) && !triageStarted) {
    triageStarted = true;
    setStep('auto', 'done');
    setStep('triage', 'running');
  }
  // triage done signals
  if (line.includes('Report-only') || line.includes('No open tasks') || line.includes('[minimal-loop] Fixing:')) {
    setStep('triage', 'done');
  }
  // worktree
  if (line.includes('[minimal-loop] Fixing:') || line.includes('worktree add')) {
    setStep('wt', 'running');
  }
  if (line.includes('[maker] attempt')) {
    setStep('wt', 'done');
    setStep('maker', 'running');
  }
  // checker
  if (line.includes('[checker]')) {
    setStep('maker', 'done');
    setStep('checker', 'running');
  }
  if (line.includes('[checker] pass') || line.includes('[checker] fail')) {
    const pass = line.includes('pass');
    setStep('checker', pass ? 'done' : 'fail');
    const m = line.match(/score (\d+)\/10/);
    if (m) updateScore(parseInt(m[1]), pass);
    if (pass) setStep('memory', 'running');
  }
  // memory / pr
  if (line.includes('STATE.md')) {
    setStep('memory', 'done');
    document.getElementById('memory-summary').textContent = 'Task marked done\nRun logged';
    fetchState();
  }
  if (line.includes('[slack]') || line.includes('[github]')) {
    setStep('memory', 'done');
    setStep('pr', 'running');
  }
  if (line.includes('PR #') && line.includes('opened')) {
    setStep('pr', 'done');
    document.getElementById('pr-badge').style.display = 'inline-flex';
    document.getElementById('memory-summary').textContent = 'Task done · PR opened';
  }
}

function updateScore(score, pass) {
  document.getElementById('score-num').textContent = `${score}/10`;
  const bar = document.getElementById('score-bar');
  bar.style.width = `${score * 10}%`;
  bar.style.background = score >= 7 ? '#5DCAA5' : score >= 5 ? '#EF9F27' : '#E24B4A';
  const vbox = document.getElementById('verdict-box');
  vbox.style.display = 'block';
  vbox.className = `verdict ${pass ? 'verdict-pass' : 'verdict-fail'}`;
  vbox.textContent = pass ? `✓ Passed (score ${score}/10)` : `✗ Failed — retrying`;
}

// ── terminal ──────────────────────────────────────────────────────────────────

function log(text, cls) {
  const span = document.createElement('span');
  span.className = `line ${cls || colorOf(text)}`;
  span.textContent = text;
  term.appendChild(span);
  term.scrollTop = term.scrollHeight;
}

// ── state.md ──────────────────────────────────────────────────────────────────

function fetchState() {
  fetch('/api/state').then(r => r.text()).then(t => { stateEl.textContent = t; });
}

// ── run ───────────────────────────────────────────────────────────────────────

function updateModeLabel() {
  const m = document.getElementById('mode-select').value;
  const title = document.querySelector('.shell-title');
  if (title) title.textContent = m === 'full'
    ? 'terminal — starters/minimal-loop/run.py --mode once'
    : 'terminal — starters/minimal-loop/run.py --mode once --report-only';
}

async function startLoop() {
  if (running) return;
  running = true; triageStarted = false; stepState = {};
  const mode = document.getElementById('mode-select').value;
  const reportOnly = mode !== 'full';

  document.getElementById('btn-run').disabled = true;
  document.getElementById('btn-reset').disabled = false;
  document.getElementById('mode-select').disabled = true;
  term.innerHTML = '';
  setStatus('running', 'warning');

  const cmdSuffix = reportOnly ? ' --report-only' : '';
  log(`$ python starters/minimal-loop/run.py --mode once${cmdSuffix}`, 'c-dim');
  log('', 'c-dim');

  const resp = await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: 'once', reportOnly }),
  });

  if (!resp.ok) {
    log('[error] Could not start. Is OPENAI_API_KEY set?', 'c-red');
    setStatus('error', 'danger');
    running = false;
    return;
  }

  es = new EventSource('/api/stream');
  es.onmessage = e => {
    const line = JSON.parse(e.data);
    processLine(line);
    log(line);
  };
  es.addEventListener('done', () => { es.close(); es = null; onComplete(); });
  es.onerror = () => { es && es.close(); es = null; onComplete(); };
}

function onComplete() {
  running = false;
  // flush: running → done, never-touched → skip
  STEP_IDS.forEach(id => {
    if (stepState[id] === 'running') setStep(id, 'done');
    else if (!stepState[id]) {
      const ic = document.getElementById(`ic-${id}`);
      const sb = document.getElementById(`sb-${id}`);
      if (ic && sb) { ic.innerHTML = `<i class="ti ${STEP_ICONS[id]}"></i>`; sb.className = 'step-badge sb-skip'; sb.textContent = 'skipped'; }
    }
  });
  if (triageStarted && !stepState.triage) setStep('triage', 'done');
  setStatus('complete ✓', 'success');
  fetchState();
  document.getElementById('btn-run').disabled = false;
}

// ── reset ─────────────────────────────────────────────────────────────────────

function resetLoop() {
  fetch('/api/reset', { method: 'POST' });
  if (es) { es.close(); es = null; }
  running = false; stepState = {}; triageStarted = false;
  term.innerHTML = '<span class="line c-dim">$ python starters/minimal-loop/run.py --mode once</span><span class="line c-dim">Press "Run loop" to start...</span>';
  STEP_IDS.forEach(id => {
    const ic = document.getElementById(`ic-${id}`);
    const sb = document.getElementById(`sb-${id}`);
    const sn = document.getElementById(`sn-${id}`);
    ic.className = 'step-icon si-wait';
    ic.innerHTML = `<i class="ti ${STEP_ICONS[id]}"></i>`;
    sb.className = 'step-badge sb-pending'; sb.textContent = 'pending';
    sn.className = 'step-name';
  });
  document.getElementById('score-num').textContent = '—';
  document.getElementById('score-bar').style.width = '0%';
  document.getElementById('verdict-box').style.display = 'none';
  document.getElementById('pr-badge').style.display = 'none';
  document.getElementById('memory-summary').textContent = 'STATE.md not yet updated';
  document.getElementById('btn-run').disabled = false;
  document.getElementById('btn-reset').disabled = true;
  document.getElementById('mode-select').disabled = false;
  setStatus('idle');
  fetchState();
}

fetchState();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.")
        print("Run:  OPENAI_API_KEY=sk-... python demo_server.py")
        sys.exit(1)
    print("Loop demo → http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
