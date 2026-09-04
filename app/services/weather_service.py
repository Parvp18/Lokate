import logging

import httpx
from datetime import datetime, timezone, timedelta

from app.config import settings

logger = logging.getLogger(__name__)

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"

# Simple in-memory cache to avoid rate-limits
_cache = {}
CACHE_TTL = timedelta(minutes=10)


async def get_weather_severity(lat: float, lng: float) -> str:
    """
    Returns a severity category: 'CLEAR', 'MILD', 'MODERATE', or 'SEVERE'.
    Caches the response for 10 minutes per roughly 1km grid point.
    """
    if not settings.OPENWEATHERMAP_API_KEY:
        logger.warning("OPENWEATHERMAP_API_KEY not set. Falling back to CLEAR.")
        return "CLEAR"

    # Round to 2 decimal places to bucket cache (~1.1km grid)
    cache_key = f"{round(lat, 2)},{round(lng, 2)}"
    now = datetime.now(timezone.utc)
    
    if cache_key in _cache:
        cached_severity, expires_at = _cache[cache_key]
        if now < expires_at:
            return cached_severity

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                OWM_URL,
                params={
                    "lat": lat,
                    "lon": lng,
                    "appid": settings.OPENWEATHERMAP_API_KEY,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            
            severity = _parse_severity(data.get("weather", []))
            _cache[cache_key] = (severity, now + CACHE_TTL)
            return severity
            
    except Exception as e:
        logger.error(f"Weather API failed: {e}. Assuming CLEAR.")
        return "CLEAR"


def _parse_severity(weather_list: list[dict]) -> str:
    if not weather_list:
        return "CLEAR"
        
    main = weather_list[0].get("main", "").lower()
    desc = weather_list[0].get("description", "").lower()
    
    # Simple deterministic categorization
    if main in ["thunderstorm", "tornado", "squall", "hurricane"]:
        return "SEVERE"
    if main in ["snow"] and "heavy" in desc:
        return "SEVERE"
    
    if main in ["rain", "snow"]:
        return "MODERATE"
    if main in ["drizzle", "mist", "fog", "haze"]:
        return "MILD"
        
    return "CLEAR"
