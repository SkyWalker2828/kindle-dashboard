import requests

url = "https://api.open-meteo.com/v1/forecast"

params = {
    "latitude": 29.08,
    "longitude": 119.65,
    "current": "temperature_2m,relative_humidity_2m,weather_code",
    "daily": "temperature_2m_max,temperature_2m_min",
    "timezone": "Asia/Shanghai",
    "forecast_days": 1,
}

try:
    r = requests.get(url, params=params, timeout=10, headers={"User-Agent": "Mozilla/5.0 (KindleDashboard/1.0)"})
    r.raise_for_status()
    data = r.json()

    current = data["current"]
    daily = data["daily"]

    print(f"{current['temperature_2m']:.0f}|{current['relative_humidity_2m']}|{current['weather_code']}|{daily['temperature_2m_min'][0]:.0f}|{daily['temperature_2m_max'][0]:.0f}")

except Exception:
    print("ERROR")
