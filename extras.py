"""Bepul qo'shimcha xizmatlar: ob-havo (open-meteo), valyuta kursi (cbu.uz). Kalit kerak emas."""

import aiohttp

WEATHER_CODES = {
    0: "ochiq osmon ☀️", 1: "asosan ochiq 🌤", 2: "qisman bulutli ⛅", 3: "bulutli ☁️",
    45: "tuman 🌫", 48: "qirovli tuman 🌫", 51: "mayda yomg'ir 🌦", 53: "yomg'ir 🌦", 55: "kuchli mayda yomg'ir 🌧",
    61: "yengil yomg'ir 🌧", 63: "yomg'ir 🌧", 65: "kuchli yomg'ir 🌧", 71: "yengil qor 🌨", 73: "qor 🌨",
    75: "kuchli qor ❄️", 80: "jala 🌦", 81: "jala 🌧", 82: "kuchli jala ⛈", 95: "momaqaldiroq ⛈",
}
_TIMEOUT = aiohttp.ClientTimeout(total=15)


async def _json(url: str, params: dict | None = None, timeout: aiohttp.ClientTimeout = _TIMEOUT):
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(url, params=params) as r:
            r.raise_for_status()
            return await r.json(content_type=None)


async def weather(city: str = "Toshkent") -> str:
    geo = await _json("https://geocoding-api.open-meteo.com/v1/search",
                      {"name": city, "count": 1, "language": "uz"})
    if not geo.get("results"):
        return f"'{city}' shahri topilmadi."
    place = geo["results"][0]
    data = await _json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto", "forecast_days": 3,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        },
    )
    cur = data["current"]
    lines = [
        f"{place['name']}: hozir {cur['temperature_2m']:.0f}°C (his qilinishi {cur['apparent_temperature']:.0f}°C), "
        f"{WEATHER_CODES.get(cur['weather_code'], '')}, shamol {cur['wind_speed_10m']:.0f} km/s"
    ]
    d = data["daily"]
    for i, day in enumerate(d["time"]):
        lines.append(
            f"{day}: {d['temperature_2m_min'][i]:.0f}…{d['temperature_2m_max'][i]:.0f}°C, "
            f"{WEATHER_CODES.get(d['weather_code'][i], '')}, yog'ingarchilik ehtimoli {d['precipitation_probability_max'][i]}%"
        )
    return "\n".join(lines)


async def currency(codes: str = "USD,EUR,RUB") -> str:
    """Avval O'zbekiston Markaziy banki; u javob bermasa (chet eldagi serverdan ochilmasligi mumkin) — zaxira manba."""
    want = {c.strip().upper() for c in codes.split(",") if c.strip()}
    try:
        rows = await _json("https://cbu.uz/uz/arkhiv-kursov-valyut/json/", timeout=aiohttp.ClientTimeout(total=6))
        out = [f"1 {r['Ccy']} = {r['Rate']} so'm ({r['Diff']})" for r in rows if r["Ccy"] in want]
        if out:
            return f"Markaziy bank kursi ({rows[0]['Date']}):\n" + "\n".join(out)
    except Exception:
        pass
    data = await _json("https://open.er-api.com/v6/latest/USD")
    rates = data["rates"]
    out = [f"1 {c} = {rates['UZS'] / rates[c]:,.2f} so'm".replace(",", " ") for c in sorted(want) if c in rates]
    if not out:
        return "Bunday valyuta topilmadi."
    return f"Valyuta kursi (xalqaro manba, {data.get('time_last_update_utc', '')[:16]}):\n" + "\n".join(out)
