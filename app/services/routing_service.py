import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# OpenRouteService matrix endpoint for car routing
ORS_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/driving-car"


async def get_distance_and_duration(
    start_lat: float, start_lng: float, end_lat: float, end_lng: float
) -> tuple[float, float]:
    """
    Returns (distance_km, duration_minutes) using OpenRouteService.
    If the API fails or key is missing, returns a naive fallback.
    """
    if not settings.OPENROUTESERVICE_API_KEY:
        logger.warning("OPENROUTESERVICE_API_KEY not set. Falling back to straight-line mock.")
        return _mock_distance_duration(start_lat, start_lng, end_lat, end_lng)

    # API wants [[lng, lat]]
    payload = {
        "locations": [[start_lng, start_lat], [end_lng, end_lat]],
        "metrics": ["distance", "duration"], 
    }
    headers = {
        "Authorization": settings.OPENROUTESERVICE_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(ORS_MATRIX_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            # ORS matrix response: duration is in seconds, distance is in meters by default
            # index [0][1] is start -> end
            duration_sec = data["durations"][0][1]
            distance_m = data["distances"][0][1]
            
            return distance_m / 1000.0, duration_sec / 60.0

    except Exception as e:
        logger.error(f"Routing API failed: {e}. Using fallback.")
        return _mock_distance_duration(start_lat, start_lng, end_lat, end_lng)


def _mock_distance_duration(
    start_lat: float, start_lng: float, end_lat: float, end_lng: float
) -> tuple[float, float]:
    """Naive euclidean fallback so the app works during demo if API fails."""
    # very rough approximation, good enough for fallback demo
    deg_dist = ((start_lat - end_lat)**2 + (start_lng - end_lng)**2)**0.5
    km = deg_dist * 111.0
    mins = (km / 40.0) * 60.0  # assume avg 40km/h
    return max(0.1, round(km, 2)), max(1.0, round(mins, 1))
