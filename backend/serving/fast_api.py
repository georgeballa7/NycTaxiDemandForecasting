from datetime import date
import json
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import FastAPI, HTTPException

from backend.src.config.settings import APP_DATA_DIR

from backend.serving.schemas import (
    ZoneResponse,
    MetricResponse,
    FeatureImportanceResponse,
    PredictionResponse,
    FuturePredictionRequest,
    FuturePredictionResponse,
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


app = FastAPI(
    title="NYC Taxi Demand Forecasting API",
    version="1.0.0",
    description=(
        "API for serving NYC taxi demand predictions, "
        "EDA results and model information."
    ),
)



# --------------------------------------------------
# Load app-ready datasets
# --------------------------------------------------

predictions_df = pd.read_parquet(
    APP_DATA_DIR / "predictions.parquet"
)

metrics_df = pd.read_csv(
    APP_DATA_DIR / "model_metrics.csv"
)

feature_importance_df = pd.read_csv(
    APP_DATA_DIR / "feature_importance.csv"
)

future_forecast_dir = (
    APP_DATA_DIR / "future_forecast"
)

future_profiles_df = pd.read_parquet(
    future_forecast_dir
    / "future_demand_profiles.parquet"
)

with open(
    future_forecast_dir / "metadata.json",
    encoding="utf-8",
) as file:
    future_forecast_metadata = json.load(file)

future_trained_through = pd.Timestamp(
    future_forecast_metadata["trained_through"]
)


# --------------------------------------------------
# Date / time conversions
# --------------------------------------------------

predictions_df["pickup_hour"] = pd.to_datetime(
    predictions_df["pickup_hour"]
)

# --------------------------------------------------
# Health
# --------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------
# Zones
# --------------------------------------------------

@app.get(
    "/zones",
    response_model=list[ZoneResponse],
)
def get_zones():
    return db_get_zones()


# --------------------------------------------------
# Model metrics
# --------------------------------------------------

@app.get(
    "/metrics",
    response_model=list[MetricResponse],
)
def get_metrics():
    return metrics_df.to_dict(orient="records")


# --------------------------------------------------
# Feature importance
# --------------------------------------------------

@app.get(
    "/feature-importance",
    response_model=list[FeatureImportanceResponse],
)
def get_feature_importance():
    return feature_importance_df.to_dict(
        orient="records"
    )


# --------------------------------------------------
# Predictions
# --------------------------------------------------

@app.get(
    "/predictions/{location_id}",
    response_model=list[PredictionResponse],
)
def get_predictions(
    location_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
):
    result = predictions_df[
        predictions_df["LocationID"] == location_id
    ].copy()

    if result.empty:
        raise HTTPException(
            status_code=404,
            detail=f"LocationID {location_id} not found",
        )

    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    if start_date is not None:
        result = result[
            result["pickup_hour"].dt.date >= start_date
        ]

    if end_date is not None:
        result = result[
            result["pickup_hour"].dt.date <= end_date
        ]

    if result.empty:
        raise HTTPException(
            status_code=404,
            detail="No predictions found for the selected date range",
        )

    return result.to_dict(orient="records")


@app.post(
    "/predict",
    response_model=FuturePredictionResponse,
)
def predict_future_demand(
    request: FuturePredictionRequest,
):
    forecast_datetime = request.forecast_datetime

    nyc_timezone = ZoneInfo("America/New_York")

    if forecast_datetime.tzinfo is not None:
        forecast_datetime = (
            forecast_datetime
            .astimezone(nyc_timezone)
            .replace(tzinfo=None)
        )

    forecast_timestamp = pd.Timestamp(
        forecast_datetime
    )

    if forecast_timestamp <= future_trained_through:
        raise HTTPException(
            status_code=400,
            detail=(
                "forecast_datetime must be later than "
                f"{future_trained_through.isoformat()}"
            ),
        )

    # Match Spark dayofweek:
    # Sunday=1, Monday=2, ..., Saturday=7
    day_of_week = (
        (forecast_datetime.weekday() + 1) % 7
    ) + 1

    hour = forecast_datetime.hour

    zone_profiles = future_profiles_df[
        future_profiles_df["LocationID"]
        == request.location_id
    ]

    if zone_profiles.empty:
        raise HTTPException(
            status_code=404,
            detail=(
                "No historical demand profile found "
                f"for LocationID {request.location_id}"
            ),
        )

    exact_profile = zone_profiles[
        (
            zone_profiles["day_of_week"]
            == day_of_week
        )
        & (
            zone_profiles["hour"]
            == hour
        )
    ]

    if not exact_profile.empty:
        predicted_demand = float(
            exact_profile.iloc[0][
                "predicted_demand"
            ]
        )
        forecast_method = "zone_dow_hour"

    else:
        zone_hour_profiles = zone_profiles[
            zone_profiles["hour"] == hour
        ]

        if not zone_hour_profiles.empty:
            predicted_demand = float(
                zone_hour_profiles[
                    "predicted_demand"
                ].mean()
            )
            forecast_method = (
                "zone_hour_fallback"
            )

        else:
            predicted_demand = float(
                zone_profiles[
                    "predicted_demand"
                ].mean()
            )
            forecast_method = "zone_fallback"

    return {
        "location_id": request.location_id,
        "forecast_datetime": forecast_datetime,
        "predicted_demand": predicted_demand,
        "forecast_method": forecast_method,
        "trained_through": (
            future_trained_through
            .to_pydatetime()
        ),
    }


# --------------------------------------------------
# NYC-wide EDA (PostgreSQL)
# --------------------------------------------------

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
    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    result = db_get_demand_over_time()

    if start_date is not None:
        result = [
            row for row in result
            if row["date"] >= start_date
        ]

    if end_date is not None:
        result = [
            row for row in result
            if row["date"] <= end_date
        ]

    # Preserve the existing API contract used by api_client.py/Streamlit.
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


# --------------------------------------------------
# Zone-specific EDA (PostgreSQL)
# --------------------------------------------------

@app.get(
    "/eda/zones/{location_id}/demand-by-hour",
    response_model=list[ZoneDemandByHourResponse],
)
def get_zone_demand_by_hour(
    location_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
):
    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    result = db_get_zone_demand_by_hour(
        location_id,
        start_date,
        end_date,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No demand data found for the selected zone/date range",
        )

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
    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    result = db_get_zone_demand_by_weekday(
        location_id,
        start_date,
        end_date,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No demand data found for the selected zone/date range",
        )

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
    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    result = db_get_zone_demand_over_time(
        location_id,
        start_date,
        end_date,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No demand data found for the selected zone/date range",
        )

    return result



# --------------------------------------------------
# Business Insights
# --------------------------------------------------


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