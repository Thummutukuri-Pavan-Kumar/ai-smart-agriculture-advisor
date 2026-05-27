# backend/utils.py
import os
import time
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip() or None
DEFAULT_TIMEOUT = 8

def _now_ts():
    return int(time.time())

# --- Geocode / OneCall helpers ---
def geocode_city(city: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    Return first geocode candidate dict: { lat, lon, name, country, state? } or None
    """
    if not OPENWEATHER_API_KEY or not city:
        return None
    try:
        url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {"q": city, "limit": 1, "appid": OPENWEATHER_API_KEY}
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        item = data[0]
        return {
            "lat": float(item.get("lat")),
            "lon": float(item.get("lon")),
            "name": item.get("name") or city,
            "country": item.get("country") or "",
            "state": item.get("state") or ""
        }
    except requests.exceptions.HTTPError as he:
        # e.g. 401 invalid key, 429 rate limit => helpful message in logs
        print("[utils.geocode_city] HTTPError:", he, "status_code=", getattr(he.response, "status_code", None), flush=True)
        return None
    except Exception as e:
        print("[utils.geocode_city] error:", e, flush=True)
        return None


def weather_for_coords(lat: float, lon: float, timeout: int = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    Call OneCall API and return wrapper {"onecall": <json>} or None
    """
    if not OPENWEATHER_API_KEY:
        print("[utils.weather_for_coords] No OPENWEATHER_API_KEY configured", flush=True)
        return None
    try:
        url = "https://api.openweathermap.org/data/2.5/onecall"
        params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric", "exclude": "minutely"}
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return {"onecall": r.json()}
    except requests.exceptions.HTTPError as he:
        print("[utils.weather_for_coords] HTTPError:", he, "status_code=", getattr(he.response, "status_code", None), flush=True)
        return {"onecall": None}
    except Exception as e:
        print("[utils.weather_for_coords] error:", e, flush=True)
        return {"onecall": None}


def call_openweather_city(city: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    Return:
      - {"lat":..., "lon":..., "name":..., "country":..., "state":..., "onecall": {...}} on success
      - or {"current": {...}} if geocode fails but current weather endpoint succeeded
      - or None on failure/unconfigured
    """
    if not OPENWEATHER_API_KEY or not city:
        return None

    geo = geocode_city(city, timeout=timeout)
    if geo:
        oc = weather_for_coords(geo["lat"], geo["lon"], timeout=timeout)
        # oc is {"onecall": <json> or None}
        res = {**geo, "onecall": None}
        if isinstance(oc, dict) and "onecall" in oc:
            res["onecall"] = oc["onecall"]
        return res

    # fallback: current weather by city name
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return {"current": r.json()}
    except requests.exceptions.HTTPError as he:
        print("[utils.call_openweather_city] HTTPError:", he, flush=True)
        return None
    except Exception as e:
        print("[utils.call_openweather_city] error:", e, flush=True)
        return None


def estimate_next_24h_rain_mm(response: Optional[Dict[str, Any]]) -> float:
    """
    Accepts wrapper returned from call_openweather_city() or raw onecall dict.
    Returns total rain mm for next 24 hours (float).
    """
    if not response:
        return 0.0

    # if wrapper with 'onecall' key
    oc = None
    if isinstance(response, dict) and "onecall" in response:
        oc = response.get("onecall")
    elif isinstance(response, dict) and ("current" in response and "hourly" not in response):
        # fallback wrapper: {"current": {...}}
        # current may contain 'rain'
        current = response.get("current", {})
        if isinstance(current.get("rain"), dict):
            return float(current["rain"].get("1h", 0.0) or 0.0)
        return float(current.get("rain", 0.0) or 0.0)
    else:
        # maybe they passed raw onecall dict
        oc = response

    if not oc:
        return 0.0

    try:
        hourly = oc.get("hourly")
        if isinstance(hourly, list) and len(hourly) > 0:
            total = 0.0
            for h in hourly[:24]:
                r = h.get("rain")
                if isinstance(r, dict):
                    total += float(r.get("1h", 0.0) or 0.0)
                else:
                    total += float(r or 0.0)
            return round(total, 2)
    except Exception:
        pass

    try:
        daily = oc.get("daily")
        if isinstance(daily, list) and len(daily) > 0:
            return float(daily[0].get("rain", 0.0) or 0.0)
    except Exception:
        pass

    return 0.0
