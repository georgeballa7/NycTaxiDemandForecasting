import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.utils.api_client import (
    get_business_summary,
    get_payment_breakdown,
    get_revenue_by_zone,
    get_revenue_over_time,
    get_tip_analysis,
    get_tip_analysis_by_zone,
)

from frontend.utils.theme import (
    CHECKER_BLACK,
    TAXI_YELLOW,
    apply_taxi_plotly_theme,
)


st.set_page_config(
    page_title="Business Insights | NYC Taxi Demand Forecasting and Business Analytics",
    page_icon="💼",
    layout="wide",
)

st.title("💼 Business Insights")
st.caption(
    "Revenue, payment behavior and recorded credit-card "
    "tip patterns across NYC Yellow Taxi trips."
)


@st.cache_data(ttl=300)
def load_business_data():
    return (
        get_business_summary(),
        get_revenue_over_time(),
        get_revenue_by_zone(limit=10),
        get_payment_breakdown(),
        get_tip_analysis(),
        get_tip_analysis_by_zone(limit=10),
    )


try:
    (
        summary,
        revenue_time,
        revenue_zones,
        payments,
        tips,
        tip_zones,
    ) = load_business_data()

except Exception as exc:
    st.error("The dashboard could not load business data from the API.")
    st.exception(exc)
    st.stop()


# --------------------------------------------------
# Business KPIs
# --------------------------------------------------

st.subheader("Business Performance")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Total Trips",
    f"{summary['total_trips']:,}",
)

col2.metric(
    "Fare Revenue",
    f"${summary['total_fare_amount'] / 1_000_000:.1f}M",
)

col3.metric(
    "Total Collected Amount",
    f"${summary['total_amount'] / 1_000_000:.1f}M",
)

col4.metric(
    "Recorded Tips",
    f"${summary['total_tip_amount'] / 1_000_000:.1f}M",
)

col5.metric(
    "Avg Trip Distance",
    f"{summary['avg_trip_distance']:.2f} mi",
)


# --------------------------------------------------
# Revenue over time
# --------------------------------------------------

st.divider()
st.subheader("Revenue Over Time")

revenue_df = pd.DataFrame(revenue_time)

revenue_df["pickup_date"] = pd.to_datetime(
    revenue_df["pickup_date"]
)

fig_revenue = px.line(
    revenue_df,
    x="pickup_date",
    y="fare_amount",
    labels={
        "pickup_date": "Date",
        "fare_amount": "Fare Revenue ($)",
    },
)

fig_revenue.update_layout(
    xaxis_title=None,
    yaxis_title="Fare Revenue ($)",
)

fig_revenue = apply_taxi_plotly_theme(
    fig_revenue
)

st.plotly_chart(
    fig_revenue,
    width="stretch",
)


# --------------------------------------------------
# Revenue by zone
# --------------------------------------------------

st.divider()
st.subheader("Top Pickup Zones by Fare Revenue")

zones_df = pd.DataFrame(revenue_zones)

fig_zones = px.bar(
    zones_df.sort_values("fare_amount"),
    x="fare_amount",
    y="Zone",
    orientation="h",
    hover_data=[
        "Borough",
        "total_trips",
        "avg_fare_per_trip",
    ],
    labels={
        "fare_amount": "Fare Revenue ($)",
        "Zone": "Pickup Zone",
    },
)

fig_zones = apply_taxi_plotly_theme(
    fig_zones
)

st.plotly_chart(
    fig_zones,
    width="stretch",
)


# --------------------------------------------------
# Payment behavior
# --------------------------------------------------

st.divider()
st.subheader("Payment Mix")

payments_df = pd.DataFrame(payments)

col1, col2 = st.columns(2)

with col1:
    fig_payment = px.pie(
        payments_df,
        names="payment_method",
        values="total_trips",
        hole=0.45,
    )

    fig_payment.update_traces(
        textinfo="none",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Trips: %{value:,}<br>"
            "Share: %{percent:.2%}"
            "<extra></extra>"
        ),
    )

    fig_payment = apply_taxi_plotly_theme(
        fig_payment
    )

    payment_colors = [
        TAXI_YELLOW,
        CHECKER_BLACK,
        "#D89E00",
        "#8C7A3B",
        "#6B7280",
    ]

    for trace in fig_payment.data:
        trace.marker.colors = payment_colors[
            : len(payments_df)
        ]

    st.plotly_chart(
        fig_payment,
        width="stretch",
    )

with col2:
    payment_display = payments_df[
        [
            "payment_method",
            "total_trips",
            "trip_share_pct",
        ]
    ].copy()

    payment_display.columns = [
        "Payment Method",
        "Trips",
        "Share (%)",
    ]

    st.dataframe(
        payment_display,
        width="stretch",
        hide_index=True,
    )


# --------------------------------------------------
# Credit-card tip analysis
# --------------------------------------------------

st.divider()
st.subheader("Credit Card Tip Analysis")

st.caption(
    "Tip metrics are restricted to credit-card trips because "
    "cash tips are not reliably captured in the source data."
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Recorded Tips",
    f"${tips['total_tips']:,.0f}",
)

col2.metric(
    "Avg Tip per Trip",
    f"${tips['avg_tip_per_trip']:.2f}",
)

col3.metric(
    "Tip-to-Fare Ratio",
    f"{tips['tip_to_fare_pct']:.2f}%",
)


tip_zones_df = pd.DataFrame(tip_zones)

fig_tips = px.bar(
    tip_zones_df.sort_values("total_tips"),
    x="total_tips",
    y="Zone",
    orientation="h",
    hover_data=[
        "Borough",
        "total_credit_card_trips",
        "avg_tip_per_trip",
        "tip_to_fare_pct",
    ],
    labels={
        "total_tips": "Recorded Tips ($)",
        "Zone": "Pickup Zone",
    },
)

fig_tips = apply_taxi_plotly_theme(
    fig_tips
)

st.plotly_chart(
    fig_tips,
    width="stretch",
)


# --------------------------------------------------
# Key business takeaways
# --------------------------------------------------

st.divider()
st.subheader("Key Business Takeaways")

st.markdown(
    """
- **Airport pickups generate exceptional trip value.** JFK and LaGuardia lead
  fare revenue despite not being the highest-volume pickup zones. Their much
  higher average fares make airport demand commercially important.

- **High demand does not automatically mean high revenue.** Several Manhattan
  zones generate very large trip volumes, while airport zones produce
  substantially more fare revenue per trip.

- **Credit cards dominate customer payments.** More than 87% of trips are paid
  by credit card, making electronic payments the primary transaction channel.

- **Recorded tips represent a meaningful part of credit-card trip economics.**
  Credit-card trips show a 22.47% recorded tip-to-fare ratio. Cash tips are not
  reliably captured in the source data and should therefore not be compared
  directly.
"""
)