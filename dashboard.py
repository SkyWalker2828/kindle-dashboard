#!/usr/bin/env python3
"""
Kindle Dashboard — portrait 1236x1648, e-ink editorial.
Redesign pass: integrated bleed illustration, inline temp+condition,
two-column Up Next / Reminders, softer filled-icon language.
"""

import datetime
import json
import math
import os
import subprocess
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

# ============================================================
# CONFIG
# ============================================================
BASE = os.path.dirname(os.path.abspath(__file__))
if not os.path.isdir(BASE) or not os.path.exists(os.path.join(BASE, "dashboard.py")):
    BASE = os.path.expanduser("~/KindleDashboard")

CONFIG_PATH = os.path.join(BASE, "config.json")


def load_config():
    defaults = {"name": "", "city": "", "country": "", "reminders": []}
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
# CANVAS
# ============================================================
W, H = 1236, 1648
img = Image.new("L", (W, H), 255)
draw = ImageDraw.Draw(img)
MARGIN = 60

# ============================================================
# FONTS
# ============================================================
FONT_DIRS = [
    os.path.join(BASE, "fonts"),
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/Library/Fonts",
    "/usr/share/fonts/truetype/google-fonts",
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


_SERIF = find_font(["Lora-Variable.ttf", "Lora.ttf", "Georgia.ttf", "DejaVuSerif.ttf"])
_SANS = find_font(["Inter-Variable.ttf", "Inter.ttc", "HelveticaNeue.ttc", "Helvetica.ttc", "DejaVuSans.ttf"])
_SANS_BOLD = find_font(["Inter-Bold.ttf", "HelveticaNeue-Bold.ttf", "DejaVuSans-Bold.ttf"])
_MONO = find_font(["SFNSMono.ttf", "Menlo.ttc", "DejaVuSansMono.ttf"])


def F(path, size, variation=None):
    """Load a font; if it's a variable font, switch to the named weight."""
    if not path:
        return ImageFont.load_default()
    try:
        f = ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()
    if variation:
        try:
            names = {n.decode() if isinstance(n, bytes) else n for n in f.get_variation_names()}
            if variation in names:
                f.set_variation_by_name(variation)
        except Exception:
            pass
    return f


# Serif at three real weights via the variable font — no faux-bold anywhere.
DATE_HEAD = F(_SERIF, 50, "SemiBold")
CITY_LINE = F(_SERIF, 30, "Regular")
GREETING = F(_SANS, 26, None)
BIG_TEMP = F(_SERIF, 158, "SemiBold")
CONDITION = F(_SERIF, 54, "Regular")
STATUS = F(_SANS, 28, None)
SECTION_LABEL = F(_SANS_BOLD, 25, None)
ROW_TIME = F(_SANS_BOLD, 29, None)
ROW_TITLE = F(_SANS, 29, None)
REMIND_TEXT = F(_SANS, 27, None)
OUTLOOK_DAY = F(_SERIF, 32, "SemiBold")
OUTLOOK_TEMP = F(_SERIF, 36, "Regular")
OUTLOOK_COND = F(_SANS, 23, None)
CITY_BIG = F(_SERIF, 52, "SemiBold")
UPDATED = F(_MONO, 16)

INK = 15        # near-black, softer than pure 0 for a warmer e-ink look
MUTE = 110      # secondary text
FAINT = 190     # rules

# ============================================================
# HELPERS
# ============================================================
def txt(x, y, s, f, fill=INK, anchor=None):
    draw.text((x, y), s, font=f, fill=fill, anchor=anchor)


def text_w(s, f):
    b = draw.textbbox((0, 0), s, font=f)
    return b[2] - b[0]


def text_h(s, f):
    b = draw.textbbox((0, 0), s, font=f)
    return b[3] - b[1]


def rule(y, x1=MARGIN, x2=W - MARGIN, shade=FAINT, width=2):
    draw.line((x1, y, x2, y), fill=shade, width=width)


def fit_text(s, base_path, max_width, start_size, min_size=14, variation=None):
    lo, hi = min_size, start_size
    best = F(base_path, min_size, variation)
    while lo <= hi:
        mid = (lo + hi) // 2
        f = F(base_path, mid, variation)
        if text_w(s, f) <= max_width:
            best = f
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def section_header(x, y, icon_fn, label):
    """Small line-icon + letterspaced caps label."""
    icon_fn(x, y - 2, 28)
    txt(x + 38, y, label.upper(), SECTION_LABEL, fill=MUTE)


# ---- section icons (simple, consistent stroke weight = 2.5) ----
def icon_calendar(x, y, size):
    w = size
    draw.rounded_rectangle((x, y + 3, x + w, y + w), radius=3, outline=INK, width=2)
    draw.line((x + w * 0.28, y, x + w * 0.28, y + 7), fill=INK, width=2)
    draw.line((x + w * 0.72, y, x + w * 0.72, y + 7), fill=INK, width=2)
    draw.line((x + 2, y + 10, x + w - 2, y + 10), fill=INK, width=2)


def icon_checklist(x, y, size):
    w = size
    for i, dy in enumerate((0, w * 0.45)):
        draw.rectangle((x, y + dy, x + 8, y + dy + 8), outline=INK, width=2)
        draw.line((x + 14, y + dy + 4, x + w, y + dy + 4), fill=INK, width=2)


def icon_outlook(x, y, size):
    r = size * 0.28
    cx, cy = x + r + 2, y + r + 4
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=INK, width=2)
    draw.ellipse((x + size * 0.35, y + size * 0.15, x + size, y + size * 0.75), outline=INK, width=2, fill=235)


def draw_weather_icon(cx, cy, code, r=34):
    """Rounder, softer icons with a light fill — closer to the reference style."""
    lw = 4
    if code in (0, 1):  # clear
        draw.ellipse((cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6), outline=INK, width=lw, fill=240)
        for angle in range(0, 360, 45):
            a = math.radians(angle)
            x1 = cx + math.cos(a) * (r * 0.6 + 6)
            y1 = cy + math.sin(a) * (r * 0.6 + 6)
            x2 = cx + math.cos(a) * (r * 0.6 + 17)
            y2 = cy + math.sin(a) * (r * 0.6 + 17)
            draw.line((x1, y1, x2, y2), fill=INK, width=lw - 1)
    elif code in (2, 3, 45, 48):  # cloud / fog
        draw.ellipse((cx - r, cy - r * 0.3, cx + r * 0.15, cy + r * 0.55), outline=INK, width=lw, fill=205)
        draw.ellipse((cx - r * 0.25, cy - r * 0.75, cx + r, cy + r * 0.35), outline=INK, width=lw, fill=205)
    elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82):  # rain
        draw.ellipse((cx - r, cy - r * 0.55, cx + r * 0.1, cy + r * 0.2), outline=INK, width=lw, fill=205)
        draw.ellipse((cx - r * 0.3, cy - r, cx + r * 0.9, cy - r * 0.1), outline=INK, width=lw, fill=205)
        for dx in (-r * 0.5, 0, r * 0.5):
            draw.line((cx + dx, cy + r * 0.4, cx + dx - 5, cy + r * 0.85), fill=INK, width=3)
    elif code in (71, 73, 75):  # snow
        draw.ellipse((cx - r, cy - r * 0.55, cx + r * 0.1, cy + r * 0.2), outline=INK, width=lw, fill=205)
        draw.ellipse((cx - r * 0.3, cy - r, cx + r * 0.9, cy - r * 0.1), outline=INK, width=lw, fill=205)
        for dx in (-r * 0.5, 0, r * 0.5):
            draw.ellipse((cx + dx - 4, cy + r * 0.5, cx + dx + 4, cy + r * 0.58), outline=INK, width=2)
    elif code in (95, 96, 99):  # thunder
        draw.ellipse((cx - r, cy - r * 0.55, cx + r * 0.1, cy + r * 0.2), outline=INK, width=lw, fill=205)
        draw.ellipse((cx - r * 0.3, cy - r, cx + r * 0.9, cy - r * 0.1), outline=INK, width=lw, fill=205)
        draw.line((cx, cy + r * 0.3, cx - r * 0.25, cy + r * 0.8), fill=INK, width=lw)
        draw.line((cx - r * 0.25, cy + r * 0.8, cx + r * 0.22, cy + r * 0.8), fill=INK, width=lw)
        draw.line((cx + r * 0.22, cy + r * 0.8, cx - r * 0.05, cy + r * 1.3), fill=INK, width=lw)
    else:
        draw.ellipse((cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6), outline=INK, width=lw)


def cover_crop(im, tw, th, focus_x=0.5, focus_y=0.5):
    src_ratio = im.width / im.height
    dst_ratio = tw / th
    if src_ratio > dst_ratio:
        nh = th
        nw = int(nh * src_ratio)
    else:
        nw = tw
        nh = int(nw / src_ratio)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    l = int((nw - tw) * focus_x)
    t = int((nh - th) * focus_y)
    return im.crop((l, t, l + tw, t + th))


def process_photo(im, gamma=1.05, contrast=1.3, sharpness=1.5):
    im = ImageOps.grayscale(im)
    im = ImageOps.autocontrast(im, cutoff=1)
    lut = [min(255, int(((i / 255.0) ** gamma) * 255)) for i in range(256)]
    im = im.point(lut)
    im = ImageEnhance.Contrast(im).enhance(contrast)
    im = ImageEnhance.Sharpness(im).enhance(sharpness)
    return im


def feather_left_edge(im, feather_px):
    """Blend the illustration's left edge into white so it reads as
    'bleeding' out of the page rather than a hard-edged photo block."""
    px = im.load()
    w, h = im.size
    for x in range(min(feather_px, w)):
        a = x / feather_px
        for y in range(h):
            v = px[x, y]
            px[x, y] = int(v * a + 255 * (1 - a))
    return im


def light_chip(x, y, w, h, radius=10, fill=246):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill)


def two_columns(items, x, y, col_w, row_h, row_draw_fn, max_rows_per_col=2):
    """Lay `items` into a left/right column pair, filling left first."""
    n = len(items)
    left_n = min(max_rows_per_col, math.ceil(n / 2)) if n > max_rows_per_col else n
    left_items = items[:left_n]
    right_items = items[left_n:left_n + max_rows_per_col]
    for i, item in enumerate(left_items):
        row_draw_fn(item, x, y + i * row_h)
    for i, item in enumerate(right_items):
        row_draw_fn(item, x + col_w, y + i * row_h)
    rows_used = max(len(left_items), len(right_items))
    return rows_used


# ============================================================
# LIVE DATA — calendar
# ============================================================
today_events = []
upcoming = []
calendar_url = os.environ.get("CALENDAR_ICAL_URL", "").strip()

if calendar_url:
    try:
        import urllib.request
        from icalendar import Calendar
        from dateutil.rrule import rrulestr

        req = urllib.request.Request(calendar_url, headers={"User-Agent": "KindleDashboard/1.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            calendar_data = response.read()
        cal = Calendar.from_ical(calendar_data)

        china_tz = ZoneInfo("Asia/Shanghai")
        now_cal = datetime.datetime.now(china_tz)
        today = now_cal.date()
        window_end = now_cal + datetime.timedelta(days=7)

        events = []
        for component in cal.walk("VEVENT"):
            summary = str(component.get("SUMMARY", "")).strip()
            dtstart = component.get("DTSTART")
            if not summary or not dtstart:
                continue
            start_value = dtstart.dt
            rrule = component.get("RRULE")

            if rrule and isinstance(start_value, datetime.datetime):
                if start_value.tzinfo is None:
                    start_value = start_value.replace(tzinfo=china_tz)
                else:
                    start_value = start_value.astimezone(china_tz)
                try:
                    rule_text = rrule.to_ical().decode("utf-8")
                    recurrence_rule = rrulestr(rule_text, dtstart=start_value)
                    for occurrence in recurrence_rule.between(now_cal, window_end, inc=True):
                        occurrence = occurrence.astimezone(china_tz)
                        events.append((occurrence.date(), occurrence.strftime("%H:%M"), summary, False))
                except Exception:
                    pass
            else:
                all_day = isinstance(start_value, datetime.date) and not isinstance(start_value, datetime.datetime)
                if all_day:
                    event_date = start_value
                    event_time = "All day"
                else:
                    if start_value.tzinfo:
                        start_value = start_value.astimezone(china_tz)
                    event_date = start_value.date()
                    event_time = start_value.strftime("%H:%M")
                if event_date >= today:
                    events.append((event_date, event_time, summary, all_day))

        events.sort(key=lambda x: (x[0], x[1] if x[1] != "All day" else "00:00"))

        for event_date, event_time, summary, all_day in events:
            if event_date == today:
                today_events.append((event_time, summary))
            elif event_date > today:
                upcoming.append((event_date.strftime("%a"), event_time, summary))
    except Exception as e:
        print("CALENDAR_ERROR:", type(e).__name__)
        today_events = []
        upcoming = []

# ============================================================
# LIVE DATA — weather
# ============================================================
WEATHER_CODES = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Cloudy",
    45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Showers", 81: "Showers", 82: "Heavy showers",
    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
}

weather = {
    "temp": "--", "feels_like": None, "humidity": "--", "condition": "Weather unavailable",
    "low": "--", "high": "--", "ok": False, "days": [],
}


def run(cmd, timeout=15):
    try:
        return subprocess.check_output(cmd, text=True, timeout=timeout, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


out = run(["python3", os.path.join(BASE, "weather.py")])
if out and out != "ERROR":
    parts = out.split("|")
    if len(parts) >= 6:
        try:
            temp, feels_like, hum, code, low, high = parts[:6]
            weather = {
                "temp": temp,
                "feels_like": None if feels_like in ("", "--") else feels_like,
                "humidity": hum,
                "condition": WEATHER_CODES.get(int(code), "Weather"),
                "low": low, "high": high, "ok": True, "days": [],
            }
            if len(parts) >= 7:
                for d in parts[6].split(";"):
                    hi, lo, c = d.split(",")
                    weather["days"].append({"high": hi, "low": lo, "code": int(c)})
        except Exception:
            pass

# ============================================================
# DATE / TIME
# ============================================================
now = datetime.datetime.now(ZoneInfo("Asia/Shanghai"))
short_date = now.strftime("%A, %-d %B")
greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 18 else "Good evening"
if CFG.get("name"):
    greeting = f"{greeting}, {CFG['name']}"
generated_stamp = now.strftime("Synced %H:%M")

# ============================================================
# HEADER — illustration bleeds from top right, text on the left
# ============================================================
IMG_ZONE_H = 500
SCENE_W = int(W * 0.62)
SCENE_H = IMG_ZONE_H

scene_path = None
for name in ("main-landscape.png", "main-landscape.jpg"):
    p = os.path.join(BASE, name)
    if os.path.exists(p):
        scene_path = p
        break

if scene_path:
    scene = Image.open(scene_path).convert("L")
    scene = cover_crop(scene, SCENE_W, SCENE_H, focus_x=0.5, focus_y=0.2)
    scene = process_photo(scene)
    scene = feather_left_edge(scene, 130)
    img.paste(scene, (W - SCENE_W, 0), )

# Text column, capped to the left of where the illustration starts
TEXT_MAX_W = W - SCENE_W + 40  # a little overlap allowed since the edge is feathered

if CFG.get("name"):
    txt(MARGIN, 44, greeting, GREETING, fill=MUTE)
    date_y = 76
else:
    date_y = 48

txt(MARGIN, date_y, short_date, DATE_HEAD)
if CFG.get("city"):
    txt(MARGIN, date_y + 62, CFG["city"], CITY_LINE, fill=MUTE)

stamp_w = text_w(generated_stamp, UPDATED)
txt(W - MARGIN - stamp_w, date_y + 4, generated_stamp, UPDATED, fill=170)

# Big temp inline with condition (baseline-aligned)
temp_y = date_y + 128
temp_str = f"{weather['temp']}°"
txt(MARGIN, temp_y, temp_str, BIG_TEMP)
cond_x = MARGIN + text_w(temp_str, BIG_TEMP) + 24
txt(cond_x, temp_y + 74, weather["condition"], CONDITION)

status_y = temp_y + 196
if weather["ok"]:
    bits = [f"H {weather['high']}°", f"L {weather['low']}°"]
    if weather["feels_like"] and weather["feels_like"] != weather["temp"]:
        bits.append(f"Feels like {weather['feels_like']}°")
    else:
        bits.append(f"{weather['humidity']}% humidity")
    txt(MARGIN, status_y, "   ·   ".join(bits), STATUS, fill=MUTE)
else:
    txt(MARGIN, status_y, "Live weather unavailable", STATUS, fill=MUTE)

y = IMG_ZONE_H + 56

# ============================================================
# UP NEXT — two columns
# ============================================================
rule(y)
y += 36
section_header(MARGIN, y, icon_calendar, "Up next")
y += 56

rows = []
if today_events:
    rows.extend(today_events)
if len(rows) < 4:
    for day, tm, title in upcoming[: 4 - len(rows)]:
        rows.append((f"{day} {tm}", title))
if not rows:
    rows = [("-", "Nothing on the calendar")]

col_w = (W - 2 * MARGIN) // 2
ROW_H_EVENTS = 108


def draw_event_row(item, x, ry):
    t, title = item
    txt(x, ry, t, ROW_TIME)
    f = fit_text(title, _SANS, col_w - 150, start_size=29, min_size=19)
    txt(x + 138, ry, title, f)


rows_used = two_columns(rows, MARGIN, y, col_w, ROW_H_EVENTS, draw_event_row, max_rows_per_col=2)
y += rows_used * ROW_H_EVENTS + 44

# ============================================================
# REMINDERS — two columns, checkboxes
# ============================================================
reminders = [r for r in CFG.get("reminders", []) if r]
if reminders:
    rule(y)
    y += 36
    section_header(MARGIN, y, icon_checklist, "Reminders")
    y += 56

    ROW_H_REM = 86

    def draw_reminder_row(item, x, ry):
        draw.rectangle((x, ry + 6, x + 26, ry + 32), outline=INK, width=3)
        f = fit_text(item, _SANS, col_w - 54, start_size=27, min_size=18)
        txt(x + 40, ry, item, f)

    rows_used = two_columns(reminders[:2], MARGIN, y, col_w, ROW_H_REM, draw_reminder_row, max_rows_per_col=1)
    y += rows_used * ROW_H_REM + 36

# ============================================================
# OUTLOOK
# ============================================================
rule(y)
y += 36
section_header(MARGIN, y, icon_outlook, "Outlook")
y += 68

days = weather.get("days", [])
if len(days) >= 2:
    n_days = min(3, len(days) - 1)
    col_w2 = (W - 2 * MARGIN) // n_days
    for i, day_data in enumerate(days[1:1 + n_days]):
        col_x = MARGIN + i * col_w2
        day_name = (now + datetime.timedelta(days=i + 1)).strftime("%A")
        txt(col_x, y, day_name, OUTLOOK_DAY)
        draw_weather_icon(col_x + 46, y + 92, day_data["code"], r=42)
        temp_str = f"{day_data['high']}°/{day_data['low']}°"
        txt(col_x + 104, y + 64, temp_str, OUTLOOK_TEMP)
        cond = WEATHER_CODES.get(day_data["code"], "")
        txt(col_x + 104, y + 106, cond, OUTLOOK_COND, fill=MUTE)
    y += 190
else:
    txt(MARGIN, y, "3-day forecast unavailable", STATUS, fill=MUTE)
    y += 140

# ============================================================
# FOOTER BANNER
# ============================================================
BANNER_H = 190
BANNER_Y = H - BANNER_H

footer_path = None
for name in ("footer-strip.jpg", "footer-strip.png"):
    p = os.path.join(BASE, name)
    if os.path.exists(p):
        footer_path = p
        break

if footer_path:
    foot = Image.open(footer_path).convert("L")
    foot = cover_crop(foot, W, BANNER_H)
    foot = process_photo(foot, gamma=0.9, contrast=1.25, sharpness=1.3)
    img.paste(foot, (0, BANNER_Y))
else:
    draw.rectangle((0, BANNER_Y, W, H), fill=25)

city = CFG.get("city", "")
if city:
    chip_w = text_w(city, CITY_BIG) + 56
    chip_h = 84
    chip_x, chip_y = MARGIN - 18, BANNER_Y + (BANNER_H - chip_h) // 2
    light_chip(chip_x, chip_y, chip_w, chip_h)
    txt(MARGIN, chip_y + (chip_h - 50) // 2 - 4, city, CITY_BIG)

# Guard: warn (don't crash) if the middle content ran into the footer band.
if y + 10 > BANNER_Y:
    print(f"LAYOUT_WARNING: content bottom {y} overlaps footer band starting {BANNER_Y}")

# ============================================================
# SAVE
# ============================================================
out_path = os.path.join(BASE, "dashboard.png")
img.save(out_path)
print(f"Created {out_path}")

kindle_path = os.path.join(BASE, "dashboard-kindle.png")
img.save(kindle_path)
print(f"Created {kindle_path}")
