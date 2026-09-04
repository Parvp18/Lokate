import math
from datetime import datetime, timezone, timedelta

from app.services import routing_service, weather_service

# Percentage inflators for travel time based on destination weather
WEATHER_MULTIPLIERS = {
    "CLEAR": 1.00,    # baseline
    "MILD": 1.10,     # +10%
    "MODERATE": 1.25, # +25%
    "SEVERE": 1.50,   # +50%
}


async def predict_eta(
    start_lat: float, start_lng: float, end_lat: float, end_lng: float
) -> tuple[float, float, datetime, str]:
    """
    Returns:
    - distance (km)
    - adjusted_duration (minutes)
    - expected_arrival (timestamp)
    - weather_severity_applied (str for reasoning)
    """
    
    # Execute calls concurrently
    import asyncio
    route_task = asyncio.create_task(
        routing_service.get_distance_and_duration(start_lat, start_lng, end_lat, end_lng)
    )
    weather_task = asyncio.create_task(
        weather_service.get_weather_severity(end_lat, end_lng)
    )
    
    dist_km, baseline_duration = await route_task
    severity = await weather_task
    
    multiplier = WEATHER_MULTIPLIERS.get(severity, 1.0)
    
    adjusted_duration = math.ceil(baseline_duration * multiplier)
    expected_arrival = datetime.now(timezone.utc) + timedelta(minutes=adjusted_duration)
    
    return dist_km, adjusted_duration, expected_arrival, severity
