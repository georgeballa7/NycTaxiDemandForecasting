from datetime import date, datetime, time

import pandas as pd
import streamlit as st

from frontend.utils.api_client import (
    get_future_model_metrics,
    get_zones,
    predict_future_demand,
)
from frontend.utils.theme import page_accent


st.set_page_config(
    page_title="Forecast | NYC Taxi Demand Forecasting and Business Analytics",
    page_icon="🔮",
    layout="wide",
)

st.title("Forecast")
page_accent()
st.write(
    "Forecast hourly NYC Yellow Taxi pickup demand for a selected taxi zone, date and hour."
)


@st.cache_data(ttl=300)
def load_forecast_reference_data():
    return get_zones(), get_future_model_metrics()


try:
    zones, future_metrics = load_forecast_reference_data()
    zones_df = pd.DataFrame(zones)
    metrics_by_model = {item["model"]: item for item in future_metrics}

    profile_metrics = metrics_by_model["zone_dow_hour_mean"]
    rf_metrics = metrics_by_model["random_forest"]
    backtest_months = int(profile_metrics["backtest_months"])

    st.subheader("Taxi Zone")
    borough_col, zone_col = st.columns(2)

    boroughs = sorted(zones_df["Borough"].dropna().unique().tolist())
    with borough_col:
        selected_borough = st.selectbox(
            "Borough",
            boroughs,
            index=boroughs.index("Manhattan") if "Manhattan" in boroughs else 0,
        )

    borough_zones_df = zones_df[zones_df["Borough"] == selected_borough].sort_values("Zone")
    zone_names = borough_zones_df["Zone"].dropna().tolist()

    with zone_col:
        selected_zone = st.selectbox("Taxi Zone", zone_names)

    selected_zone_row = borough_zones_df[borough_zones_df["Zone"] == selected_zone].iloc[0]
    location_id = int(selected_zone_row["LocationID"])

    st.divider()
    st.subheader("Future Demand Forecast")
    st.caption(
        "Historical zone, weekday and hour patterns are used for long-horizon forecasting. "
        "Times are interpreted in New York local time."
    )

    future_date_col, future_hour_col = st.columns(2)
    with future_date_col:
        forecast_date = st.date_input(
            "Forecast Date",
            value=date.today(),
            key="future_forecast_date",
        )
    with future_hour_col:
        forecast_hour = st.selectbox(
            "Forecast Hour",
            options=list(range(24)),
            format_func=lambda hour: f"{hour:02d}:00",
            key="future_forecast_hour",
        )

    forecast_datetime = datetime.combine(forecast_date, time(hour=forecast_hour))

    if st.button("Forecast Demand", type="primary"):
        try:
            result = predict_future_demand(
                location_id=location_id,
                forecast_datetime=forecast_datetime,
            )
            predicted_pickups = round(result["predicted_demand"])

            result_col1, result_col2 = st.columns(2)
            result_col1.metric("Predicted Taxi Pickups", f"{predicted_pickups:,}")
            result_col2.metric("Forecast Hour", f"{forecast_datetime:%H:%M}")

            method_labels = {
                "zone_dow_hour": "Zone + weekday + hour profile",
                "zone_hour_fallback": "Zone + hour fallback",
                "zone_fallback": "Zone average fallback",
            }
            trained_through = pd.to_datetime(result["trained_through"]).strftime("%d %b %Y %H:%M")

            st.success(
                f"**{selected_zone}, {selected_borough}: {predicted_pickups:,} expected pickups** "
                f"for **{forecast_datetime:%d %b %Y %H:%M}**."
            )
            st.caption(
                f"Method: {method_labels.get(result['forecast_method'], result['forecast_method'])} · "
                f"Historical demand available through {trained_through}."
            )
        except Exception as exc:
            st.error(
                "The forecast could not be generated. Choose a time later than the latest observed demand data and try again."
            )
            st.exception(exc)

    st.divider()
    st.subheader("Model Validation")
    st.write(
        "The production method was selected using leakage-safe rolling time-series backtesting. "
        "For long-horizon forecasting, the historical zone-weekday-hour profile outperformed "
        "the Random Forest across the evaluated holdouts."
    )

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Profile MAE", f"{profile_metrics['mae']:.2f}")
    metric_col2.metric("Profile RMSE", f"{profile_metrics['rmse']:.2f}")
    metric_col3.metric("Random Forest MAE", f"{rf_metrics['mae']:.2f}")
    metric_col4.metric("Random Forest RMSE", f"{rf_metrics['rmse']:.2f}")

    st.caption(
        f"Validation currently summarizes {backtest_months} rolling monthly holdouts. "
        "Lower MAE and RMSE indicate better forecast accuracy. The model with the stronger "
        "rolling holdout performance is selected for production forecasting."
    )

except Exception as exc:
    st.error("The Forecast page could not load data from the API.")
    st.exception(exc)
