import json
import time
import urllib.request
from urllib.parse import quote_plus


_WEATHER_CACHE = {}  # {cache_key: (timestamp, weather_text)}

def weather_action(
    parameters: dict,
    player=None,
    session_memory=None,
) -> str:
    city = (parameters or {}).get("city", "")
    when = (parameters or {}).get("time", "today")

    if not city or not isinstance(city, str) or not city.strip():
        # 1. Fall back to user's saved location in memory if available
        try:
            from memory.memory_manager import load_memory
            mem = load_memory()
            city = mem.get("identity", {}).get("city", {}).get("value", "")
        except Exception:
            city = ""

    city = (city or "").strip()
    when = (when or "today").strip()
    search_q = city.split(",")[0].strip() if "," in city else city

    # Cache check (5 minutes = 300 seconds)
    cache_key = f"{search_q.lower()}_{when.lower()}"
    now_ts = time.time()
    if cache_key in _WEATHER_CACHE:
        cached_ts, cached_text = _WEATHER_CACHE[cache_key]
        if now_ts - cached_ts < 300.0:
            print(f"[Weather] Cache hit for {cache_key}: {cached_text}")
            _log(cached_text, player)
            return cached_text

    # 1. Fetch real-time live weather data (fast, no browser popup)
    weather_text = ""
    try:
        url = f"https://wttr.in/{quote_plus(search_q)}?format=j1" if search_q else "https://wttr.in/?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=2.5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if not city:
                try:
                    detected_city = data["nearest_area"][0]["areaName"][0]["value"]
                    if detected_city:
                        city = detected_city
                        # Silently remember for subsequent calls
                        try:
                            from memory.memory_manager import update_memory
                            update_memory({"identity": {"city": {"value": city}}})
                        except Exception:
                            pass
                except Exception:
                    city = "your area"
            cur = data["current_condition"][0]
            w = data["weather"][0]
            desc = cur["weatherDesc"][0]["value"].strip()
            temp_c = cur["temp_C"]
            feels_c = cur["FeelsLikeC"]
            max_c = w["maxtempC"]
            min_c = w["mintempC"]

            weather_text = (
                f"In {city}, it is {temp_c}°C and {desc}, feeling like {feels_c}°C. "
                f"Today's high is {max_c}°C with a low of {min_c}°C."
            )
            _WEATHER_CACHE[cache_key] = (now_ts, weather_text)
    except Exception as e:
        print(f"[Weather] wttr.in query failed ({e}), falling back to grounded search...")

    # 2. Fallback to Gemini Grounded Search if wttr.in is unavailable
    if not weather_text:
        try:
            from core import gemini
            res = gemini.call(
                f"Current live weather in {city} {when}: exact temperature in Celsius, sky condition, humidity, and forecast today. Keep it to 2 clear sentences.",
                tier=gemini.SEARCH,
                config={"tools": [{"google_search": {}}]},
                timeout_ms=10000,
            )
            if res and res.text:
                weather_text = res.text.strip()
        except Exception as e:
            print(f"[Weather] Grounded search fallback failed: {e}")

    if not weather_text:
        weather_text = f"Sir, I could not retrieve the weather for {city} right now."

    _log(weather_text, player)

    # Show on HUD content panel if available
    if player and hasattr(player, "show_content"):
        try:
            player.show_content(f"WEATHER — {city.upper()}", weather_text)
        except Exception:
            pass

    if session_memory:
        try:
            session_memory.set_last_search(query=f"weather in {city}", response=weather_text)
        except Exception:
            pass

    return weather_text


def _log(message: str, player=None) -> None:
    print(f"[Weather] {message}")
    if player and hasattr(player, "write_log"):
        try:
            player.write_log(f"MAGNUS AI: {message}")
        except Exception:
            pass


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "weather_report",
    "description": "Fetches and reports real-time live weather, temperature, sky conditions, and forecast for any city or location. Always use this tool when the user asks about the weather. Magnus AI will speak the weather directly to the user.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "city": {
                "type": "STRING",
                "description": "City name or location (e.g. 'Suri', 'Kolkata', 'London', 'New York')"
            },
            "time": {
                "type": "STRING",
                "description": "Time frame (e.g. 'today', 'tomorrow', 'this evening')"
            }
        },
        "required": [
            "city"
        ]
    },
    "handler": weather_action,
}
