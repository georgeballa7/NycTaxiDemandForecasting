import requests

from frontend.config.settings import (
    API_BASE_URL,
    API_TIMEOUT,
)


def _get(endpoint, params=None):
    """Send a GET request to the configured API endpoint and return decoded JSON."""
    response = requests.get(
        f"{API_BASE_URL}{endpoint}",
        params=params,
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _post(endpoint, payload):
    """Send a JSON POST request to the configured API endpoint and return decoded JSON."""
    response = requests.post(
        f"{API_BASE_URL}{endpoint}",
        json=payload,
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_health():
    """Return the backend API health status."""
    return _get("/health")


def get_demand_date_range():
    """Return the minimum and maximum available demand dates."""
    return _get("/data-range")


def get_zones():
    """Return all taxi-zone reference records."""
    return _get("/zones")


def get_metrics():
    """Return historical-model evaluation metrics."""
    return _get("/metrics")


def get_future_model_metrics():
    """Return future-forecast backtest metrics."""
    return _get("/future-model-metrics")


def get_feature_importance():
    """Return historical-model feature importance values."""
    return _get("/feature-importance")


def predict_future_demand(location_id: int, forecast_datetime):
    """Request a future demand prediction for a zone and forecast datetime."""
    return _post(
        "/predict",
        {
            "location_id": location_id,
            "forecast_datetime": forecast_datetime.isoformat(),
        },
    )


def get_demand_by_hour():
    """Return system-wide demand aggregated by hour of day."""
    return _get("/eda/demand-by-hour")


def get_demand_by_weekday():
    """Return system-wide demand aggregated by weekday."""
    return _get("/eda/demand-by-weekday")


def get_demand_over_time(start_date=None, end_date=None):
    """Return system-wide daily demand, optionally bounded by dates."""
    params = {}
    if start_date is not None:
        params["start_date"] = str(start_date)
    if end_date is not None:
        params["end_date"] = str(end_date)
    return _get("/eda/demand-over-time", params=params)


def get_top_zones(limit: int = 10):
    """Return the highest-demand taxi zones up to the requested limit."""
    return _get("/eda/top-zones", params={"limit": limit})


def get_predictions(location_id: int, start_date=None, end_date=None):
    """Return historical actual/predicted demand for a zone and optional dates."""
    params = {}
    if start_date is not None:
        params["start_date"] = str(start_date)
    if end_date is not None:
        params["end_date"] = str(end_date)
    return _get(f"/predictions/{location_id}", params=params)


def get_zone_demand_by_hour(location_id: int, start_date=None, end_date=None):
    """Return hourly demand aggregates for one zone and optional date range."""
    params = {}
    if start_date is not None:
        params["start_date"] = str(start_date)
    if end_date is not None:
        params["end_date"] = str(end_date)
    return _get(f"/eda/zones/{location_id}/demand-by-hour", params=params)


def get_zone_demand_by_weekday(location_id: int, start_date=None, end_date=None):
    """Return weekday demand aggregates for one zone and optional date range."""
    params = {}
    if start_date is not None:
        params["start_date"] = str(start_date)
    if end_date is not None:
        params["end_date"] = str(end_date)
    return _get(f"/eda/zones/{location_id}/demand-by-weekday", params=params)


def get_zone_demand_over_time(location_id: int, start_date=None, end_date=None):
    """Return daily demand history for one zone and optional date range."""
    params = {}
    if start_date is not None:
        params["start_date"] = str(start_date)
    if end_date is not None:
        params["end_date"] = str(end_date)
    return _get(f"/eda/zones/{location_id}/demand-over-time", params=params)


def get_business_summary():
    """Return headline business-performance metrics."""
    return _get("/business/summary")


def get_revenue_over_time():
    """Return daily revenue and trip metrics."""
    return _get("/business/revenue-over-time")


def get_revenue_by_zone(limit: int = 10):
    """Return highest-revenue pickup zones up to the requested limit."""
    return _get("/business/revenue-by-zone", params={"limit": limit})


def get_payment_breakdown():
    """Return trip and revenue metrics grouped by payment method."""
    return _get("/business/payment-breakdown")


def get_tip_analysis():
    """Return aggregate recorded credit-card tip metrics."""
    return _get("/business/tip-analysis")


def get_tip_analysis_by_zone(limit: int = 10):
    """Return recorded credit-card tip metrics by pickup zone."""
    return _get("/business/tip-analysis-by-zone", params={"limit": limit})
