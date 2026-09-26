#!/usr/bin/env python3
"""
Kindle Dashboard - 1448x1072 landscape, quiet editorial e-ink.
Fixed vertical grid. No overlapping zones.
"""

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
import subprocess
import os
import json
import datetime


# ============================================================
# CONFIG
# ============================================================

BASE = os.path.dirname(os.path.abspath(__file__))
if not os.path.isdir(BASE) or not os.path.exists(os.path.join(BASE, "dashboard.py")):
    BASE = os.path.expanduser("~/KindleDashboard")
CONFIG_PATH = os.path.join(BASE, "config.json")

def load_config():
    defaults = {"name": "", "city": "-", "country": "", "commute": None, "reminders": []}
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        for k, v in defaults.items():
            cfg.setdefault(k, v)
        return cfg
    except Exception:
        return defaults

CFG = load_config()


# ============================================================
# CANVAS + VERTICAL GRID
# ============================================================
#
#  y=0    greeting / date      |   header image (bleeds top-right)
#  y=460  ─── rule ───
#  y=490  UP NEXT              |   REMINDERS
#  y=790  ─── rule ───
#  y=820  city / next / temps
#  y=922  ─── banner starts ───
#  y=1072 bottom
#
# ============================================================

W, H = 1448, 1072
img = Image.new("L", (W, H), 255)
draw = ImageDraw.Draw(img)

MARGIN = 64
COL_SPLIT = 880                  # x where left/right columns split

RULE_TOP_Y     = 460             # between header and middle
RULE_MID_Y     = 790             # between middle and footer text
FOOTER_TEXT_Y  = 820             # city name baseline top
BANNER_Y       = 922             # footer banner top
BANNER_H       = H - BANNER_Y    # 150


# ============================================================
# FONTS
# ============================================================

FONT_DIRS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/Library/Fonts",
    "/usr/share/fonts/truetype/inter",
    "/usr/share/fonts/truetype/dejavu",
]

def find_font(candidates):
    for d in FONT_DIRS:
        for name in candidates:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    return None

_SERIF = find_font(["Lora.ttf", "NewYork.ttf", "Georgia.ttf", "DejaVuSerif.ttf"])
_SANS  = find_font(["Inter.ttc", "InterVariable.ttf", "HelveticaNeue.ttc", "Helvetica.ttc", "DejaVuSans.ttf"])
_MONO  = find_font(["SFNSMono.ttf", "Menlo.ttc", "DejaVuSansMono.ttf"])

# HelveticaNeue.ttc verified indices:
#   0=Regular 1=Bold 2=Italic 3=BoldItalic 4=CondBold
#   5=UltraLight 6=UltraLightItalic 7=Light 8=LightItalic
#   9=CondBlack 10=Medium 11=MediumItalic 12=Thin 13=ThinItalic
HN_THIN    = 12
HN_LIGHT   = 7
HN_REGULAR = 0
HN_MEDIUM  = 10
HN_BOLD    = 1

def F(path, size, index=None):
    if path:
        try:
            if index is not None:
                return ImageFont.truetype(path, size, index=index)
        except Exception:
            pass
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

# ---- Display serif ----
BIG_TEMP  = F(_SERIF, 190)    # the "26°"
CONDITION = F(_SERIF, 62)     # "Clear"
CITY_BIG  = F(_SERIF, 56)     # footer "Jinhua"
TEMP_SIDE = F(_SERIF, 54)     # footer H/L

# ---- UI text ----
GREETING  = F(_SANS, 36, HN_MEDIUM)
DATE      = F(_SANS, 26, HN_BOLD)
SECTION   = F(_SERIF, 36)   # small letterspaced caps
ROW_MAIN  = F(_SANS, 28, HN_REGULAR)   # event times
ROW_SUB   = F(_SANS, 28, HN_LIGHT)    # event titles
STATUS    = F(_SANS, 26, HN_MEDIUM)   # "Feels like... H... L..."
REMIND    = F(_SANS, 26, HN_LIGHT)
META      = F(_MONO, 14)


# ============================================================
# HELPERS
# ============================================================

def txt(x, y, s, f, fill=0, anchor=None):
    draw.text((x, y), s, font=f, fill=fill, anchor=anchor)

def text_w(s, f):
    b = draw.textbbox((0, 0), s, font=f)
    return b[2] - b[0]

def rule(y, x1=MARGIN, x2=W - MARGIN, shade=180, width=2):
    draw.line((x1, y, x2, y), fill=shade, width=width)

def fit_text(s, base_path, max_width, start_size, min_size=14, weight=None):
    lo, hi = min_size, start_size
    best = F(base_path, min_size, weight)
    while lo <= hi:
        mid = (lo + hi) // 2
        f = F(base_path, mid, weight)
        if text_w(s, f) <= max_width:
            best = f
            lo = mid + 1
        else:
            hi = mid - 1
    return best

def draw_checkbox(x, y, size=20, weight=2):
    draw.rectangle((x, y, x + size, y + size), outline=0, width=weight)

def letterspaced(s):
    return s.upper()


def section_label(x, y, s):
    """Draw a section header in serif, faux-bold by double-stroking."""
    text = s.upper()
    txt(x, y, text, SECTION)
    txt(x + 1, y, text, SECTION)
    txt(x, y + 1, text, SECTION)



def cover_crop(im, tw, th):
    src_ratio = im.width / im.height
    dst_ratio = tw / th
    if src_ratio > dst_ratio:
        nh = th
        nw = int(nh * src_ratio)
    else:
        nw = tw
        nh = int(nw / src_ratio)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    l = (nw - tw) // 2
    t = (nh - th) // 2
    return im.crop((l, t, l + tw, t + th))


def process_photo(im):
    """Clean, dramatic B&W for the header."""
    im = ImageOps.grayscale(im)
    im = ImageOps.autocontrast(im, cutoff=1)
    lut = [min(255, int(((i / 255.0) ** 1.05) * 255)) for i in range(256)]
    im = im.point(lut)
    im = ImageEnhance.Contrast(im).enhance(1.3)
    im = ImageEnhance.Sharpness(im).enhance(1.5)
    return im


def process_banner(im):
    """High-contrast B&W banner."""
    im = ImageOps.grayscale(im)
    im = ImageOps.autocontrast(im, cutoff=1)
    lut = [min(255, int(((i / 255.0) ** 0.9) * 255)) for i in range(256)]
    im = im.point(lut)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    im = ImageEnhance.Sharpness(im).enhance(1.3)
    return im


# ============================================================
# LIVE DATA
# ============================================================

def run(cmd, timeout=12):
    try:
        return subprocess.check_output(cmd, text=True, timeout=timeout,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""

today_events = []
out = run([os.path.join(BASE, "calendar_events")])
if out and out != "NO_EVENTS":
    for line in out.splitlines():
        if "|" in line:
            t, title = line.split("|", 1)
            today_events.append((t.strip(), title.strip()))

upcoming = []
out = run([os.path.join(BASE, "calendar_upcoming")])
if out and out != "NO_EVENTS":
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            upcoming.append(tuple(p.strip() for p in parts))

WEATHER_CODES = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Cloudy",
    45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Showers", 81: "Showers", 82: "Heavy showers",
    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
}

weather = {"temp": "--", "humidity": "--", "condition": "Weather unavailable",
           "low": "--", "high": "--", "ok": False}

out = run(["python3", os.path.join(BASE, "weather.py")], timeout=15)
if out and out != "ERROR" and out.count("|") >= 4:
    try:
        temp, hum, code, low, high = out.split("|")
        weather = {"temp": temp, "humidity": hum,
                   "condition": WEATHER_CODES.get(int(code), "Weather"),
                   "low": low, "high": high, "ok": True}
    except Exception:
        pass


# ============================================================
# DATE / TIME
# ============================================================

now = datetime.datetime.now()
clock      = now.strftime("%H:%M")
short_date = now.strftime("%A, %B %-d, %Y")
greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 18 else "Good evening"
if CFG.get("name"):
    greeting = f"{greeting}, {CFG['name']}"


# ============================================================
# HEADER IMAGE  (top-right, bleeds to right edge, feather on left)
# ============================================================

SCENE_W = 640
SCENE_H = 440
SCENE_X = W - SCENE_W
SCENE_Y = 0

scene_path = None
for name in ("main-landscape.png", "main-landscape.jpg"):
    p = os.path.join(BASE, name)
    if os.path.exists(p):
        scene_path = p
        break

if scene_path:
    scene = Image.open(scene_path).convert("L")
    scene = cover_crop(scene, SCENE_W, SCENE_H)
    scene = process_photo(scene)

    # Feather left edge into white
    FEATHER = 100
    for x in range(FEATHER):
        a = x / FEATHER
        col = scene.crop((x, 0, x + 1, SCENE_H))
        col = col.point(lambda p, a=a: int(p * a + 255 * (1 - a)))
        scene.paste(col, (x, 0))

    img.paste(scene, (SCENE_X, SCENE_Y))


# ============================================================
# HEADER TEXT
# ============================================================

txt(MARGIN, 56, greeting, GREETING)
txt(MARGIN, 100, short_date, DATE)

# Big temperature + condition
txt(MARGIN, 130, f"{weather['temp']}°", BIG_TEMP)
txt(MARGIN, 340, weather["condition"], CONDITION)

# Status line — medium weight, clean
status = f"Feels like {weather['temp']}°   ·   H {weather['high']}°   ·   L {weather['low']}°   ·   {weather['humidity']}% humidity"
if not weather["ok"]:
    status = "Live weather unavailable"
txt(MARGIN, 420, status, STATUS)


# ============================================================
# MIDDLE RULE
# ============================================================

rule(RULE_TOP_Y)


# ============================================================
# UP NEXT  (left column)
# ============================================================

UP_NEXT_X = MARGIN
UP_NEXT_W = COL_SPLIT - MARGIN - 40

section_label(UP_NEXT_X, RULE_TOP_Y + 28, "up next")

rows = []
if today_events:
    for t, title in today_events[:4]:
        rows.append((t, title))
if len(rows) < 4:
    for day, time, title in upcoming[: 4 - len(rows)]:
        rows.append((f"{day} {time}", title))
if not rows:
    rows = [("-", "Calendar unavailable")]

row_y = RULE_TOP_Y + 90
ROW_H = 68

for t, title in rows[:4]:
    txt(UP_NEXT_X, row_y, t, ROW_MAIN)
    title_x = UP_NEXT_X + 220
    title_max = UP_NEXT_W - 220
    f = fit_text(title, _SANS, title_max, start_size=28, min_size=18, weight=HN_LIGHT)
    txt(title_x, row_y, title, f)
    row_y += ROW_H


# ============================================================
# REMINDERS  (right column)
# ============================================================

REM_X = COL_SPLIT + 40
REM_W = W - MARGIN - REM_X

section_label(REM_X, RULE_TOP_Y + 28, "reminders")

rem_y = RULE_TOP_Y + 90
reminders = CFG.get("reminders", [])

if not reminders:
    txt(REM_X, rem_y, "Add reminders in config.json", REMIND)
else:
    for task in reminders[:4]:
        draw_checkbox(REM_X, rem_y + 4, size=20)
        f = fit_text(task, _SANS, REM_W - 40, start_size=26, min_size=17, weight=HN_LIGHT)
        txt(REM_X + 38, rem_y, task, f)
        rem_y += 56


# ============================================================
# FOOTER TEXT ZONE
# ============================================================

rule(RULE_MID_Y)

# City name (serif, big)
txt(MARGIN, FOOTER_TEXT_Y, CFG.get("city", "-"), CITY_BIG)

# Next event line under the city
next_event = upcoming[0] if upcoming else None
if next_event:
    day, time, title = next_event
    txt(MARGIN, FOOTER_TEXT_Y + 70, f"Next: {day} {time} — {title}", STATUS)
else:
    txt(MARGIN, FOOTER_TEXT_Y + 70, "No upcoming events", STATUS)

# H / L temps, right-aligned
txt(W - MARGIN, FOOTER_TEXT_Y - 6, f"H {weather['high']}°", TEMP_SIDE, anchor="ra")
txt(W - MARGIN, FOOTER_TEXT_Y + 60, f"L {weather['low']}°", TEMP_SIDE, anchor="ra")


# ============================================================
# FOOTER BANNER  (full width)
# ============================================================

footer_path = None
for name in ("footer-strip.jpg", "footer-strip.png"):
    p = os.path.join(BASE, name)
    if os.path.exists(p):
        footer_path = p
        break

if footer_path:
    foot = Image.open(footer_path).convert("L")
    foot = cover_crop(foot, W, BANNER_H)
    foot = process_banner(foot)
    img.paste(foot, (0, BANNER_Y))


# ============================================================
# SYNC META  (top-right, under the scene image)
# ============================================================

txt(W - MARGIN, SCENE_H + 14, f"SYNCED {clock}", META, anchor="ra")


# ============================================================
# SAVE
# ============================================================

# Landscape version (Mac preview / original)
out_path = os.path.join(BASE, "dashboard.png")
img.save(out_path)
print(f"Created {out_path}")

# Portrait version for Kindle (rotate 90 CW + resize to 1236x1648)
kindle = img.rotate(90, expand=True)
kindle = kindle.resize((1236, 1648), Image.Resampling.LANCZOS)
kindle_path = os.path.join(BASE, "dashboard-kindle.png")
kindle.save(kindle_path)
print(f"Created {kindle_path}")
