from datetime import date, datetime, time

import pandas as pd
import streamlit as st

from frontend.utils.api_client import (
    get_zones,
    predict_future_demand,
)


st.set_page_config(
    page_title="Forecast | NYC Taxi Demand Forecasting and Business Analytics",
    page_icon="🔮",
    layout="wide",
)

st.title("Forecast")
st.write(
    "Forecast hourly NYC Yellow Taxi pickup demand for a selected taxi zone, "
    "date and hour."
)


@st.cache_data(ttl=300)
def load_zones():
    return get_zones()


try:
    zones_df = pd.DataFrame(load_zones())

    # --------------------------------------------------
    # Taxi zone selection
    # --------------------------------------------------

    st.subheader("Taxi Zone")
    borough_col, zone_col = st.columns(2)

    boroughs = sorted(
        zones_df["Borough"].dropna().unique().tolist()
    )

    with borough_col:
        selected_borough = st.selectbox(
            "Borough",
            boroughs,
            index=(
                boroughs.index("Manhattan")
                if "Manhattan" in boroughs
                else 0
            ),
        )

    borough_zones_df = (
        zones_df[
            zones_df["Borough"] == selected_borough
        ]
        .sort_values("Zone")
    )

    zone_names = borough_zones_df["Zone"].dropna().tolist()

    with zone_col:
        selected_zone = st.selectbox(
            "Taxi Zone",
            zone_names,
        )

    selected_zone_row = (
        borough_zones_df[
            borough_zones_df["Zone"] == selected_zone
        ]
        .iloc[0]
    )
    location_id = int(selected_zone_row["LocationID"])

    # --------------------------------------------------
    # Future forecast
    # --------------------------------------------------

    st.subheader("Future Demand Forecast")
    st.caption(
        "Forecast hourly taxi pickups using historical demand patterns for "
        "the selected zone, weekday and hour. Times are interpreted in "
        "New York local time."
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

    forecast_datetime = datetime.combine(
        forecast_date,
        time(hour=forecast_hour),
    )

    if st.button(
        "Forecast Demand",
        type="primary",
    ):
        try:
            result = predict_future_demand(
                location_id=location_id,
                forecast_datetime=forecast_datetime,
            )

            predicted_pickups = round(result["predicted_demand"])

            result_col1, result_col2 = st.columns(2)

            with result_col1:
                st.metric(
                    "Predicted Taxi Pickups",
                    f"{predicted_pickups:,}",
                )

            with result_col2:
                st.metric(
                    "Forecast Hour",
                    f"{forecast_datetime:%H:%M}",
                )

            method_labels = {
                "zone_dow_hour": "Zone + weekday + hour profile",
                "zone_hour_fallback": "Zone + hour fallback",
                "zone_fallback": "Zone average fallback",
            }

            trained_through = pd.to_datetime(
                result["trained_through"]
            ).strftime("%d %b %Y %H:%M")

            st.info(
                f"**{selected_zone}, {selected_borough}:** Forecast demand "
                f"is **{predicted_pickups:,} pickups** for "
                f"**{forecast_datetime:%d %b %Y %H:%M}**. "
                f"Forecast method: **{method_labels.get(result['forecast_method'], result['forecast_method'])}**. "
                f"Historical demand data are available through "
                f"**{trained_through}**."
            )

        except Exception as exc:
            st.error(
                "The forecast could not be generated. Choose a time later "
                "than the latest observed demand data and try again."
            )
            st.exception(exc)

    # --------------------------------------------------
    # Model validation
    # --------------------------------------------------

    st.divider()
    st.subheader("Model Validation")
    st.write(
        "The production forecast method was selected using leakage-safe "
        "rolling time-series backtesting on unseen future months. A simple "
        "historical zone-weekday-hour demand profile consistently "
        "outperformed the Random Forest for this long-horizon forecasting "
        "task."
    )

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric("Profile MAE", "6.40")

    with metric_col2:
        st.metric("Profile RMSE", "16.04")

    with metric_col3:
        st.metric("Random Forest MAE", "7.32")

    with metric_col4:
        st.metric("Random Forest RMSE", "19.74")

    st.caption(
        "Validation covers four rolling monthly holdouts from February "
        "through May 2026. Lower MAE and RMSE indicate better forecast "
        "accuracy. The Random Forest was evaluated as an alternative model, "
        "but the historical profile achieved lower errors across the rolling "
        "holdout periods and was therefore selected for production forecasting."
    )

except Exception as exc:
    st.error(
        "The Forecast page could not load data from the API."
    )
    st.exception(exc)
