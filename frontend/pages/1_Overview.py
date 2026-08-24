import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.utils.api_client import (
    get_demand_over_time,
    get_metrics,
    get_top_zones,
    get_zones,
)


st.set_page_config(
    page_title="Overview | NYC Taxi Demand Forecasting",
    page_icon="🚕",
    layout="wide",
)


st.title("NYC Taxi Demand Forecasting")

st.write(
    "Explore NYC taxi demand patterns and the performance "
    "of the demand forecasting model."
)


@st.cache_data(ttl=300)
def load_overview_data():
    zones = get_zones()
    metrics = get_metrics()
    top_zones = get_top_zones(limit=10)
    demand_over_time = get_demand_over_time()

    return zones, metrics, top_zones, demand_over_time


try:
    zones, metrics, top_zones, demand_over_time = load_overview_data()

    # -----------------------------------
    # Model metrics
    # -----------------------------------

    random_forest = next(
        item
        for item in metrics
        if item["model"] == "Random Forest"
    )

    top_zone = top_zones[0]

    # -----------------------------------
    # KPI Cards
    # -----------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Taxi Zones",
            value=len(zones),
        )

    with col2:
        st.metric(
            label="Random Forest MAE",
            value=f"{random_forest['mae']:.2f}",
        )

    with col3:
        st.metric(
            label="Random Forest RMSE",
            value=f"{random_forest['rmse']:.2f}",
        )

    with col4:
        st.metric(
            label="Highest-Demand Zone",
            value=top_zone["Zone"],
        )

    # -----------------------------------
    # Taxi Demand over Time
    # -----------------------------------

    st.subheader("Taxi Demand over Time")

    demand_df = pd.DataFrame(demand_over_time)

    demand_df["pickup_hour"] = pd.to_datetime(
        demand_df["pickup_hour"]
    )

    daily_demand_df = (
        demand_df
        .set_index("pickup_hour")
        .resample("D")["total_demand"]
        .sum()
        .reset_index()
    )

    fig = px.line(
        daily_demand_df,
        x="pickup_hour",
        y="total_demand",
        labels={
            "pickup_hour": "Date",
            "total_demand": "Taxi Pickups",
        },
    )

    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Taxi Pickups",
        hovermode="x unified",
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )



    st.subheader("Top Taxi Zones by Demand")

    top_zones_df = pd.DataFrame(top_zones)

    top_zones_fig = px.bar(
        top_zones_df.sort_values(
            "total_demand",
            ascending=True,
        ),
        x="total_demand",
        y="Zone",
        orientation="h",
        hover_data={
            "Borough": True,
            "avg_hourly_demand": ":.1f",
            "total_demand": ":,",
        },
        labels={
            "total_demand": "Total Pickups",
            "Zone": "Taxi Zone",
            "avg_hourly_demand": "Avg. Hourly Demand",
        },
    )

    top_zones_fig.update_layout(
        xaxis_title="Total Pickups",
        yaxis_title=None,
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),
    )

    st.plotly_chart(
        top_zones_fig,
        use_container_width=True,
    )


    metrics_df = pd.DataFrame(metrics)

    st.subheader("Model Performance")

    metrics_df = pd.DataFrame(metrics)

    mae_col, rmse_col = st.columns(2)

    with mae_col:
        mae_fig = px.bar(
            metrics_df,
            x="model",
            y="mae",
            text="mae",
            labels={
                "model": "Model",
                "mae": "MAE",
            },
            title="Mean Absolute Error",
        )

        mae_fig.update_traces(
            texttemplate="%{text:.2f}",
            textposition="outside",
        )

        mae_fig.update_layout(
            xaxis_title=None,
            yaxis_title="MAE",
            showlegend=False,
            margin=dict(
                l=20,
                r=20,
                t=50,
                b=20,
            ),
        )

        st.plotly_chart(
            mae_fig,
            use_container_width=True,
        )


    with rmse_col:
        rmse_fig = px.bar(
            metrics_df,
            x="model",
            y="rmse",
            text="rmse",
            labels={
                "model": "Model",
                "rmse": "RMSE",
            },
            title="Root Mean Squared Error",
        )

        rmse_fig.update_traces(
            texttemplate="%{text:.2f}",
            textposition="outside",
        )

        rmse_fig.update_layout(
            xaxis_title=None,
            yaxis_title="RMSE",
            showlegend=False,
            margin=dict(
                l=20,
                r=20,
                t=50,
                b=20,
            ),
        )

        st.plotly_chart(
            rmse_fig,
            use_container_width=True,
        )
        
except Exception as exc:
    st.error(
        "The dashboard could not load data from the API."
    )

    st.exception(exc)