#!/usr/bin/env python3
"""
Kindle Dashboard - portrait 1236x1648, e-ink editorial.
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
    defaults = {"name": "", "city": "-", "country": ""}
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
# CANVAS - PORTRAIT
# ============================================================

W, H = 1236, 1648
img = Image.new("L", (W, H), 255)
draw = ImageDraw.Draw(img)

MARGIN = 56


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

HN_LIGHT   = 7
HN_REGULAR = 0
HN_MEDIUM  = 10

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

CLOCK     = F(_SERIF, 88)
GREETING  = F(_SANS, 30, HN_MEDIUM)
DATE      = F(_SANS, 22, HN_LIGHT)
BIG_TEMP  = F(_SERIF, 160)
CONDITION = F(_SERIF, 54)
STATUS    = F(_SANS, 24, HN_MEDIUM)
SECTION   = F(_SERIF, 32)
ROW_MAIN  = F(_SANS, 24, HN_REGULAR)
CITY_BIG  = F(_SERIF, 44)
TEMP_SIDE = F(_SERIF, 38)
OUTLOOK_B = F(_SANS, 22, HN_MEDIUM)
OUTLOOK_S = F(_SANS, 20, HN_LIGHT)
OUTLOOK_T = F(_SERIF, 32)
META      = F(_MONO, 13)


# ============================================================
# VERTICAL GRID (portrait 1648 tall)
# ============================================================
#
#  y=0      header image (full width, 440 tall)
#  y=440    -- image bottom --
#  y=470    clock (big)
#  y=590    greeting
#  y=628    date
#  y=690    big temp
#  y=890    condition
#  y=950    status line 1
#  y=990    status line 2
#  y=1050   -- rule 1 --
#  y=1080   UP NEXT label
#  y=1130   up next rows (3 x 54 = 162)
#  y=1310   -- rule 2 --
#  y=1340   OUTLOOK label
#  y=1390   outlook cards (2 days)
#  y=1470   -- rule 3 --
#  y=1490   city / temps / next event
#  y=1520   -- banner starts (128 tall) --
#  y=1648   end
#
# ============================================================

IMG_H       = 380
CLOCK_Y     = 410
GREETING_Y  = 520
DATE_Y      = 556
TEMP_Y      = 610
COND_Y      = 800
STATUS1_Y   = 856
STATUS2_Y   = 890
RULE_1      = 940
UP_NEXT_Y   = 968
ROW_H       = 54
ROWS        = 3
RULE_2      = UP_NEXT_Y + 50 + ROWS * ROW_H + 10   # 1302
OUTLOOK_Y   = RULE_2 + 30                            # 1332
CARD_Y      = OUTLOOK_Y + 50                         # 1382
BANNER_H    = 190
BANNER_Y    = H - BANNER_H


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

def section_label(x, y, s):
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
    im = ImageOps.grayscale(im)
    im = ImageOps.autocontrast(im, cutoff=1)
    lut = [min(255, int(((i / 255.0) ** 1.05) * 255)) for i in range(256)]
    im = im.point(lut)
    im = ImageEnhance.Contrast(im).enhance(1.3)
    im = ImageEnhance.Sharpness(im).enhance(1.5)
    return im


def process_banner(im):
    im = ImageOps.grayscale(im)
    im = ImageOps.autocontrast(im, cutoff=1)
    lut = [min(255, int(((i / 255.0) ** 0.9) * 255)) for i in range(256)]
    im = im.point(lut)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    im = ImageEnhance.Sharpness(im).enhance(1.3)
    return im


def draw_weather_icon(x, y, code, size=44):
    """Draw a simple line-art weather icon for the given code."""
    cx, cy = x + size // 2, y + size // 2
    r = size // 3

    # Sun (always draw for clear/partly)
    if code in (0, 1):
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=0, width=3)
        # rays
        import math
        for angle in range(0, 360, 45):
            a = math.radians(angle)
            x1 = cx + int(math.cos(a) * (r + 6))
            y1 = cy + int(math.sin(a) * (r + 6))
            x2 = cx + int(math.cos(a) * (r + 14))
            y2 = cy + int(math.sin(a) * (r + 14))
            draw.line((x1, y1, x2, y2), fill=0, width=2)

    # Cloud
    elif code in (2, 3, 45, 48):
        draw.ellipse((cx - 20, cy - 6, cx + 4, cy + 18), outline=0, width=3)
        draw.ellipse((cx - 6, cy - 16, cx + 22, cy + 12), outline=0, width=3)
        draw.ellipse((cx + 10, cy - 6, cx + 30, cy + 18), outline=0, width=3)

    # Rain
    elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        draw.ellipse((cx - 22, cy - 12, cx + 4, cy + 12), outline=0, width=3)
        draw.ellipse((cx - 8, cy - 22, cx + 22, cy + 8), outline=0, width=3)
        # rain drops
        for dx in (-10, 2, 14):
            draw.line((cx + dx, cy + 16, cx + dx - 3, cy + 26), fill=0, width=2)

    # Snow
    elif code in (71, 73, 75):
        draw.ellipse((cx - 22, cy - 12, cx + 4, cy + 12), outline=0, width=3)
        draw.ellipse((cx - 8, cy - 22, cx + 22, cy + 8), outline=0, width=3)
        for dx in (-10, 2, 14):
            draw.ellipse((cx + dx - 2, cy + 18, cx + dx + 2, cy + 22), outline=0, width=1)

    # Thunder
    elif code in (95, 96, 99):
        draw.ellipse((cx - 22, cy - 12, cx + 4, cy + 12), outline=0, width=3)
        draw.ellipse((cx - 8, cy - 22, cx + 22, cy + 8), outline=0, width=3)
        # lightning bolt
        draw.line((cx, cy + 10, cx - 4, cy + 22), fill=0, width=3)
        draw.line((cx - 4, cy + 22, cx + 4, cy + 22), fill=0, width=3)
        draw.line((cx + 4, cy + 22, cx, cy + 34), fill=0, width=3)


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
upcoming = []

calendar_url = os.environ.get("CALENDAR_ICAL_URL", "").strip()

if calendar_url:
    try:
        import urllib.request
        from icalendar import Calendar
        from dateutil.rrule import rrulestr
        from zoneinfo import ZoneInfo

        req = urllib.request.Request(
            calendar_url,
            headers={"User-Agent": "KindleDashboard/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            calendar_data = response.read()

        cal = Calendar.from_ical(calendar_data)
        china_tz = ZoneInfo("Asia/Shanghai")
        now = datetime.datetime.now(china_tz)
        today = now.date()
        window_end = now + datetime.timedelta(days=7)

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

                    for occurrence in recurrence_rule.between(now, window_end, inc=True):
                        occurrence = occurrence.astimezone(china_tz)
                        events.append((
                            occurrence.date(),
                            occurrence.strftime("%H:%M"),
                            summary,
                            False,
                        ))
                except Exception:
                    pass

            else:
                all_day = (
                    isinstance(start_value, datetime.date)
                    and not isinstance(start_value, datetime.datetime)
                )

                if all_day:
                    event_date = start_value
                    event_time = "All day"
                else:
                    if start_value.tzinfo:
                        start_value = start_value.astimezone(china_tz)
                    event_date = start_value.date()
                    event_time = start_value.strftime("%H:%M")

                if event_date >= today:
                    events.append((
                        event_date,
                        event_time,
                        summary,
                        all_day,
                    ))

        events.sort(
            key=lambda x: (
                x[0],
                x[1] if x[1] != "All day" else "00:00",
            )
        )

        for event_date, event_time, summary, all_day in events:
            if event_date == today:
                today_events.append((event_time, summary))
            elif event_date > today:
                day_name = event_date.strftime("%a")
                upcoming.append((day_name, event_time, summary))

    except Exception as e:
        print("CALENDAR_ERROR:", type(e).__name__)
        today_events = []
        upcoming = []

WEATHER_CODES = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Cloudy",
    45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Showers", 81: "Showers", 82: "Heavy showers",
    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
}

weather = {
    "temp": "--", "humidity": "--", "condition": "Weather unavailable",
    "low": "--", "high": "--", "ok": False, "days": [],
}

out = run(["python3", os.path.join(BASE, "weather.py")], timeout=15)
if out and out != "ERROR":
    parts = out.split("|")
    if len(parts) >= 5:
        try:
            temp, hum, code, low, high = parts[0], parts[1], parts[2], parts[3], parts[4]
            weather = {
                "temp": temp, "humidity": hum,
                "condition": WEATHER_CODES.get(int(code), "Weather"),
                "low": low, "high": high, "ok": True, "days": [],
            }
            if len(parts) >= 6:
                for d in parts[5].split(";"):
                    hi, lo, c = d.split(",")
                    weather["days"].append({
                        "high": hi, "low": lo, "code": int(c),
                    })
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
# HEADER IMAGE - FULL WIDTH AT TOP
# ============================================================

scene_path = None
for name in ("main-landscape.png", "main-landscape.jpg"):
    p = os.path.join(BASE, name)
    if os.path.exists(p):
        scene_path = p
        break

if scene_path:
    scene = Image.open(scene_path).convert("L")
    scene = cover_crop(scene, W, IMG_H)
    scene = process_photo(scene)
    img.paste(scene, (0, 0))


# ============================================================
# CLOCK + GREETING + DATE
# ============================================================

txt(MARGIN, CLOCK_Y, clock, CLOCK)
txt(MARGIN, GREETING_Y, greeting, GREETING)
txt(MARGIN, DATE_Y, short_date, DATE)


# ============================================================
# BIG TEMP + CONDITION + STATUS
# ============================================================

txt(MARGIN, TEMP_Y, f"{weather['temp']}°", BIG_TEMP)
txt(MARGIN, COND_Y, weather["condition"], CONDITION)

if weather["ok"]:
    txt(MARGIN, STATUS1_Y, f"Feels like {weather['temp']}°", STATUS)
    txt(MARGIN, STATUS2_Y,
        f"H {weather['high']}°   L {weather['low']}°   {weather['humidity']}% humidity",
        STATUS)
else:
    txt(MARGIN, STATUS1_Y, "Live weather unavailable", STATUS)


# ============================================================
# RULE 1
# ============================================================

rule(RULE_1)


# ============================================================
# UP NEXT
# ============================================================

section_label(MARGIN, UP_NEXT_Y, "up next")

rows = []
if today_events:
    for t, title in today_events[:ROWS]:
        rows.append((t, title))
if len(rows) < ROWS:
    for day, time, title in upcoming[: ROWS - len(rows)]:
        rows.append((f"{day} {time}", title))
if not rows:
    rows = [("-", "Calendar unavailable")]

row_y = UP_NEXT_Y + 50
for t, title in rows[:ROWS]:
    txt(MARGIN, row_y, t, ROW_MAIN)
    title_x = MARGIN + 220
    title_max = W - MARGIN - title_x
    f = fit_text(title, _SANS, title_max, start_size=24, min_size=15, weight=HN_LIGHT)
    txt(title_x, row_y, title, f)
    row_y += ROW_H


# ============================================================
# RULE 2
# ============================================================

rule(RULE_2)


# ============================================================
# 3-DAY OUTLOOK
# ============================================================

section_label(MARGIN, OUTLOOK_Y, "outlook")

days = weather.get("days", [])
if len(days) >= 2:
    col_w = (W - 2 * MARGIN) // 2
    for i, day_data in enumerate(days[1:3]):   # skip today, show next 2
        col_x = MARGIN + i * col_w

        # Day label
        day_name = (now + datetime.timedelta(days=i + 1)).strftime("%A")
        txt(col_x, CARD_Y, day_name, OUTLOOK_B)

        # Weather icon
        draw_weather_icon(col_x, CARD_Y + 34, day_data["code"], size=52)

        # Temps
        temp_str = f"{day_data['high']}° / {day_data['low']}°"
        txt(col_x + 70, CARD_Y + 48, temp_str, OUTLOOK_T)

        # Condition name small
        cond = WEATHER_CODES.get(day_data["code"], "")
        txt(col_x + 70, CARD_Y + 88, cond, OUTLOOK_S)
else:
    txt(MARGIN, CARD_Y, "3-day forecast unavailable", STATUS)


# ============================================================
# RULE 3
# ============================================================



# ============================================================
# FOOTER BANNER - FULL WIDTH AT BOTTOM
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

    # City name overlay - black serif, faux-bold, on the banner
    city = CFG.get("city", "")
    if city:
        city_font = F(_SERIF, 56)
        cx, cy = MARGIN, BANNER_Y + 24
        # Faux-bold via multi-stroke
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                draw.text((cx + dx, cy + dy), city, font=city_font, fill=0)


# ============================================================
# SAVE
# ============================================================

out_path = os.path.join(BASE, "dashboard.png")
img.save(out_path)
print(f"Created {out_path}")

kindle_path = os.path.join(BASE, "dashboard-kindle.png")
img.save(kindle_path)
print(f"Created {kindle_path}")
