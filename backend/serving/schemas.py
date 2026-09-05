from datetime import datetime
from pydantic import BaseModel


class FuturePredictionRequest(BaseModel):
    location_id: int
    forecast_datetime: datetime


class FuturePredictionResponse(BaseModel):
    location_id: int
    forecast_datetime: datetime
    predicted_demand: float
    forecast_method: str
    trained_through: datetime


class ZoneResponse(BaseModel):
    LocationID: int
    Borough: str
    Zone: str
    service_zone: str


class MetricResponse(BaseModel):
    model: str
    mae: float
    rmse: float


class FeatureImportanceResponse(BaseModel):
    feature: str
    importance: float


class PredictionResponse(BaseModel):
    LocationID: int
    Borough: str
    Zone: str
    service_zone: str
    pickup_hour: datetime
    actual_demand: float
    predicted_demand: float



class DemandByHourResponse(BaseModel):
    hour: int
    avg_demand: float
    total_demand: int


class DemandByWeekdayResponse(BaseModel):
    weekday_number: int
    weekday: str
    avg_demand: float
    total_demand: int


class DemandOverTimeResponse(BaseModel):
    pickup_hour: datetime
    total_demand: int


class TopZoneResponse(BaseModel):
    LocationID: int
    Borough: str
    Zone: str
    service_zone: str
    total_demand: int
    avg_hourly_demand: float


from datetime import date


class ZoneDemandByHourResponse(BaseModel):
    LocationID: int
    Borough: str
    Zone: str
    service_zone: str
    hour: int
    avg_demand: float
    total_demand: int


class ZoneDemandByWeekdayResponse(BaseModel):
    LocationID: int
    Borough: str
    Zone: str
    service_zone: str
    weekday_number: int
    weekday: str
    avg_demand: float
    total_demand: int


class ZoneDemandOverTimeResponse(BaseModel):
    LocationID: int
    Borough: str
    Zone: str
    service_zone: str
    date: date
    total_demand: int


class BusinessSummaryResponse(BaseModel):
    total_trips: int
    total_fare_amount: float
    total_amount: float
    total_tip_amount: float
    avg_trip_distance: float


class RevenueOverTimeResponse(BaseModel):
    pickup_date: date
    total_trips: int
    fare_amount: float
    total_amount: float
    tip_amount: float


class RevenueByZoneResponse(BaseModel):
    LocationID: int
    Borough: str
    Zone: str
    service_zone: str
    total_trips: int
    fare_amount: float
    total_amount: float
    avg_fare_per_trip: float


class PaymentBreakdownResponse(BaseModel):
    payment_type: int
    payment_method: str
    total_trips: int
    fare_amount: float
    total_amount: float
    tip_amount: float
    trip_share_pct: float


class TipAnalysisResponse(BaseModel):
    total_tips: float
    avg_tip_per_trip: float
    tip_to_fare_pct: float
    total_credit_card_trips: int


class TipAnalysisByZoneResponse(BaseModel):
    LocationID: int
    Borough: str
    Zone: str
    total_credit_card_trips: int
    total_tips: float
    avg_tip_per_trip: float
    tip_to_fare_pct: float