import pandas as pd
import streamlit as st

from frontend.utils.api_client import (
    get_business_summary,
    get_revenue_by_zone,
    get_top_zones,
)
from frontend.utils.theme import page_accent


st.set_page_config(
    page_title="Strategic Insights | NYC Taxi Demand Forecasting and Business Analytics",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Strategic Insights")
page_accent()
st.caption("Turning demand forecasting and business analytics into practical fleet-planning decisions.")


@st.cache_data(ttl=300)
def load_strategic_data():
    return (
        get_business_summary(),
        get_top_zones(limit=10),
        get_revenue_by_zone(limit=10),
    )


try:
    summary, demand_zones, revenue_zones = load_strategic_data()
except Exception as exc:
    st.error("Strategic insights could not load data from the API.")
    st.exception(exc)
    st.stop()


demand_df = pd.DataFrame(demand_zones)
revenue_df = pd.DataFrame(revenue_zones)
top_demand_zone = demand_df.iloc[0]
top_revenue_zone = revenue_df.iloc[0]

st.subheader("Executive Summary")
st.write(
    "Operating decisions should not be based on trip demand alone. High-demand locations "
    "support vehicle utilization, while high-value locations can generate substantially more "
    "fare revenue per trip. Combining demand, timing, commercial value and forecasts provides "
    "a stronger basis for fleet planning than any single metric."
)

summary_col1, summary_col2, summary_col3 = st.columns(3)
summary_col1.metric("Trips Analyzed", f"{summary['total_trips']:,}")
summary_col2.metric("Highest-Demand Zone", top_demand_zone["Zone"])
summary_col3.metric("Highest Fare-Revenue Zone", top_revenue_zone["Zone"])

st.divider()
st.subheader("1. Where Should the Fleet Operate?")
st.markdown(
    f"**{top_demand_zone['Zone']}** is the highest-demand pickup zone in the current ranking, "
    f"with approximately **{top_demand_zone['total_demand']:,} trips**. High-demand zones can "
    "help maintain vehicle utilization and reduce passenger-search time."
)
st.info("Operational implication: position capacity near consistently high-demand zones when demand is expected to be strong.")

st.divider()
st.subheader("2. When Should Vehicles Be Deployed?")
st.write(
    "Demand follows recurring hourly and weekly patterns rather than remaining uniform throughout the day. "
    "Fleet size can therefore be adjusted to expected demand, with more vehicles during recurring peaks and "
    "less capacity during quieter periods."
)
st.info("Operational implication: vary active fleet capacity by time of day and weekday instead of using a flat deployment plan.")

st.divider()
st.subheader("3. Demand Does Not Equal Commercial Value")
col1, col2 = st.columns(2)
col1.metric(
    "Highest-Demand Zone",
    top_demand_zone["Zone"],
    f"{top_demand_zone['total_demand']:,} trips",
)
col2.metric(
    "Highest Fare-Revenue Zone",
    top_revenue_zone["Zone"],
    f"${top_revenue_zone['fare_amount'] / 1_000_000:.1f}M",
)
st.write(
    "A high-volume zone can provide frequent trips, while another zone may produce fewer but more valuable trips."
)
st.info("Strategic implication: vehicle positioning should consider both expected trip demand and expected trip value.")

st.divider()
st.subheader("4. Airports Represent High-Value Opportunities")
airport_df = revenue_df[revenue_df["service_zone"] == "Airports"]

if not airport_df.empty:
    airport_display = airport_df[
        ["Zone", "total_trips", "fare_amount", "avg_fare_per_trip"]
    ].rename(
        columns={
            "Zone": "Airport Zone",
            "total_trips": "Trips",
            "fare_amount": "Fare Revenue ($)",
            "avg_fare_per_trip": "Avg Fare / Trip ($)",
        }
    )
    st.dataframe(airport_display, width="stretch", hide_index=True)

st.write(
    "Airport pickups stand out because their average fare per trip is substantially higher than that of many "
    "high-volume Manhattan zones. This opportunity should still be balanced against travel time, queueing and vehicle availability."
)

st.divider()
st.subheader("5. Use Forecasts for Fleet Planning")
st.write(
    "Historical analytics explain where and when demand has occurred. The forecasting layer adds a forward-looking "
    "signal that can support capacity decisions before demand materializes. Unexpected events can still change demand, "
    "so forecasts should support rather than replace operational judgment."
)

st.divider()
st.subheader("Recommended Operating Strategy")
st.success(
    "**Optimize expected demand and economic value together — not trip volume alone.**\n\n"
    "Use high-demand zones to support vehicle utilization, monitor high-value airport opportunities for revenue potential, "
    "and use the demand forecast to adjust capacity ahead of expected changes."
)
