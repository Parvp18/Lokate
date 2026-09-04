"""Tests for the ETA/Routing/Weather integration layer."""

from unittest.mock import patch
import pytest

from app.services import eta_service


@pytest.mark.asyncio
@patch("app.services.routing_service.get_distance_and_duration")
@patch("app.services.weather_service.get_weather_severity")
async def test_predict_eta_clear_weather(mock_weather, mock_routing):
    # Baseline: 10km, 20 mins, CLEAR
    mock_routing.return_value = (10.0, 20.0)
    mock_weather.return_value = "CLEAR"

    dist, dur, eta, sev = await eta_service.predict_eta(0, 0, 1, 1)

    assert dist == 10.0
    assert dur == 20.0 # 20 * 1.00 = 20
    assert sev == "CLEAR"


@pytest.mark.asyncio
@patch("app.services.routing_service.get_distance_and_duration")
@patch("app.services.weather_service.get_weather_severity")
async def test_predict_eta_severe_weather(mock_weather, mock_routing):
    # Baseline: 10km, 20 mins, SEVERE
    mock_routing.return_value = (10.0, 20.0)
    mock_weather.return_value = "SEVERE"

    dist, dur, eta, sev = await eta_service.predict_eta(0, 0, 1, 1)

    assert dist == 10.0
    assert dur == 30.0 # 20 * 1.50 = 30
    assert sev == "SEVERE"


@pytest.mark.asyncio
@patch("app.services.routing_service.get_distance_and_duration")
@patch("app.services.weather_service.get_weather_severity")
async def test_predict_eta_moderate_weather(mock_weather, mock_routing):
    # Baseline: 50km, 60 mins, MODERATE
    mock_routing.return_value = (50.0, 60.0)
    mock_weather.return_value = "MODERATE"

    dist, dur, eta, sev = await eta_service.predict_eta(0, 0, 1, 1)

    assert dist == 50.0
    assert dur == 75.0 # 60 * 1.25 = 75
    assert sev == "MODERATE"
