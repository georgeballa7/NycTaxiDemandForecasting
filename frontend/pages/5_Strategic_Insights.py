import pandas as pd
import streamlit as st

from frontend.utils.api_client import (
    get_business_summary,
    get_revenue_by_zone,
    get_top_zones,
)


st.set_page_config(
    page_title=(
        "Strategic Insights | "
        "NYC Taxi Demand Forecasting and Business Analytics"
    ),
    page_icon="🎯",
    layout="wide",
)


st.title("🎯 Strategic Insights")
st.caption(
    "Turning demand forecasting and business analytics into "
    "practical fleet-planning decisions."
)


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


# --------------------------------------------------
# Executive summary
# --------------------------------------------------

st.subheader("Executive Summary")

st.markdown(
    """
    The analysis shows that operating decisions should not be based on
    trip demand alone. High-demand locations provide strong opportunities
    for vehicle utilization, while high-value locations can generate
    substantially more fare revenue per trip.

    Combining historical demand patterns, short-term forecasting and
    commercial performance therefore provides a stronger basis for fleet
    planning than any single metric.
    """
)


# --------------------------------------------------
# Where should the fleet operate?
# --------------------------------------------------

st.divider()
st.subheader("1. Where Should the Fleet Operate?")

top_demand_zone = demand_df.iloc[0]

st.markdown(
    f"""
    **{top_demand_zone['Zone']}** is the highest-demand pickup zone in
    the analyzed ranking, with approximately
    **{top_demand_zone['total_demand']:,} trips**.

    High-demand zones are particularly useful for maintaining vehicle
    utilization and reducing the risk of drivers waiting too long for
    passengers.

    **Operational implication:** Positioning vehicles near consistently
    high-demand zones can improve the probability of quickly finding the
    next passenger.
    """
)


# --------------------------------------------------
# When should vehicles operate?
# --------------------------------------------------

st.divider()
st.subheader("2. When Should Vehicles Be Deployed?")

st.markdown(
    """
    Demand is strongly influenced by time. The Demand Explorer shows
    recurring hourly and weekly patterns rather than uniform taxi demand
    throughout the day.

    **Operational implication:** Fleet size should vary with expected
    demand. More vehicles can be deployed during recurring high-demand
    periods, while quieter periods may require fewer active vehicles.

    This can improve fleet utilization and reduce unnecessary idle time.
    """
)


# --------------------------------------------------
# Demand versus commercial value
# --------------------------------------------------

st.divider()
st.subheader("3. Demand Does Not Equal Commercial Value")

top_revenue_zone = revenue_df.iloc[0]

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Highest-Demand Zone",
        top_demand_zone["Zone"],
        f"{top_demand_zone['total_demand']:,} trips",
    )

with col2:
    st.metric(
        "Highest Fare-Revenue Zone",
        top_revenue_zone["Zone"],
        f"${top_revenue_zone['fare_amount'] / 1_000_000:.1f}M",
    )

st.markdown(
    """
    The highest-demand locations are not necessarily the locations
    generating the greatest fare revenue.

    This distinction matters for fleet strategy. A high-volume zone can
    provide frequent trips, while another zone may produce fewer but much
    more valuable trips.

    **Strategic implication:** Vehicle positioning should consider both
    expected trip demand and expected trip value.
    """
)


# --------------------------------------------------
# Airport strategy
# --------------------------------------------------

st.divider()
st.subheader("4. Airports Represent High-Value Opportunities")

airport_df = revenue_df[
    revenue_df["service_zone"] == "Airports"
]

if not airport_df.empty:
    st.dataframe(
        airport_df[
            [
                "Zone",
                "total_trips",
                "fare_amount",
                "avg_fare_per_trip",
            ]
        ].rename(
            columns={
                "Zone": "Airport Zone",
                "total_trips": "Trips",
                "fare_amount": "Fare Revenue ($)",
                "avg_fare_per_trip": "Avg Fare / Trip ($)",
            }
        ),
        width="stretch",
        hide_index=True,
    )

st.markdown(
    """
    Airport pickups stand out because their average fare per trip is
    substantially higher than that of many high-volume Manhattan zones.

    **Strategic implication:** Airport demand deserves dedicated attention
    when planning fleet allocation. However, operators should balance the
    higher trip value against operational factors such as travel time,
    waiting time and vehicle availability.
    """
)


# --------------------------------------------------
# Forecast-driven planning
# --------------------------------------------------

st.divider()
st.subheader("5. Use Forecasts for Fleet Planning")

st.markdown(
    """
    Historical patterns explain where and when demand has occurred.
    The forecasting layer adds a forward-looking signal by estimating
    demand for upcoming periods.

    **Operational implication:** Forecasts can support decisions about
    how many vehicles to deploy and where additional capacity may be
    needed before demand materializes.

    Forecasts should support operational decisions rather than replace
    them, since unexpected events and conditions can still change demand.
    """
)


# --------------------------------------------------
# Recommended strategy
# --------------------------------------------------

st.divider()
st.subheader("Recommended Operating Strategy")

st.success(
    """
    Combine demand, timing, trip value and forecasts when allocating the
    fleet. Use high-demand zones to support vehicle utilization, monitor
    high-value airport opportunities for revenue potential, and use the
    demand forecast to adjust capacity ahead of expected changes.

    The central lesson from the project is simple:

    **Optimize for expected demand and economic value together — not for
    trip volume alone.**
    """
)