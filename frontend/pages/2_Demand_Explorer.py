from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.utils.api_client import (
    get_demand_date_range,
    get_zones,
    get_zone_demand_by_hour,
    get_zone_demand_by_weekday,
    get_zone_demand_over_time,
)

from frontend.utils.theme import apply_taxi_plotly_theme

# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Demand Explorer | NYC Taxi Demand Forecasting",
    page_icon="📊",
    layout="wide",
)

st.title("Demand Explorer")

st.write(
    "Explore taxi demand patterns by borough, taxi zone, "
    "time of day and weekday."
)


# --------------------------------------------------
# Load shared reference data
# --------------------------------------------------

@st.cache_data(ttl=300)
def load_zones():
    return get_zones()


@st.cache_data(ttl=300)
def load_data_range():
    return get_demand_date_range()


try:
    zones_df = pd.DataFrame(load_zones())
    data_range = load_data_range()

    min_data_date = date.fromisoformat(
        data_range["min_date"]
    )
    max_data_date = date.fromisoformat(
        data_range["max_date"]
    )

    # --------------------------------------------------
    # Filters
    # --------------------------------------------------

    st.subheader("Filters")

    filter_col1, filter_col2 = st.columns(2)

    boroughs = sorted(
        zones_df["Borough"]
        .dropna()
        .unique()
        .tolist()
    )

    with filter_col1:
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
            zones_df["Borough"]
            == selected_borough
        ]
        .sort_values("Zone")
    )

    zone_names = (
        borough_zones_df["Zone"]
        .dropna()
        .tolist()
    )

    with filter_col2:
        selected_zone = st.selectbox(
            "Taxi Zone",
            zone_names,
        )

    selected_zone_row = (
        borough_zones_df[
            borough_zones_df["Zone"]
            == selected_zone
        ]
        .iloc[0]
    )

    location_id = int(
        selected_zone_row["LocationID"]
    )

    # --------------------------------------------------
    # Dynamic date filter
    # --------------------------------------------------

    st.caption(
        f"Available demand data: "
        f"{min_data_date:%d %b %Y} – {max_data_date:%d %b %Y}"
    )

    date_col1, date_col2 = st.columns(2)

    with date_col1:
        start_date = st.date_input(
            "Start Date",
            value=min_data_date,
            min_value=min_data_date,
            max_value=max_data_date,
        )

    with date_col2:
        end_date = st.date_input(
            "End Date",
            value=max_data_date,
            min_value=min_data_date,
            max_value=max_data_date,
        )

    if start_date > end_date:
        st.warning(
            "Start date must be before or equal to end date."
        )
        st.stop()

    # --------------------------------------------------
    # Load data for selected taxi zone
    # --------------------------------------------------

    @st.cache_data(ttl=300)
    def load_zone_data(
        location_id,
        start_date,
        end_date,
    ):
        demand_by_hour = get_zone_demand_by_hour(
            location_id,
            start_date=start_date,
            end_date=end_date,
        )

        demand_by_weekday = get_zone_demand_by_weekday(
            location_id,
            start_date=start_date,
            end_date=end_date,
        )

        demand_over_time = get_zone_demand_over_time(
            location_id,
            start_date=start_date,
            end_date=end_date,
        )

        return (
            demand_by_hour,
            demand_by_weekday,
            demand_over_time,
        )

    (
        demand_by_hour,
        demand_by_weekday,
        demand_over_time,
    ) = load_zone_data(
        location_id,
        start_date,
        end_date,
    )

    hour_df = pd.DataFrame(demand_by_hour)
    weekday_df = pd.DataFrame(demand_by_weekday)
    time_df = pd.DataFrame(demand_over_time)

    time_df["date"] = pd.to_datetime(
        time_df["date"]
    )

    # --------------------------------------------------
    # Selected zone summary
    # --------------------------------------------------

    st.divider()

    st.subheader(
        f"{selected_zone}, {selected_borough}"
    )

    total_demand = int(
        time_df["total_demand"].sum()
    )

    avg_daily_demand = (
        time_df["total_demand"].mean()
    )

    peak_row = time_df.loc[
        time_df["total_demand"].idxmax()
    ]

    peak_daily_demand = int(
        peak_row["total_demand"]
    )

    peak_date = peak_row["date"].strftime(
        "%d %b %Y"
    )

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric(
            "Total Pickups",
            f"{total_demand:,}",
        )

    with kpi2:
        st.metric(
            "Avg. Daily Demand",
            f"{avg_daily_demand:,.0f}",
        )

    with kpi3:
        st.metric(
            "Peak Daily Demand",
            f"{peak_daily_demand:,}",
        )

    with kpi4:
        st.metric(
            "Peak Date",
            peak_date,
        )

    # --------------------------------------------------
    # Demand over time
    # --------------------------------------------------

    st.subheader("Demand over Time")

    time_fig = px.line(
        time_df,
        x="date",
        y="total_demand",
        labels={
            "date": "Date",
            "total_demand": "Taxi Pickups",
        },
    )

    time_fig.update_layout(
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
    time_fig = apply_taxi_plotly_theme(time_fig)

    st.plotly_chart(
        time_fig,
        width="stretch",
    )

    # --------------------------------------------------
    # Demand patterns
    # --------------------------------------------------

    st.subheader("Demand Patterns")

    hour_col, weekday_col = st.columns(2)

    with hour_col:
        hour_fig = px.bar(
            hour_df,
            x="hour",
            y="avg_demand",
            labels={
                "hour": "Hour",
                "avg_demand": "Average Demand",
            },
            title="Average Demand by Hour",
        )

        hour_fig.update_layout(
            xaxis=dict(
                tickmode="linear",
                dtick=2,
            ),
            xaxis_title="Hour of Day",
            yaxis_title="Average Demand",
            showlegend=False,
            margin=dict(
                l=20,
                r=20,
                t=50,
                b=20,
            ),
        )

        hour_fig = apply_taxi_plotly_theme(hour_fig)

        st.plotly_chart(
            hour_fig,
            width="stretch",
        )

    with weekday_col:
        weekday_df = weekday_df.sort_values(
            "weekday_number"
        )

        weekday_fig = px.bar(
            weekday_df,
            x="weekday",
            y="avg_demand",
            labels={
                "weekday": "Weekday",
                "avg_demand": "Average Demand",
            },
            title="Average Demand by Weekday",
        )

        weekday_fig.update_layout(
            xaxis_title=None,
            yaxis_title="Average Demand",
            showlegend=False,
            margin=dict(
                l=20,
                r=20,
                t=50,
                b=20,
            ),
        )
        weekday_fig = apply_taxi_plotly_theme(weekday_fig)

        st.plotly_chart(
            weekday_fig,
            width="stretch",
        )

    # --------------------------------------------------
    # Demand Insights
    # --------------------------------------------------

    st.subheader("Demand Insights")

    peak_hour_row = hour_df.loc[
        hour_df["avg_demand"].idxmax()
    ]

    peak_hour = int(
        peak_hour_row["hour"]
    )

    peak_hour_demand = float(
        peak_hour_row["avg_demand"]
    )

    low_hour_row = hour_df.loc[
        hour_df["avg_demand"].idxmin()
    ]

    low_hour = int(
        low_hour_row["hour"]
    )

    low_hour_demand = float(
        low_hour_row["avg_demand"]
    )

    peak_weekday_row = weekday_df.loc[
        weekday_df["avg_demand"].idxmax()
    ]

    peak_weekday = peak_weekday_row[
        "weekday"
    ]

    peak_weekday_demand = float(
        peak_weekday_row["avg_demand"]
    )

    overall_hourly_average = (
        hour_df["avg_demand"].mean()
    )

    peak_vs_average = (
        (
            peak_hour_demand
            / overall_hourly_average
        )
        - 1
    ) * 100

    insight1, insight2, insight3, insight4 = st.columns(4)

    with insight1:
        st.metric(
            "Peak Hour",
            f"{peak_hour:02d}:00",
            f"{peak_hour_demand:.1f} avg. pickups",
        )

    with insight2:
        st.metric(
            "Lowest-Demand Hour",
            f"{low_hour:02d}:00",
            f"{low_hour_demand:.1f} avg. pickups",
        )

    with insight3:
        st.metric(
            "Strongest Weekday",
            peak_weekday,
            f"{peak_weekday_demand:.1f} avg. pickups",
        )

    with insight4:
        st.metric(
            "Peak vs. Average",
            f"+{peak_vs_average:.1f}%",
        )

    st.info(
        f"**{selected_zone}, {selected_borough}:** "
        f"Demand is highest around **{peak_hour:02d}:00**, "
        f"with an average of **{peak_hour_demand:.1f} pickups per hour**. "
        f"The lowest-demand period occurs around **{low_hour:02d}:00**. "
        f"Across the selected date range, **{peak_weekday}** shows the "
        f"strongest average demand. Peak-hour demand is approximately "
        f"**{peak_vs_average:.1f}% above the zone's average hourly demand**."
    )

except Exception as exc:
    st.error(
        "The Demand Explorer could not load data from the API."
    )

    st.exception(exc)
