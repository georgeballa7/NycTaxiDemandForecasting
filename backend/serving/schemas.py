from datetime import datetime
from pydantic import BaseModel


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