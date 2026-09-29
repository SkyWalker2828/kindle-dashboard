import requests

URL = "https://api.open-meteo.com/v1/forecast"
PARAMS = {
    "latitude": 29.08,
    "longitude": 119.65,
    "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code",
    "daily": "temperature_2m_max,temperature_2m_min,weather_code",
    "timezone": "Asia/Shanghai",
    "forecast_days": 3,
}

try:
    r = requests.get(URL, params=PARAMS, timeout=10,
                      headers={"User-Agent": "Mozilla/5.0 (KindleDashboard/1.0)"})
    r.raise_for_status()
    data = r.json()
    current = data["current"]
    daily = data["daily"]

    days = []
    for i in range(3):
        days.append(
            f"{daily['temperature_2m_max'][i]:.0f},"
            f"{daily['temperature_2m_min'][i]:.0f},"
            f"{daily['weather_code'][i]}"
        )

    # Output: temp | feels_like | humidity | code | today_low | today_high | day1,day2,day3
    print(
        f"{current['temperature_2m']:.0f}|"
        f"{current['apparent_temperature']:.0f}|"
        f"{current['relative_humidity_2m']}|"
        f"{current['weather_code']}|"
        f"{daily['temperature_2m_min'][0]:.0f}|"
        f"{daily['temperature_2m_max'][0]:.0f}|"
        f"{';'.join(days)}"
    )
except Exception:
    print("ERROR")
