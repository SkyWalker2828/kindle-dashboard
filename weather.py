import requests

url = "http://api.open-meteo.com/v1/forecast"

params = {
    "latitude": 29.08,
    "longitude": 119.65,
    "current": "temperature_2m,relative_humidity_2m,weather_code",
    "daily": "temperature_2m_max,temperature_2m_min,weather_code",
    "timezone": "Asia/Shanghai",
    "forecast_days": 3,
}

try:
    r = requests.get(url, params=params, timeout=10,
                     headers={"User-Agent": "Mozilla/5.0 (KindleDashboard/1.0)"})
    r.raise_for_status()
    data = r.json()

    current = data["current"]
    daily = data["daily"]

    # Format: current fields, then 3 days (max,min,code) joined by ";"
    days = []
    for i in range(3):
        days.append(f"{daily['temperature_2m_max'][i]:.0f},{daily['temperature_2m_min'][i]:.0f},{daily['weather_code'][i]}")

    print(f"{current['temperature_2m']:.0f}|{current['relative_humidity_2m']}|{current['weather_code']}|{daily['temperature_2m_min'][0]:.0f}|{daily['temperature_2m_max'][0]:.0f}|{';'.join(days)}")

except Exception:
    print("ERROR")
