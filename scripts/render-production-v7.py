#!/usr/bin/env python3
"""
GenoMAX² V7 — Design System v1.0 Implementation
=================================================
Clean rewrite. Reuses only: text primitives, QR, crop marks, parse_back_text, pipeline.

Design tokens:
  Safe area: 28px
  Spacing:   8 / 12 / 16 / 24 / 32 / 48 / 64
  Fonts:     IBM Plex Mono only (Regular/Medium/SemiBold/Bold)
"""

import json, os, sys, re, argparse, io, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from reportlab.lib.units import inch, mm
from reportlab.lib.colors import CMYKColor, Color
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image

# ─── PATHS ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
FONTS_DIR = BASE / "design-system" / "fonts"
DATA_DIR = BASE / "design-system" / "data"
OUTPUT_BASE = BASE / "design-system" / "production-v7"

# ─── FONTS (IBM Plex Mono only per Design System v1.0) ───────────────────
FONT_MAP = {
    "Mono":         "IBMPlexMono-Regular.ttf",
    "Mono-Medium":  "IBMPlexMono-Medium.ttf",
    "Mono-SemiBold":"IBMPlexMono-SemiBold.ttf",
    "Mono-Bold":    "IBMPlexMono-Bold.ttf",
    "Mono-Light":   "IBMPlexMono-Light.ttf",
    # Condensed fallbacks for overflow cascading
    "Cond":         "IBMPlexSansCondensed-Regular.ttf",
    "Cond-Medium":  "IBMPlexSansCondensed-Medium.ttf",
    "Cond-SemiBold":"IBMPlexSansCondensed-SemiBold.ttf",
    "Cond-Bold":    "IBMPlexSansCondensed-Bold.ttf",
}
for name, fn in FONT_MAP.items():
    p = FONTS_DIR / fn
    if p.exists():
        pdfmetrics.registerFont(TTFont(name, str(p)))

COND_MAP = {
    "Mono-Bold": "Cond-Bold",
    "Mono-SemiBold": "Cond-SemiBold",
    "Mono-Medium": "Cond-Medium",
    "Mono": "Cond",
}