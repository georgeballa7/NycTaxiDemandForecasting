import streamlit as st


TAXI_YELLOW = "#F5B800"
CHECKER_BLACK = "#202124"
WARM_GRAY = "#F7F6F2"
TAXI_CREAM = "#FFF8E1"
GRID_GRAY = "#E2E2E2"
SUCCESS_GREEN = "#2E7D32"


def apply_streamlit_theme():
    """Apply a restrained NYC Yellow Cab visual identity to Streamlit."""

    st.markdown(
        f"""
        <style>
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }}

        h1 {{
            letter-spacing: -0.02em;
        }}

        h2, h3 {{
            color: {CHECKER_BLACK};
        }}

        div[data-testid="stMetric"] {{
            border: 1px solid #ECE8DD;
            border-radius: 12px;
            padding: 0.8rem 1rem;
            background: #FFFFFF;
        }}

        div[data-testid="stMetric"] label {{
            color: #5F6368;
        }}

        div[data-testid="stAlert"] {{
            border-radius: 10px;
        }}

        .stButton > button[kind="primary"] {{
            border-radius: 9px;
            font-weight: 650;
        }}

        section[data-testid="stSidebar"] {{
            border-right: 1px solid #EEE9DD;
        }}

        section[data-testid="stSidebar"] hr {{
            border-color: #E8E2D5;
        }}

        .taxi-accent {{
            width: 52px;
            height: 4px;
            background: {TAXI_YELLOW};
            border-radius: 999px;
            margin: -0.45rem 0 1rem 0;
        }}

        .taxi-section-note {{
            color: #666B70;
            font-size: 0.92rem;
            margin-top: -0.5rem;
            margin-bottom: 0.8rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_accent():
    st.markdown(
        '<div class="taxi-accent"></div>',
        unsafe_allow_html=True,
    )


def apply_taxi_plotly_theme(fig):
    """Apply the NYC Yellow Cab visual identity to a Plotly figure."""

    for trace in fig.data:
        if trace.type == "bar":
            trace.marker.color = TAXI_YELLOW

        elif trace.type in ("scatter", "scattergl"):
            trace.line.color = TAXI_YELLOW

        elif trace.type == "pie":
            trace.marker.colors = [
                TAXI_YELLOW,
                CHECKER_BLACK,
                "#D89E00",
                "#8C7A3B",
                "#6B7280",
            ]

    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            color=CHECKER_BLACK,
        ),
        xaxis=dict(
            gridcolor=GRID_GRAY,
            zerolinecolor=GRID_GRAY,
        ),
        yaxis=dict(
            gridcolor=GRID_GRAY,
            zerolinecolor=GRID_GRAY,
        ),
        legend=dict(
            font=dict(
                color=CHECKER_BLACK,
            ),
        ),
    )

    return fig
