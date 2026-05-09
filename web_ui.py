#!/usr/bin/env python3
# =============================================================================
# web_ui.py — OSINT Email Intelligence Tool v2 — Web Interface
# Usage: python web_ui.py
# Then open: http://127.0.0.1:5000
# =============================================================================

import json, sys, os, threading
sys.path.insert(0, os.path.dirname(__file__))

try:
    from flask import Flask, request, jsonify, Response
    _FLASK = True
except ImportError:
    _FLASK = False

import config
from main import run_analysis

app = Flask(__name__) if _FLASK else None

# ── Embedded HTML (single-file UI, no static folder needed) ─────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OSINT · Email Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  /* ── Reset & Base ── */
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:       #080c10;
    --bg2:      #0d1117;
    --bg3:      #131920;
    --border:   #1e2d3d;
    --border2:  #243447;
    --text:     #c9d1d9;
    --text2:    #8b949e;
    --text3:    #58677a;
    --accent:   #00d4ff;
    --accent2:  #0099cc;
    --green:    #39d353;
    --red:      #f85149;
    --yellow:   #e3b341;
    --orange:   #f0883e;
    --purple:   #bc8cff;
    --glow:     0 0 20px rgba(0,212,255,.15);
    --glow2:    0 0 40px rgba(0,212,255,.08);
  }
  html { scroll-behavior: smooth; }
  body {
    font-family: 'JetBrains Mono', monospace;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* ── Scanline overlay ── */
  body::before {
    content: '';
    position: fixed; inset: 0; pointer-events: none; z-index: 1000;
    background: repeating-linear-gradient(
      0deg, transparent, transparent 2px,
      rgba(0,0,0,.03) 2px, rgba(0,0,0,.03) 4px
    );
  }

  /* ── Grid bg ── */
  body::after {
    content: '';
    position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background-image:
      linear-gradient(var(--border) 1px, transparent 1px),
      linear-gradient(90deg, var(--border) 1px, transparent 1px);
    background-size: 40px 40px;
    opacity: .25;
  }

  /* ── Layout ── */
  .wrap { position: relative; z-index: 1; max-width: 1100px; margin: 0 auto; padding: 0 24px 80px; }

  /* ── Header ── */
  header {
    padding: 48px 0 32px;
    display: flex; align-items: center; gap: 20px;
  }
  .logo-mark {
    width: 48px; height: 48px;
    border: 2px solid var(--accent);
    display: grid; place-items: center;
    font-family: 'Syne', sans-serif; font-weight: 800;
    font-size: 18px; color: var(--accent);
    box-shadow: var(--glow), inset 0 0 12px rgba(0,212,255,.05);
    animation: pulse 3s ease-in-out infinite;
    flex-shrink: 0;
  }
  @keyframes pulse {
    0%,100% { box-shadow: var(--glow), inset 0 0 12px rgba(0,212,255,.05); }
    50%      { box-shadow: 0 0 30px rgba(0,212,255,.3), inset 0 0 20px rgba(0,212,255,.1); }
  }
  .title-block h1 {
    font-family: 'Syne', sans-serif; font-weight: 800;
    font-size: clamp(20px, 4vw, 28px); color: var(--accent);
    letter-spacing: -.5px; line-height: 1.1;
  }
  .title-block p { font-size: 11px; color: var(--text3); letter-spacing: 2px; text-transform: uppercase; margin-top: 4px; }

  /* ── Search bar ── */
  .search-section { margin-bottom: 32px; }
  .search-box {
    display: flex; gap: 0;
    border: 1px solid var(--border2);
    background: var(--bg2);
    transition: border-color .2s, box-shadow .2s;
  }
  .search-box:focus-within {
    border-color: var(--accent);
    box-shadow: var(--glow);
  }
  .search-prefix {
    padding: 0 16px;
    display: flex; align-items: center;
    color: var(--accent); font-size: 13px; font-weight: 600;
    border-right: 1px solid var(--border2);
    user-select: none; white-space: nowrap;
  }
  #emailInput {
    flex: 1; padding: 16px 20px;
    background: transparent; border: none; outline: none;
    color: var(--text); font-family: 'JetBrains Mono', monospace; font-size: 15px;
  }
  #emailInput::placeholder { color: var(--text3); }
  #scanBtn {
    padding: 16px 32px;
    background: var(--accent); border: none;
    color: var(--bg); font-family: 'Syne', sans-serif; font-weight: 800;
    font-size: 13px; letter-spacing: 1px; text-transform: uppercase;
    cursor: pointer; transition: background .2s, transform .1s;
    white-space: nowrap;
  }
  #scanBtn:hover  { background: #33ddff; }
  #scanBtn:active { transform: scale(.98); }
  #scanBtn:disabled { background: var(--border2); color: var(--text3); cursor: not-allowed; }

  /* ── Status bar ── */
  #statusBar {
    display: none; padding: 10px 16px;
    background: var(--bg3); border: 1px solid var(--border);
    border-top: none; font-size: 11px; color: var(--text2);
    align-items: center; gap: 10px;
  }
  #statusBar.active { display: flex; }
  .spinner {
    width: 12px; height: 12px; border: 2px solid var(--border2);
    border-top-color: var(--accent); border-radius: 50%;
    animation: spin .7s linear infinite; flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Results grid ── */
  #results { display: none; }
  #results.visible { display: block; }

  /* ── Section cards ── */
  .card {
    background: var(--bg2); border: 1px solid var(--border);
    margin-bottom: 16px; overflow: hidden;
    animation: fadeUp .4s ease both;
  }
  @keyframes fadeUp { from { opacity:0; transform: translateY(12px); } to { opacity:1; transform: none; } }
  .card:nth-child(1) { animation-delay: .05s; }
  .card:nth-child(2) { animation-delay: .1s;  }
  .card:nth-child(3) { animation-delay: .15s; }
  .card:nth-child(4) { animation-delay: .2s;  }
  .card:nth-child(5) { animation-delay: .25s; }
  .card:nth-child(6) { animation-delay: .3s;  }
  .card:nth-child(7) { animation-delay: .35s; }

  .card-header {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 20px; cursor: pointer;
    border-bottom: 1px solid var(--border);
    user-select: none;
  }
  .card-header:hover { background: var(--bg3); }
  .card-icon { font-size: 16px; width: 24px; text-align: center; }
  .card-title { font-family: 'Syne', sans-serif; font-weight: 600; font-size: 13px; letter-spacing: .5px; }
  .card-badge {
    margin-left: auto; font-size: 10px; padding: 2px 8px;
    background: var(--bg3); border: 1px solid var(--border2);
    color: var(--text2); letter-spacing: 1px;
  }
  .card-badge.green  { border-color: var(--green);  color: var(--green); }
  .card-badge.red    { border-color: var(--red);    color: var(--red); }
  .card-badge.yellow { border-color: var(--yellow); color: var(--yellow); }
  .card-badge.cyan   { border-color: var(--accent); color: var(--accent); }
  .card-toggle { color: var(--text3); font-size: 12px; margin-left: 8px; transition: transform .2s; }
  .card.collapsed .card-toggle { transform: rotate(-90deg); }
  .card-body { padding: 20px; }
  .card.collapsed .card-body { display: none; }

  /* ── KV rows ── */
  .kv { display: grid; grid-template-columns: 180px 1fr; gap: 8px 16px; align-items: start; }
  .kv-key { color: var(--text3); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; padding-top: 2px; }
  .kv-val { color: var(--text); font-size: 12px; word-break: break-all; }
  .kv-val a { color: var(--accent); text-decoration: none; }
  .kv-val a:hover { text-decoration: underline; }

  /* ── Divider within card ── */
  .cd { border: none; border-top: 1px solid var(--border); margin: 16px 0; }

  /* ── Breach list ── */
  .breach-item {
    padding: 10px 14px; margin-bottom: 8px;
    border-left: 3px solid var(--red); background: rgba(248,81,73,.05);
    display: grid; grid-template-columns: 1fr auto; gap: 4px;
  }
  .breach-name { font-weight: 600; font-size: 12px; color: var(--red); }
  .breach-date { font-size: 10px; color: var(--text3); text-align: right; }
  .breach-data { font-size: 10px; color: var(--text2); grid-column: 1/-1; margin-top: 4px; }
  .breach-count { font-size: 10px; color: var(--yellow); }
  .paste-item {
    padding: 8px 12px; margin-bottom: 6px;
    border-left: 3px solid var(--yellow); background: rgba(227,179,65,.05);
    font-size: 11px;
  }

  /* ── Platform grid ── */
  .platform-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px;
  }
  .platform-chip {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; border: 1px solid var(--border);
    font-size: 11px; transition: border-color .2s;
  }
  .platform-chip.found    { border-color: var(--green);  background: rgba(57,211,83,.05); }
  .platform-chip.notfound { opacity: .45; }
  .platform-chip .dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
  .platform-chip.found    .dot { background: var(--green); box-shadow: 0 0 6px var(--green); }
  .platform-chip.notfound .dot { background: var(--text3); }
  .platform-name  { font-weight: 600; }
  .platform-user  { color: var(--text3); font-size: 10px; }

  /* ── URL list ── */
  .url-list { display: flex; flex-direction: column; gap: 6px; }
  .url-item {
    padding: 8px 12px; background: var(--bg3); border: 1px solid var(--border);
    font-size: 11px; word-break: break-all;
    display: flex; gap: 10px; align-items: flex-start;
  }
  .url-item a { color: var(--accent); text-decoration: none; flex: 1; }
  .url-item a:hover { text-decoration: underline; }
  .url-idx { color: var(--text3); flex-shrink: 0; }

  /* ── Score bar ── */
  .score-section { display: flex; gap: 24px; align-items: center; flex-wrap: wrap; margin-bottom: 20px; }
  .score-circle {
    width: 90px; height: 90px; border-radius: 50%;
    border: 3px solid var(--accent); display: grid; place-items: center;
    box-shadow: var(--glow); flex-shrink: 0;
    position: relative;
  }
  .score-number { font-family: 'Syne', sans-serif; font-size: 28px; font-weight: 800; color: var(--accent); }
  .score-label  { font-size: 9px; color: var(--text3); text-transform: uppercase; letter-spacing: 2px; position: absolute; bottom: 14px; }
  .confidence-badge {
    padding: 6px 18px; font-family: 'Syne', sans-serif; font-weight: 800;
    font-size: 14px; letter-spacing: 2px; text-transform: uppercase; border: 2px solid;
  }
  .confidence-LOW    { color: var(--green);  border-color: var(--green);  background: rgba(57,211,83,.08); }
  .confidence-MEDIUM { color: var(--yellow); border-color: var(--yellow); background: rgba(227,179,65,.08); }
  .confidence-HIGH   { color: var(--red);    border-color: var(--red);    background: rgba(248,81,73,.08); }

  .factor-bar { margin-bottom: 10px; }
  .factor-label { display: flex; justify-content: space-between; font-size: 10px; color: var(--text3); margin-bottom: 4px; }
  .factor-track { background: var(--bg3); height: 4px; border-radius: 2px; overflow: hidden; }
  .factor-fill  { height: 100%; background: var(--accent); border-radius: 2px; transition: width .8s ease; }

  /* ── Summary strip ── */
  #summaryStrip {
    display: none; padding: 20px 24px; background: var(--bg2);
    border: 1px solid var(--border); margin-bottom: 24px;
    flex-wrap: wrap; gap: 32px; align-items: center;
  }
  #summaryStrip.visible { display: flex; }
  .sum-item { display: flex; flex-direction: column; gap: 4px; }
  .sum-label { font-size: 9px; color: var(--text3); letter-spacing: 2px; text-transform: uppercase; }
  .sum-val   { font-family: 'Syne', sans-serif; font-size: 18px; font-weight: 800; }
  .sum-val.green  { color: var(--green); }
  .sum-val.red    { color: var(--red); }
  .sum-val.yellow { color: var(--yellow); }
  .sum-val.cyan   { color: var(--accent); }

  /* ── JSON viewer ── */
  .json-toggle { font-size: 11px; color: var(--text3); cursor: pointer; padding: 8px 0; display: inline-block; }
  .json-toggle:hover { color: var(--accent); }
  #jsonView { display: none; margin-top: 12px; }
  #jsonView pre {
    background: var(--bg3); border: 1px solid var(--border);
    padding: 20px; font-size: 11px; line-height: 1.7;
    overflow-x: auto; color: var(--text2); max-height: 500px; overflow-y: auto;
  }

  /* ── Error state ── */
  .error-box {
    padding: 20px; border: 1px solid var(--red);
    background: rgba(248,81,73,.05); color: var(--red); font-size: 13px;
  }

  /* ── Gravatar avatar ── */
  .avatar-row { display: flex; gap: 16px; align-items: flex-start; margin-bottom: 16px; }
  .avatar-img { width: 64px; height: 64px; border: 2px solid var(--border2); }

  /* ── GitHub profile card ── */
  .gh-card {
    padding: 14px; border: 1px solid var(--border); background: var(--bg3);
    margin-bottom: 10px; display: flex; gap: 14px; align-items: flex-start;
  }
  .gh-avatar { width: 48px; height: 48px; border: 1px solid var(--border2); }
  .gh-info { flex: 1; }
  .gh-login { font-weight: 700; font-size: 13px; color: var(--accent); }
  .gh-name  { font-size: 11px; color: var(--text2); }
  .gh-meta  { font-size: 10px; color: var(--text3); margin-top: 6px; display: flex; gap: 12px; flex-wrap: wrap; }
  .gh-meta span { display: flex; gap: 4px; align-items: center; }

  /* ── Keybase proofs ── */
  .proof-row { display: flex; gap: 10px; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 11px; }
  .proof-row:last-child { border-bottom: none; }
  .proof-type { color: var(--purple); font-weight: 600; width: 80px; flex-shrink: 0; }
  .proof-name { color: var(--text2); flex: 1; }
  .proof-link { color: var(--accent); text-decoration: none; }
  .proof-link:hover { text-decoration: underline; }

  /* ── Responsive ── */
  @media (max-width: 600px) {
    header { flex-direction: column; align-items: flex-start; gap: 12px; padding: 32px 0 20px; }
    .search-box { flex-wrap: wrap; }
    #scanBtn { width: 100%; }
    .kv { grid-template-columns: 1fr; }
    .kv-key { margin-top: 8px; }
  }
</style>
</head>
<body>
<div class="wrap">

  <!-- Header -->
  <header>
    <div class="logo-mark">OI</div>
    <div class="title-block">
      <h1>OSINT Email Intelligence</h1>
      <p>Legal public data analysis · v2.0</p>
    </div>
  </header>

  <!-- Search -->
  <div class="search-section">
    <div class="search-box">
      <div class="search-prefix">⬤ TARGET</div>
      <input id="emailInput" type="email" placeholder="Enter email address to analyse…" autocomplete="off" spellcheck="false">
      <button id="scanBtn" onclick="runScan()">SCAN</button>
    </div>
    <div id="statusBar">
      <div class="spinner"></div>
      <span id="statusText">Initialising analysis pipeline…</span>
    </div>
  </div>

  <!-- Summary strip -->
  <div id="summaryStrip">
    <div class="sum-item"><div class="sum-label">Email</div><div class="sum-val cyan" id="s-email">—</div></div>
    <div class="sum-item"><div class="sum-label">Breached</div><div class="sum-val" id="s-breach">—</div></div>
    <div class="sum-item"><div class="sum-label">Breach count</div><div class="sum-val" id="s-bcount">—</div></div>
    <div class="sum-item"><div class="sum-label">Platforms found</div><div class="sum-val cyan" id="s-platforms">—</div></div>
    <div class="sum-item"><div class="sum-label">Public URLs</div><div class="sum-val cyan" id="s-urls">—</div></div>
    <div class="sum-item"><div class="sum-label">Confidence</div><div class="sum-val" id="s-conf">—</div></div>
  </div>

  <!-- Results -->
  <div id="results">

    <!-- 1. Validation -->
    <div class="card" id="card-validation">
      <div class="card-header" onclick="toggleCard('card-validation')">
        <span class="card-icon">✉</span>
        <span class="card-title">EMAIL VALIDATION</span>
        <span class="card-badge green" id="badge-validation">VALID</span>
        <span class="card-toggle">▾</span>
      </div>
      <div class="card-body">
        <div class="kv" id="kv-validation"></div>
      </div>
    </div>

    <!-- 2. Breach -->
    <div class="card" id="card-breach">
      <div class="card-header" onclick="toggleCard('card-breach')">
        <span class="card-icon">🔓</span>
        <span class="card-title">DATA BREACH ANALYSIS</span>
        <span class="card-badge" id="badge-breach">—</span>
        <span class="card-toggle">▾</span>
      </div>
      <div class="card-body" id="body-breach"></div>
    </div>

    <!-- 3. Domain -->
    <div class="card" id="card-domain">
      <div class="card-header" onclick="toggleCard('card-domain')">
        <span class="card-icon">🌐</span>
        <span class="card-title">DOMAIN INTELLIGENCE</span>
        <span class="card-badge cyan" id="badge-domain">WHOIS</span>
        <span class="card-toggle">▾</span>
      </div>
      <div class="card-body">
        <div class="kv" id="kv-domain"></div>
      </div>
    </div>

    <!-- 4. Accounts -->
    <div class="card" id="card-accounts">
      <div class="card-header" onclick="toggleCard('card-accounts')">
        <span class="card-icon">👤</span>
        <span class="card-title">LINKED ACCOUNTS</span>
        <span class="card-badge cyan" id="badge-accounts">—</span>
        <span class="card-toggle">▾</span>
      </div>
      <div class="card-body" id="body-accounts"></div>
    </div>

    <!-- 5. Platforms -->
    <div class="card" id="card-platforms">
      <div class="card-header" onclick="toggleCard('card-platforms')">
        <span class="card-icon">📡</span>
        <span class="card-title">PLATFORM PRESENCE</span>
        <span class="card-badge cyan" id="badge-platforms">—</span>
        <span class="card-toggle">▾</span>
      </div>
      <div class="card-body" id="body-platforms"></div>
    </div>

    <!-- 6. Public URLs -->
    <div class="card" id="card-urls">
      <div class="card-header" onclick="toggleCard('card-urls')">
        <span class="card-icon">🔍</span>
        <span class="card-title">PUBLIC FOOTPRINT</span>
        <span class="card-badge cyan" id="badge-urls">—</span>
        <span class="card-toggle">▾</span>
      </div>
      <div class="card-body" id="body-urls"></div>
    </div>

    <!-- 7. Correlation -->
    <div class="card" id="card-correlation">
      <div class="card-header" onclick="toggleCard('card-correlation')">
        <span class="card-icon">⚡</span>
        <span class="card-title">IDENTITY CORRELATION</span>
        <span class="card-badge" id="badge-correlation">—</span>
        <span class="card-toggle">▾</span>
      </div>
      <div class="card-body" id="body-correlation"></div>
    </div>

    <!-- JSON export -->
    <div style="margin-top:8px;">
      <span class="json-toggle" onclick="toggleJson()">{ } View raw JSON report</span>
      <div id="jsonView"><pre id="jsonPre"></pre></div>
    </div>

  </div><!-- /results -->
</div><!-- /wrap -->

<script>
let _report = null;

// ── Helpers ──────────────────────────────────────────────────────────────────
const $  = id => document.getElementById(id);
const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function kv(key, val, link=false) {
  if (!val && val !== 0) return '';
  const v = link ? `<a href="${esc(val)}" target="_blank" rel="noopener">${esc(val)}</a>` : esc(val);
  return `<div class="kv-key">${esc(key)}</div><div class="kv-val">${v}</div>`;
}
function kvArr(key, arr) {
  if (!arr || !arr.length) return '';
  return `<div class="kv-key">${esc(key)}</div><div class="kv-val">${arr.map(esc).join(', ')}</div>`;
}
function toggleCard(id) {
  document.getElementById(id).classList.toggle('collapsed');
}
function toggleJson() {
  const v = $('jsonView');
  v.style.display = v.style.display === 'none' ? 'block' : 'none';
}
function setStatus(msg) { $('statusText').textContent = msg; }

// ── Scan ─────────────────────────────────────────────────────────────────────
async function runScan() {
  const email = $('emailInput').value.trim();
  if (!email) { $('emailInput').focus(); return; }

  $('scanBtn').disabled = true;
  $('results').classList.remove('visible');
  $('summaryStrip').classList.remove('visible');
  $('statusBar').classList.add('active');
  setStatus('Validating email format…');

  try {
    setStatus('Running OSINT pipeline — breach check, WHOIS, platform probing…');
    const res = await fetch('/api/analyse', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email})
    });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || 'Server error');
    _report = data;
    renderReport(data);
  } catch(e) {
    $('results').innerHTML = `<div class="error-box">✗ ${esc(e.message)}</div>`;
    $('results').classList.add('visible');
  } finally {
    $('scanBtn').disabled = false;
    $('statusBar').classList.remove('active');
  }
}

$('emailInput').addEventListener('keydown', e => { if (e.key === 'Enter') runScan(); });

// ── Render ────────────────────────────────────────────────────────────────────
function renderReport(r) {
  const val      = r.validation    || {};
  const breach   = r.breach_data   || {};
  const domain   = r.domain_info   || {};
  const fp       = r.digital_footprint || {};
  const accounts = r.accounts      || {};
  const corr     = r.correlation   || {};

  // Summary strip
  $('s-email').textContent    = r.email || '—';
  const isBreached = breach.breached;
  const bEl = $('s-breach');
  bEl.textContent = isBreached ? 'YES' : 'No';
  bEl.className   = 'sum-val ' + (isBreached ? 'red' : 'green');
  $('s-bcount').textContent   = breach.breach_count || 0;
  const platforms_found = (accounts.platform_checks||[]).filter(p=>p.found).length;
  $('s-platforms').textContent = platforms_found;
  $('s-urls').textContent      = (fp.public_urls||[]).length;
  const confEl = $('s-conf');
  const conf   = corr.confidence || '—';
  confEl.textContent  = conf;
  confEl.className    = 'sum-val ' + ({LOW:'green',MEDIUM:'yellow',HIGH:'red'}[conf]||'cyan');
  $('summaryStrip').classList.add('visible');

  // 1. Validation
  $('kv-validation').innerHTML =
    kv('Email',      val.email) +
    kv('Username',   val.username) +
    kv('Domain',     val.domain) +
    kvArr('Variations', val.variations);

  // 2. Breach
  const bb = $('badge-breach');
  if (breach.error) {
    bb.textContent = 'ERROR'; bb.className = 'card-badge yellow';
    $('body-breach').innerHTML = `<div class="kv-val" style="color:var(--yellow)">${esc(breach.error)}</div>`;
  } else if (breach.breached) {
    bb.textContent = `${breach.breach_count} BREACHES`; bb.className = 'card-badge red';
    let html = (breach.breaches||[]).map(b => `
      <div class="breach-item">
        <div class="breach-name">${esc(b.name)}</div>
        <div class="breach-date">${esc(b.date||'')}</div>
        <div class="breach-data">${(b.data_classes||[]).map(esc).join(' · ')}</div>
        <div class="breach-count">${(b.count||0).toLocaleString()} records compromised</div>
      </div>`).join('');
    if (breach.pastes && breach.pastes.length) {
      html += `<hr class="cd"><div class="kv-key">PASTES (${breach.pastes.length})</div>`;
      html += breach.pastes.map(p=>`<div class="paste-item">${esc(p.source)} — ${esc(p.id)} — ${esc(p.date)}</div>`).join('');
    }
    $('body-breach').innerHTML = html;
  } else {
    bb.textContent = 'CLEAN'; bb.className = 'card-badge green';
    $('body-breach').innerHTML = `<div class="kv-val" style="color:var(--green)">✓ Not found in any known data breach</div>`;
  }

  // 3. Domain
  const db = $('badge-domain');
  db.textContent = domain.ip_address || 'WHOIS'; db.className = 'card-badge cyan';
  $('kv-domain').innerHTML =
    kv('Registrar',     domain.registrar) +
    kv('Created',       domain.creation_date) +
    kv('Expires',       domain.expiration_date) +
    kv('Updated',       domain.updated_date) +
    kv('IP Address',    domain.ip_address) +
    kv('Organisation',  domain.org) +
    kv('Country',       domain.country) +
    kv('DNSSEC',        domain.dnssec) +
    kvArr('Status',     domain.status) +
    kvArr('Name Servers', domain.name_servers) +
    (domain.error ? kv('Error', domain.error) : '');

  // 4. Accounts (Gravatar + GitHub + Keybase + Hunter)
  let accHtml = '';
  const grav = accounts.gravatar || {};
  if (grav.found) {
    accHtml += `<div class="avatar-row">
      <img class="avatar-img" src="${esc(grav.avatar_url)}" alt="Gravatar" onerror="this.style.display='none'">
      <div>
        <div class="kv">
          ${kv('Display name', grav.display_name)}
          ${kv('Profile', grav.profile_url, true)}
          ${kv('About', grav.about)}
        </div>
        ${(grav.accounts||[]).length ? '<hr class="cd"><div class="kv-key" style="margin-bottom:8px">LINKED ACCOUNTS</div>' +
          grav.accounts.map(a=>`<div class="proof-row"><span class="proof-type">${esc(a.name)}</span><a class="proof-link" href="${esc(a.url)}" target="_blank">${esc(a.url)}</a></div>`).join('') : ''}
      </div></div><hr class="cd">`;
  }

  const ghProfiles = accounts.github_profiles || [];
  if (ghProfiles.length) {
    accHtml += ghProfiles.map(p => `
      <div class="gh-card">
        <img class="gh-avatar" src="${esc(p.avatar||'')}" alt="" onerror="this.style.display='none'">
        <div class="gh-info">
          <div class="gh-login"><a href="${esc(p.url)}" target="_blank" style="color:var(--accent);text-decoration:none">@${esc(p.login)}</a></div>
          <div class="gh-name">${esc(p.name||'')}</div>
          ${p.bio ? `<div class="gh-name" style="margin-top:4px;color:var(--text2)">${esc(p.bio)}</div>` : ''}
          <div class="gh-meta">
            ${p.location ? `<span>📍 ${esc(p.location)}</span>` : ''}
            ${p.company  ? `<span>🏢 ${esc(p.company)}</span>` : ''}
            ${p.repos    ? `<span>📁 ${p.repos} repos</span>` : ''}
            ${p.followers? `<span>👥 ${p.followers} followers</span>` : ''}
            ${p.twitter  ? `<span>🐦 @${esc(p.twitter)}</span>` : ''}
            ${p.blog     ? `<span><a href="${esc(p.blog)}" target="_blank" style="color:var(--accent)">${esc(p.blog)}</a></span>` : ''}
          </div>
        </div>
      </div>`).join('') + '<hr class="cd">';
  }

  const kb = accounts.keybase || {};
  if (kb.found) {
    accHtml += `<div class="kv" style="margin-bottom:12px">
      ${kv('Keybase user', kb.username)}
      ${kv('Profile', kb.profile_url, true)}
    </div>`;
    if (kb.proofs && kb.proofs.length) {
      accHtml += (kb.proofs||[]).map(p=>
        `<div class="proof-row"><span class="proof-type">${esc(p.type)}</span><span class="proof-name">${esc(p.name)}</span>
         ${p.url ? `<a class="proof-link" href="${esc(p.url)}" target="_blank" rel="noopener">↗</a>` : ''}</div>`
      ).join('') + '<hr class="cd">';
    }
  }

  const hun = accounts.hunter || {};
  if (hun.status) {
    accHtml += `<div class="kv">
      ${kv('Hunter status',  hun.status)}
      ${kv('Deliverable',    hun.result)}
      ${kv('Score',          hun.score)}
      ${kv('Disposable',     hun.disposable)}
      ${kv('Webmail',        hun.webmail)}
      ${kv('MX Records',     hun.mx_records)}
    </div>`;
  }

  if (!accHtml) accHtml = `<div class="kv-val" style="color:var(--text3)">No linked accounts discovered from Gravatar / GitHub / Keybase.</div>`;
  $('body-accounts').innerHTML = accHtml;
  const totalAcc = (grav.found?1:0) + ghProfiles.length + (kb.found?1:0);
  $('badge-accounts').textContent = `${totalAcc} FOUND`;
  $('badge-accounts').className   = `card-badge ${totalAcc > 0 ? 'cyan' : ''}`;

  // 5. Platforms
  const checks = accounts.platform_checks || [];
  const found_p = checks.filter(c => c.found);
  const notfound_p = checks.filter(c => !c.found);
  $('badge-platforms').textContent = `${found_p.length} / ${checks.length}`;
  $('badge-platforms').className   = `card-badge ${found_p.length > 0 ? 'green' : ''}`;

  let platHtml = '';
  if (found_p.length) {
    platHtml += `<div style="font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px">Confirmed presence</div>
    <div class="platform-grid" style="margin-bottom:16px">` +
    found_p.map(c => `
      <div class="platform-chip found">
        <div class="dot"></div>
        <div>
          <div class="platform-name">${esc(c.platform)}</div>
          <div class="platform-user">@${esc(c.username)}</div>
        </div>
        <a href="${esc(c.url)}" target="_blank" style="margin-left:auto;color:var(--accent);font-size:12px;text-decoration:none">↗</a>
      </div>`).join('') + `</div>`;
  }
  if (notfound_p.length) {
    const uniPlatforms = [...new Set(notfound_p.map(c=>c.platform))];
    platHtml += `<details style="margin-top:8px">
      <summary style="font-size:10px;color:var(--text3);cursor:pointer;text-transform:uppercase;letter-spacing:1px">
        Not found (${uniPlatforms.length} platforms)
      </summary>
      <div class="platform-grid" style="margin-top:10px">` +
      uniPlatforms.map(pl => `<div class="platform-chip notfound"><div class="dot"></div><div class="platform-name">${esc(pl)}</div></div>`).join('') +
      `</div></details>`;
  }
  $('body-platforms').innerHTML = platHtml || '<div class="kv-val" style="color:var(--text3)">No platform checks available.</div>';

  // 6. Public URLs
  const urls = fp.public_urls || [];
  $('badge-urls').textContent = `${urls.length} URLS`;
  $('badge-urls').className   = `card-badge ${urls.length > 0 ? 'cyan' : ''}`;
  $('body-urls').innerHTML = urls.length
    ? `<div class="url-list">` + urls.map((u,i)=>
        `<div class="url-item"><span class="url-idx">${String(i+1).padStart(2,'0')}</span><a href="${esc(u)}" target="_blank" rel="noopener">${esc(u)}</a></div>`
      ).join('') + `</div>`
    : `<div class="kv-val" style="color:var(--text3)">No public URLs discovered.</div>`;

  // 7. Correlation
  const conf   = corr.confidence || 'LOW';
  const score  = corr.score || 0;
  const factors = corr.factors || {};
  const maxScore = 15;
  const confClass = {LOW:'green',MEDIUM:'yellow',HIGH:'red'}[conf] || 'green';
  $('badge-correlation').textContent = conf;
  $('badge-correlation').className   = `card-badge ${confClass}`;

  const factorNames = {
    url_matches:'URL Matches', breach_bonus:'Breach Bonus',
    platform_bonus:'Platform Presence', github_bonus:'GitHub Found',
    gravatar_bonus:'Gravatar Found', keybase_bonus:'Keybase Found',
    domain_bonus:'Domain Age', paste_bonus:'Paste Found'
  };
  const factorBars = Object.entries(factors).map(([k,v]) => {
    const pct = Math.min(v / 3 * 100, 100);
    return `<div class="factor-bar">
      <div class="factor-label"><span>${factorNames[k]||k}</span><span>${v}</span></div>
      <div class="factor-track"><div class="factor-fill" style="width:${pct}%"></div></div>
    </div>`;
  }).join('');

  const matchedUrls = corr.matched_urls || [];
  const confirmedPlatforms = corr.confirmed_platforms || [];
  $('body-correlation').innerHTML = `
    <div class="score-section">
      <div class="score-circle">
        <div class="score-number">${score}</div>
        <div class="score-label">SCORE</div>
      </div>
      <div>
        <div class="confidence-badge confidence-${conf}" style="margin-bottom:12px">${conf} CONFIDENCE</div>
        ${confirmedPlatforms.length ? `<div style="font-size:11px;color:var(--text2)">${confirmedPlatforms.join(' · ')}</div>` : ''}
      </div>
    </div>
    <div style="max-width:400px">${factorBars}</div>
    ${matchedUrls.length ? `<hr class="cd"><div style="font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px">Matched URLs</div>
      <div class="url-list">`+matchedUrls.map((u,i)=>
        `<div class="url-item"><span class="url-idx">${i+1}</span><a href="${esc(u)}" target="_blank">${esc(u)}</a></div>`
      ).join('')+`</div>` : ''}`;

  // JSON
  $('jsonPre').textContent = JSON.stringify(r, null, 2);

  $('results').classList.add('visible');
  $('results').scrollIntoView({behavior:'smooth', block:'start'});
}
</script>
</body>
</html>"""

if _FLASK:
    @app.route("/")
    def index():
        return HTML

    @app.route("/api/analyse", methods=["POST"])
    def analyse():
        data  = request.get_json(force=True)
        email = (data.get("email") or "").strip()
        if not email:
            return jsonify({"error": "No email provided"}), 400
        try:
            report = run_analysis(email, verbose=False)
            return jsonify(report)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500


def start_ui(open_browser: bool = True):
    if not _FLASK:
        print("Flask is not installed. Run:  pip install flask")
        return
    if open_browser:
        import webbrowser
        threading.Timer(1.2, lambda: webbrowser.open(
            f"http://{config.UI_HOST}:{config.UI_PORT}"
        )).start()
    print(f"\n  ◆ Web UI → http://{config.UI_HOST}:{config.UI_PORT}")
    print("  Press Ctrl+C to stop\n")
    app.run(host=config.UI_HOST, port=config.UI_PORT, debug=False)


if __name__ == "__main__":
    start_ui()
