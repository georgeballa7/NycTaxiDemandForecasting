from datetime import date
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import FastAPI, HTTPException

from backend.serving.schemas import (
    ZoneResponse,
    MetricResponse,
    FeatureImportanceResponse,
    PredictionResponse,
    FuturePredictionRequest,
    FuturePredictionResponse,
    DemandDateRangeResponse,
    FutureModelMetricResponse,
    DemandByHourResponse,
    DemandByWeekdayResponse,
    DemandOverTimeResponse,
    TopZoneResponse,
    ZoneDemandByHourResponse,
    ZoneDemandByWeekdayResponse,
    ZoneDemandOverTimeResponse,
)

from backend.serving.schemas import (
    BusinessSummaryResponse,
    RevenueOverTimeResponse,
    RevenueByZoneResponse,
    PaymentBreakdownResponse,
    TipAnalysisResponse,
    TipAnalysisByZoneResponse,
)

from backend.src.database.demand_queries_repo import (
    get_demand_date_range as db_get_demand_date_range,
    get_zones as db_get_zones,
    get_demand_by_hour as db_get_demand_by_hour,
    get_demand_by_weekday as db_get_demand_by_weekday,
    get_demand_over_time as db_get_demand_over_time,
    get_top_zones as db_get_top_zones,
    get_zone_demand_by_hour as db_get_zone_demand_by_hour,
    get_zone_demand_by_weekday as db_get_zone_demand_by_weekday,
    get_zone_demand_over_time as db_get_zone_demand_over_time,
)

from backend.src.database.business_queries_repo import (
    get_business_summary,
    get_revenue_over_time,
    get_revenue_by_zone,
    get_payment_breakdown,
    get_tip_analysis,
    get_tip_analysis_by_zone,
)

from backend.src.database.historical_model_repo import (
    get_historical_model_metrics as db_get_historical_model_metrics,
    get_historical_feature_importance as db_get_historical_feature_importance,
    get_historical_predictions as db_get_historical_predictions,
)

from backend.src.database.future_forecast_repo import (
    get_future_forecast_metadata as db_get_future_forecast_metadata,
    get_future_model_metrics as db_get_future_model_metrics,
    get_future_prediction_profile as db_get_future_prediction_profile,
)


app = FastAPI(
    title="NYC Taxi Demand Forecasting API",
    version="1.0.0",
    description=(
        "API for serving NYC taxi demand predictions, "
        "EDA results and model information."
    ),
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get(
    "/data-range",
    response_model=DemandDateRangeResponse,
)
def get_data_range():
    result = db_get_demand_date_range()

    if result["min_date"] is None or result["max_date"] is None:
        raise HTTPException(status_code=404, detail="No demand data available")

    return result


@app.get(
    "/zones",
    response_model=list[ZoneResponse],
)
def get_zones():
    return db_get_zones()


@app.get(
    "/metrics",
    response_model=list[MetricResponse],
)
def get_metrics():
    metrics = db_get_historical_model_metrics()
    if not metrics:
        raise HTTPException(status_code=404, detail="No historical model metrics available")
    return metrics


@app.get(
    "/future-model-metrics",
    response_model=list[FutureModelMetricResponse],
)
def get_future_model_metrics():
    metrics = db_get_future_model_metrics()

    if not metrics:
        raise HTTPException(
            status_code=404,
            detail="No future model metrics available",
        )

    return metrics


@app.get(
    "/feature-importance",
    response_model=list[FeatureImportanceResponse],
)
def get_feature_importance():
    feature_importance = db_get_historical_feature_importance()
    if not feature_importance:
        raise HTTPException(status_code=404, detail="No historical feature importance available")
    return feature_importance


@app.get(
    "/predictions/{location_id}",
    response_model=list[PredictionResponse],
)
def get_predictions(
    location_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    result = db_get_historical_predictions(
        location_id,
        start_date=start_date,
        end_date=end_date,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No predictions found for the selected zone/date range",
        )

    return result


@app.post(
    "/predict",
    response_model=FuturePredictionResponse,
)
def predict_future_demand(
    request: FuturePredictionRequest,
):
    metadata = db_get_future_forecast_metadata()

    if metadata is None:
        raise HTTPException(
            status_code=503,
            detail="Future forecast metadata is not available",
        )

    future_trained_through = pd.Timestamp(
        metadata["trained_through"]
    )
    forecast_datetime = request.forecast_datetime

    nyc_timezone = ZoneInfo("America/New_York")

    if forecast_datetime.tzinfo is not None:
        forecast_datetime = (
            forecast_datetime
            .astimezone(nyc_timezone)
            .replace(tzinfo=None)
        )

    forecast_timestamp = pd.Timestamp(forecast_datetime)

    if forecast_timestamp <= future_trained_through:
        raise HTTPException(
            status_code=400,
            detail=(
                "forecast_datetime must be later than "
                f"{future_trained_through.isoformat()}"
            ),
        )

    day_of_week = ((forecast_datetime.weekday() + 1) % 7) + 1
    hour = forecast_datetime.hour

    profile = db_get_future_prediction_profile(
        request.location_id,
        day_of_week,
        hour,
    )

    if not profile["profile_rows"]:
        raise HTTPException(
            status_code=404,
            detail=(
                "No historical demand profile found "
                f"for LocationID {request.location_id}"
            ),
        )

    if profile["exact_demand"] is not None:
        predicted_demand = float(profile["exact_demand"])
        forecast_method = "zone_dow_hour"
    elif profile["hour_demand"] is not None:
        predicted_demand = float(profile["hour_demand"])
        forecast_method = "zone_hour_fallback"
    else:
        predicted_demand = float(profile["zone_demand"])
        forecast_method = "zone_fallback"

    return {
        "location_id": request.location_id,
        "forecast_datetime": forecast_datetime,
        "predicted_demand": predicted_demand,
        "forecast_method": forecast_method,
        "trained_through": future_trained_through.to_pydatetime(),
    }


@app.get(
    "/eda/demand-by-hour",
    response_model=list[DemandByHourResponse],
)
def get_demand_by_hour():
    return db_get_demand_by_hour()


@app.get(
    "/eda/demand-by-weekday",
    response_model=list[DemandByWeekdayResponse],
)
def get_demand_by_weekday():
    return db_get_demand_by_weekday()


@app.get(
    "/eda/demand-over-time",
    response_model=list[DemandOverTimeResponse],
)
def get_demand_over_time(
    start_date: date | None = None,
    end_date: date | None = None,
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    result = db_get_demand_over_time()

    if start_date is not None:
        result = [row for row in result if row["date"] >= start_date]

    if end_date is not None:
        result = [row for row in result if row["date"] <= end_date]

    return [
        {
            "pickup_hour": row["date"],
            "total_demand": row["total_demand"],
        }
        for row in result
    ]


@app.get(
    "/eda/top-zones",
    response_model=list[TopZoneResponse],
)
def get_top_zones(limit: int = 10):
    if limit < 1 or limit > 265:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 265",
        )

    return db_get_top_zones(limit)


@app.get(
    "/eda/zones/{location_id}/demand-by-hour",
    response_model=list[ZoneDemandByHourResponse],
)
def get_zone_demand_by_hour(
    location_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")

    result = db_get_zone_demand_by_hour(location_id, start_date, end_date)
    if not result:
        raise HTTPException(status_code=404, detail="No demand data found for the selected zone/date range")
    return result


@app.get(
    "/eda/zones/{location_id}/demand-by-weekday",
    response_model=list[ZoneDemandByWeekdayResponse],
)
def get_zone_demand_by_weekday(
    location_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")

    result = db_get_zone_demand_by_weekday(location_id, start_date, end_date)
    if not result:
        raise HTTPException(status_code=404, detail="No demand data found for the selected zone/date range")
    return result


@app.get(
    "/eda/zones/{location_id}/demand-over-time",
    response_model=list[ZoneDemandOverTimeResponse],
)
def get_zone_demand_over_time(
    location_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")

    result = db_get_zone_demand_over_time(location_id, start_date, end_date)
    if not result:
        raise HTTPException(status_code=404, detail="No demand data found for the selected zone/date range")
    return result


@app.get(
    "/business/summary",
    response_model=BusinessSummaryResponse,
)
def business_summary():
    return get_business_summary()


@app.get(
    "/business/revenue-over-time",
    response_model=list[RevenueOverTimeResponse],
)
def revenue_over_time():
    return get_revenue_over_time()


@app.get(
    "/business/revenue-by-zone",
    response_model=list[RevenueByZoneResponse],
)
def revenue_by_zone(limit: int = 10):
    return get_revenue_by_zone(limit=limit)


@app.get(
    "/business/payment-breakdown",
    response_model=list[PaymentBreakdownResponse],
)
def payment_breakdown():
    return get_payment_breakdown()


@app.get(
    "/business/tip-analysis",
    response_model=TipAnalysisResponse,
)
def tip_analysis():
    return get_tip_analysis()


@app.get(
    "/business/tip-analysis-by-zone",
    response_model=list[TipAnalysisByZoneResponse],
)
def tip_analysis_by_zone(limit: int = 10):
    return get_tip_analysis_by_zone(limit=limit)
