TAXI_YELLOW = "#F5B800"
CHECKER_BLACK = "#202124"
WARM_GRAY = "#F7F6F2"
TAXI_CREAM = "#FFF8E1"
GRID_GRAY = "#E2E2E2"
SUCCESS_GREEN = "#2E7D32"


def apply_taxi_plotly_theme(fig):
    """
    Apply the NYC Yellow Cab visual identity to a Plotly figure.
    """

    # Recolor existing Plotly traces
    for index, trace in enumerate(fig.data):

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