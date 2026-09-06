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

MODEL_LABELS = {
    "zone_dow_hour_mean": "Zone + weekday + hour baseline",
    "linear_regression": "Linear Regression",
    "random_forest": "Random Forest",
    "gradient_boosted_trees": "Gradient-Boosted Trees",
}


@st.cache_data(ttl=300)
def load_forecast_reference_data():
    return get_zones(), get_future_model_metrics()


try:
    zones, future_metrics = load_forecast_reference_data()
    zones_df = pd.DataFrame(zones)
    metrics_df = pd.DataFrame(future_metrics).sort_values(
        ["mae", "rmse", "model"], ignore_index=True
    )
    production_model = str(metrics_df.iloc[0]["model"])
    backtest_months = int(metrics_df.iloc[0]["backtest_months"])

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
        "Forecast-safe calendar and historical demand patterns are used for long-horizon forecasting. "
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
                **MODEL_LABELS,
                "zone_dow_hour": "Zone + weekday + hour profile",
                "month_hour_fallback": "Zone + month + hour fallback",
                "zone_hour_fallback": "Zone + hour fallback",
                "hour_fallback": "Zone + hour fallback",
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
        "Production forecasting is selected automatically using leakage-safe rolling time-series "
        "backtesting. All candidate models are evaluated on the same holdout months; lowest average "
        "MAE wins, with RMSE used as the tie-breaker."
    )

    winner = metrics_df.iloc[0]
    winner_col, holdout_col = st.columns(2)
    winner_col.metric("Production Model", MODEL_LABELS.get(production_model, production_model))
    holdout_col.metric("Rolling Holdout Months", backtest_months)

    display_metrics = metrics_df.copy()
    display_metrics["Model"] = display_metrics["model"].map(
        lambda model: MODEL_LABELS.get(model, model)
    )
    display_metrics["MAE"] = display_metrics["mae"].round(2)
    display_metrics["RMSE"] = display_metrics["rmse"].round(2)
    display_metrics["Status"] = display_metrics["model"].map(
        lambda model: "Production" if model == production_model else "Candidate"
    )
    st.dataframe(
        display_metrics[["Model", "MAE", "RMSE", "Status"]],
        hide_index=True,
        use_container_width=True,
    )

    st.caption(
        f"Current winner: {MODEL_LABELS.get(production_model, production_model)} "
        f"(MAE {winner['mae']:.2f}, RMSE {winner['rmse']:.2f}) across "
        f"{backtest_months} rolling monthly holdouts. The winner is re-selected after future-model retraining."
    )

except Exception as exc:
    st.error("The Forecast page could not load data from the API.")
    st.exception(exc)
