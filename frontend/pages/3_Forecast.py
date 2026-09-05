from datetime import date, datetime, time

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.utils.api_client import (
    get_predictions,
    get_zones,
    predict_future_demand,
)

from frontend.utils.theme import (
    CHECKER_BLACK,
    TAXI_YELLOW,
    apply_taxi_plotly_theme,
)


st.set_page_config(
    page_title="Forecast | NYC Taxi Demand Forecasting and Business Analytics",
    page_icon="🔮",
    layout="wide",
)

st.title("Taxi Demand Forecast")
st.write(
    "Forecast future taxi demand for a selected NYC taxi zone and review "
    "historical model performance on the June 2025 holdout period."
)


@st.cache_data(ttl=300)
def load_zones():
    return get_zones()


@st.cache_data(ttl=300)
def load_predictions(location_id, start_date, end_date):
    return get_predictions(
        location_id,
        start_date=start_date,
        end_date=end_date,
    )


try:
    zones_df = pd.DataFrame(load_zones())

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

    future_tab, evaluation_tab = st.tabs(
        [
            "Future Demand Forecast",
            "Historical Model Evaluation",
        ]
    )

    with future_tab:
        st.subheader("Future Demand Forecast")
        st.caption(
            "Forecast hourly taxi pickups using historical demand patterns "
            "for the selected zone, weekday and hour. Times are interpreted "
            "in New York local time."
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

                st.metric(
                    "Predicted Taxi Pickups",
                    f"{result['predicted_demand']:.1f}",
                )

                method_labels = {
                    "zone_dow_hour": "Zone + weekday + hour profile",
                    "zone_hour_fallback": "Zone + hour fallback",
                    "zone_fallback": "Zone average fallback",
                }

                st.caption(
                    "Forecast method: "
                    + method_labels.get(
                        result["forecast_method"],
                        result["forecast_method"],
                    )
                )

                trained_through = pd.to_datetime(
                    result["trained_through"]
                ).strftime("%d %b %Y %H:%M")

                st.info(
                    f"**{selected_zone}, {selected_borough}:** "
                    f"Forecast demand is **{result['predicted_demand']:.1f} "
                    f"pickups** for **{forecast_datetime:%d %b %Y %H:%M}**. "
                    f"Historical demand data are available through "
                    f"**{trained_through}**."
                )

            except Exception as exc:
                st.error(
                    "The future forecast could not be generated. "
                    "Choose a time later than the latest observed data."
                )
                st.exception(exc)

    with evaluation_tab:
        st.subheader("Historical Model Evaluation")
        st.caption(
            "Compare actual and Random Forest predicted hourly taxi demand "
            "during the June 2025 holdout period."
        )

        date_col1, date_col2 = st.columns(2)

        with date_col1:
            start_date = st.date_input(
                "Start Date",
                value=date(2025, 6, 1),
                min_value=date(2025, 6, 1),
                max_value=date(2025, 6, 30),
                key="evaluation_start_date",
            )

        with date_col2:
            end_date = st.date_input(
                "End Date",
                value=date(2025, 6, 30),
                min_value=date(2025, 6, 1),
                max_value=date(2025, 6, 30),
                key="evaluation_end_date",
            )

        if start_date > end_date:
            st.warning(
                "Start date must be before or equal to end date."
            )
            st.stop()

        predictions_df = pd.DataFrame(
            load_predictions(
                location_id,
                start_date,
                end_date,
            )
        )

        predictions_df["pickup_hour"] = pd.to_datetime(
            predictions_df["pickup_hour"]
        )
        predictions_df = predictions_df.sort_values("pickup_hour")

        predictions_df["error"] = (
            predictions_df["actual_demand"]
            - predictions_df["predicted_demand"]
        )
        predictions_df["absolute_error"] = (
            predictions_df["error"].abs()
        )
        predictions_df["squared_error"] = (
            predictions_df["error"] ** 2
        )

        actual_avg = predictions_df["actual_demand"].mean()
        predicted_avg = predictions_df["predicted_demand"].mean()
        zone_mae = predictions_df["absolute_error"].mean()
        zone_rmse = np.sqrt(
            predictions_df["squared_error"].mean()
        )

        st.subheader(f"{selected_zone}, {selected_borough}")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

        with kpi1:
            st.metric("Actual Avg. Demand", f"{actual_avg:.1f}")
        with kpi2:
            st.metric("Predicted Avg. Demand", f"{predicted_avg:.1f}")
        with kpi3:
            st.metric("Zone MAE", f"{zone_mae:.2f}")
        with kpi4:
            st.metric("Zone RMSE", f"{zone_rmse:.2f}")

        st.subheader("Actual vs. Predicted Demand")

        forecast_df = predictions_df[
            ["pickup_hour", "actual_demand", "predicted_demand"]
        ].melt(
            id_vars="pickup_hour",
            value_vars=["actual_demand", "predicted_demand"],
            var_name="series",
            value_name="demand",
        )
        forecast_df["series"] = forecast_df["series"].replace(
            {
                "actual_demand": "Actual",
                "predicted_demand": "Predicted",
            }
        )

        forecast_fig = px.line(
            forecast_df,
            x="pickup_hour",
            y="demand",
            color="series",
            labels={
                "pickup_hour": "Date",
                "demand": "Taxi Pickups",
                "series": "",
            },
        )
        forecast_fig.update_layout(
            xaxis_title=None,
            yaxis_title="Taxi Pickups",
            hovermode="x unified",
            legend_title=None,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        forecast_fig = apply_taxi_plotly_theme(forecast_fig)

        for trace in forecast_fig.data:
            if trace.name == "Actual":
                trace.line.color = CHECKER_BLACK
            elif trace.name == "Predicted":
                trace.line.color = TAXI_YELLOW

        st.plotly_chart(forecast_fig, width="stretch")

        st.subheader("Prediction Error over Time")

        error_fig = px.bar(
            predictions_df,
            x="pickup_hour",
            y="error",
            labels={
                "pickup_hour": "Date",
                "error": "Prediction Error",
            },
        )
        error_fig.update_layout(
            xaxis_title=None,
            yaxis_title="Actual - Predicted",
            margin=dict(l=20, r=20, t=20, b=20),
        )
        error_fig = apply_taxi_plotly_theme(error_fig)
        st.plotly_chart(error_fig, width="stretch")

        st.subheader("Forecast Insights")

        largest_error_row = predictions_df.loc[
            predictions_df["absolute_error"].idxmax()
        ]
        largest_error = float(
            largest_error_row["absolute_error"]
        )
        largest_error_time = largest_error_row[
            "pickup_hour"
        ].strftime("%d %b %Y %H:%M")
        mean_bias = predictions_df["error"].mean()

        if mean_bias > 0:
            bias_description = "underpredict"
        elif mean_bias < 0:
            bias_description = "overpredict"
        else:
            bias_description = "show no average bias"

        insight1, insight2, insight3 = st.columns(3)
        with insight1:
            st.metric(
                "Largest Absolute Error",
                f"{largest_error:.1f}",
            )
        with insight2:
            st.metric("Mean Forecast Bias", f"{mean_bias:.2f}")
        with insight3:
            st.metric("Observations", f"{len(predictions_df):,}")

        st.info(
            f"**{selected_zone}, {selected_borough}:** "
            f"The model achieves an MAE of **{zone_mae:.2f}** and an "
            f"RMSE of **{zone_rmse:.2f}** for the selected period. "
            f"The largest prediction error of **{largest_error:.1f} "
            f"pickups** occurred at **{largest_error_time}**. On average, "
            f"the model tends to **{bias_description}** demand for this zone."
        )

        st.subheader("Error Analysis")

        low_threshold = predictions_df["actual_demand"].quantile(0.33)
        high_threshold = predictions_df["actual_demand"].quantile(0.67)

        predictions_df["demand_level"] = pd.cut(
            predictions_df["actual_demand"],
            bins=[
                -float("inf"),
                low_threshold,
                high_threshold,
                float("inf"),
            ],
            labels=["Low Demand", "Medium Demand", "High Demand"],
            include_lowest=True,
        )

        error_by_demand = (
            predictions_df
            .groupby("demand_level", observed=True)
            .agg(
                observations=("absolute_error", "size"),
                mae=("absolute_error", "mean"),
                mean_error=("error", "mean"),
                avg_actual_demand=("actual_demand", "mean"),
            )
            .reset_index()
        )

        error_level_fig = px.bar(
            error_by_demand,
            x="demand_level",
            y="mae",
            labels={
                "demand_level": "Demand Level",
                "mae": "Mean Absolute Error",
            },
            title="Forecast Error by Demand Level",
            category_orders={
                "demand_level": [
                    "Low Demand",
                    "Medium Demand",
                    "High Demand",
                ]
            },
        )
        error_level_fig.update_layout(
            xaxis_title=None,
            yaxis_title="MAE",
            showlegend=False,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        error_level_fig = apply_taxi_plotly_theme(error_level_fig)
        st.plotly_chart(error_level_fig, width="stretch")

        high_demand_stats = error_by_demand[
            error_by_demand["demand_level"] == "High Demand"
        ].iloc[0]
        high_demand_mae = float(high_demand_stats["mae"])
        high_demand_bias = float(high_demand_stats["mean_error"])
        high_demand_avg = float(
            high_demand_stats["avg_actual_demand"]
        )
        high_vs_overall_error = (
            (high_demand_mae / zone_mae) - 1
        ) * 100

        error_col1, error_col2, error_col3 = st.columns(3)
        with error_col1:
            st.metric("High-Demand MAE", f"{high_demand_mae:.2f}")
        with error_col2:
            st.metric("High-Demand Avg.", f"{high_demand_avg:.1f}")
        with error_col3:
            st.metric(
                "High vs. Overall Error",
                f"{high_vs_overall_error:+.1f}%",
            )

        if high_demand_bias > 0:
            high_demand_bias_text = (
                "tends to underestimate demand during high-demand hours"
            )
        elif high_demand_bias < 0:
            high_demand_bias_text = (
                "tends to overestimate demand during high-demand hours"
            )
        else:
            high_demand_bias_text = (
                "shows no average bias during high-demand hours"
            )

        if high_vs_overall_error > 10:
            error_comparison_text = (
                "Forecast errors increase noticeably when demand is high."
            )
        elif high_vs_overall_error < -10:
            error_comparison_text = (
                "The model performs particularly well during high-demand "
                "periods."
            )
        else:
            error_comparison_text = (
                "Forecast accuracy remains relatively stable across demand "
                "levels."
            )

        st.info(
            f"During high-demand periods, actual demand averages "
            f"**{high_demand_avg:.1f} pickups per hour**, while the model's "
            f"MAE is **{high_demand_mae:.2f}**. This is "
            f"**{abs(high_vs_overall_error):.1f}% "
            f"{'higher' if high_vs_overall_error >= 0 else 'lower'}** than "
            f"the overall MAE for the selected period. The model "
            f"**{high_demand_bias_text}**. {error_comparison_text}"
        )

except Exception as exc:
    st.error(
        "The Forecast page could not load data from the API."
    )
    st.exception(exc)
