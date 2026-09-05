import requests

from frontend.config.settings import (
    API_BASE_URL,
    API_TIMEOUT,
)


def _get(endpoint, params=None):
    response = requests.get(
        f"{API_BASE_URL}{endpoint}",
        params=params,
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _post(endpoint, payload):
    response = requests.post(
        f"{API_BASE_URL}{endpoint}",
        json=payload,
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_health():
    return _get("/health")


def get_demand_date_range():
    return _get("/data-range")


def get_zones():
    return _get("/zones")


def get_metrics():
    return _get("/metrics")


def get_feature_importance():
    return _get("/feature-importance")


def predict_future_demand(
    location_id: int,
    forecast_datetime,
):
    return _post(
        "/predict",
        {
            "location_id": location_id,
            "forecast_datetime": (
                forecast_datetime.isoformat()
            ),
        },
    )


def get_demand_by_hour():
    return _get("/eda/demand-by-hour")


def get_demand_by_weekday():
    return _get("/eda/demand-by-weekday")


def get_demand_over_time(
    start_date=None,
    end_date=None,
):
    params = {}

    if start_date is not None:
        params["start_date"] = str(start_date)

    if end_date is not None:
        params["end_date"] = str(end_date)

    return _get(
        "/eda/demand-over-time",
        params=params,
    )


def get_top_zones(limit: int = 10):
    return _get(
        "/eda/top-zones",
        params={"limit": limit},
    )


def get_predictions(
    location_id: int,
    start_date=None,
    end_date=None,
):
    params = {}

    if start_date is not None:
        params["start_date"] = str(start_date)

    if end_date is not None:
        params["end_date"] = str(end_date)

    return _get(
        f"/predictions/{location_id}",
        params=params,
    )


def get_zone_demand_by_hour(
    location_id: int,
    start_date=None,
    end_date=None,
):
    params = {}

    if start_date is not None:
        params["start_date"] = str(start_date)

    if end_date is not None:
        params["end_date"] = str(end_date)

    return _get(
        f"/eda/zones/{location_id}/demand-by-hour",
        params=params,
    )


def get_zone_demand_by_weekday(
    location_id: int,
    start_date=None,
    end_date=None,
):
    params = {}

    if start_date is not None:
        params["start_date"] = str(start_date)

    if end_date is not None:
        params["end_date"] = str(end_date)

    return _get(
        f"/eda/zones/{location_id}/demand-by-weekday",
        params=params,
    )


def get_zone_demand_over_time(
    location_id: int,
    start_date=None,
    end_date=None,
):
    params = {}

    if start_date is not None:
        params["start_date"] = str(start_date)

    if end_date is not None:
        params["end_date"] = str(end_date)

    return _get(
        f"/eda/zones/{location_id}/demand-over-time",
        params=params,
    )


def get_business_summary():
    return _get("/business/summary")


def get_revenue_over_time():
    return _get("/business/revenue-over-time")


def get_revenue_by_zone(limit: int = 10):
    return _get(
        "/business/revenue-by-zone",
        params={"limit": limit},
    )


def get_payment_breakdown():
    return _get("/business/payment-breakdown")


def get_tip_analysis():
    return _get("/business/tip-analysis")


def get_tip_analysis_by_zone(limit: int = 10):
    return _get(
        "/business/tip-analysis-by-zone",
        params={"limit": limit,
        },
    )
