from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from frontend.utils.api_client import (
    get_business_summary,
    get_demand_by_hour,
    get_demand_by_weekday,
    get_feature_importance,
    get_metrics,
    get_payment_breakdown,
    get_revenue_by_zone,
    get_tip_analysis,
    get_top_zones,
)


REPORT_TITLE = "NYC Taxi Demand Forecasting and Business Analytics"


def _money(value):
    return f"${value:,.2f}"


def _money_millions(value):
    return f"${value / 1_000_000:.1f}M"


def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=22,
            leading=27,
            alignment=TA_CENTER,
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            spaceBefore=8,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SubsectionTitle",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=6,
            spaceAfter=5,
        )
    )

    return styles


def _table(data, column_widths=None):
    table = Table(
        data,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EEF5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    return table


def _metric_table(rows):
    return _table(
        [["Metric", "Value"]] + rows,
        column_widths=[75 * mm, 75 * mm],
    )


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(
        18 * mm,
        10 * mm,
        REPORT_TITLE,
    )
    canvas.drawRightString(
        A4[0] - 18 * mm,
        10 * mm,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def generate_full_project_report():
    """
    Build a user-facing PDF from analytics exposed in the Streamlit app.
    Technical implementation details are intentionally excluded.
    """

    metrics = get_metrics()
    feature_importance = get_feature_importance()
    demand_by_hour = get_demand_by_hour()
    demand_by_weekday = get_demand_by_weekday()
    top_zones = get_top_zones(limit=10)

    business_summary = get_business_summary()
    revenue_zones = get_revenue_by_zone(limit=10)
    payments = get_payment_breakdown()
    tips = get_tip_analysis()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=REPORT_TITLE,
        author="NYC Taxi Analytics Application",
    )

    styles = _build_styles()
    story = []

    # Cover
    story.append(Spacer(1, 25 * mm))
    story.append(Paragraph(REPORT_TITLE, styles["ReportTitle"]))
    story.append(Paragraph("Full Project Report", styles["Heading2"]))
    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            (
                "A user-facing summary of demand patterns, forecasting "
                "performance, commercial taxi activity and strategic "
                "fleet-planning implications."
            ),
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            "Analysis period: January - June 2025",
            styles["BodyText"],
        )
    )
    story.append(PageBreak())

    # 1. Overview
    story.append(Paragraph("1. Overview", styles["SectionTitle"]))

    top_zone = top_zones[0] if top_zones else None
    overview_rows = []

    for item in metrics:
        model = item.get("model", "")
        mae = item.get("mae")
        rmse = item.get("rmse")

        if model and mae is not None:
            overview_rows.append([f"{model} MAE", f"{mae:.2f}"])

        if model and rmse is not None:
            overview_rows.append([f"{model} RMSE", f"{rmse:.2f}"])

    if top_zone:
        overview_rows.append(
            [
                "Highest-demand zone",
                f"{top_zone['Zone']} ({top_zone['total_demand']:,})",
            ]
        )

    if overview_rows:
        story.append(_metric_table(overview_rows))
        story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            (
                "The overview combines historical taxi demand with model "
                "performance. Demand is concentrated in major pickup zones, "
                "while the forecasting model is evaluated against a "
                "historical baseline."
            ),
            styles["BodyText"],
        )
    )

    if top_zones:
        story.append(
            Paragraph(
                "Top Taxi Zones by Demand",
                styles["SubsectionTitle"],
            )
        )
        story.append(
            _table(
                [["Zone", "Borough", "Total Demand"]]
                + [
                    [
                        row["Zone"],
                        row["Borough"],
                        f"{row['total_demand']:,}",
                    ]
                    for row in top_zones[:5]
                ],
                column_widths=[80 * mm, 40 * mm, 35 * mm],
            )
        )

    story.append(PageBreak())

    # 2. Demand Explorer
    story.append(
        Paragraph(
            "2. Demand Explorer",
            styles["SectionTitle"],
        )
    )

    if demand_by_hour:
        peak_hour = max(
            demand_by_hour,
            key=lambda row: row["avg_demand"],
        )
        low_hour = min(
            demand_by_hour,
            key=lambda row: row["avg_demand"],
        )

        story.append(
            Paragraph(
                (
                    f"Average demand is highest around "
                    f"{peak_hour['hour']:02d}:00 and lowest around "
                    f"{low_hour['hour']:02d}:00. Demand is therefore "
                    f"strongly time-dependent rather than evenly "
                    f"distributed throughout the day."
                ),
                styles["BodyText"],
            )
        )

        story.append(Spacer(1, 4 * mm))
        story.append(
            _table(
                [["Hour", "Avg Demand", "Total Demand"]]
                + [
                    [
                        f"{row['hour']:02d}:00",
                        f"{row['avg_demand']:.2f}",
                        f"{row['total_demand']:,}",
                    ]
                    for row in demand_by_hour
                ],
                column_widths=[35 * mm, 50 * mm, 55 * mm],
            )
        )

    story.append(Spacer(1, 6 * mm))

    if demand_by_weekday:
        strongest_day = max(
            demand_by_weekday,
            key=lambda row: row["avg_demand"],
        )

        story.append(
            Paragraph(
                (
                    f"{strongest_day['weekday']} has the highest observed "
                    f"average demand in the analyzed period. Weekly "
                    f"recurrence is therefore relevant for fleet scheduling."
                ),
                styles["BodyText"],
            )
        )

        story.append(Spacer(1, 4 * mm))
        story.append(
            _table(
                [["Weekday", "Avg Demand", "Total Demand"]]
                + [
                    [
                        row["weekday"],
                        f"{row['avg_demand']:.2f}",
                        f"{row['total_demand']:,}",
                    ]
                    for row in demand_by_weekday
                ],
                column_widths=[45 * mm, 45 * mm, 55 * mm],
            )
        )

    story.append(PageBreak())

    # 3. Forecast
    story.append(Paragraph("3. Forecast", styles["SectionTitle"]))

    if metrics:
        story.append(
            _table(
                [["Model", "MAE", "RMSE"]]
                + [
                    [
                        row.get("model", ""),
                        f"{row.get('mae', 0):.2f}",
                        f"{row.get('rmse', 0):.2f}",
                    ]
                    for row in metrics
                ],
                column_widths=[70 * mm, 40 * mm, 40 * mm],
            )
        )
        story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            (
                "The forecast provides a forward-looking estimate of "
                "hourly taxi demand. It should be used as a planning signal "
                "for expected capacity needs rather than as a guarantee of "
                "future demand."
            ),
            styles["BodyText"],
        )
    )

    if feature_importance:
        top_features = sorted(
            feature_importance,
            key=lambda row: row.get("importance", 0),
            reverse=True,
        )[:5]

        story.append(
            Paragraph(
                "Most Influential Forecast Features",
                styles["SubsectionTitle"],
            )
        )

        story.append(
            _table(
                [["Feature", "Importance"]]
                + [
                    [
                        row.get("feature", ""),
                        f"{row.get('importance', 0) * 100:.2f}%",
                    ]
                    for row in top_features
                ],
                column_widths=[90 * mm, 55 * mm],
            )
        )

        if top_features:
            story.append(Spacer(1, 4 * mm))
            story.append(
                Paragraph(
                    (
                        f"The strongest forecasting signal is "
                        f"<b>{top_features[0].get('feature', '')}</b>, "
                        f"showing the importance of recurring historical "
                        f"demand patterns."
                    ),
                    styles["BodyText"],
                )
            )

    story.append(PageBreak())

    # 4. Business Insights
    story.append(
        Paragraph(
            "4. Business Insights",
            styles["SectionTitle"],
        )
    )

    story.append(
        _metric_table(
            [
                ["Total Trips", f"{business_summary['total_trips']:,}"],
                [
                    "Fare Revenue",
                    _money_millions(
                        business_summary["total_fare_amount"]
                    ),
                ],
                [
                    "Total Collected Amount",
                    _money_millions(
                        business_summary["total_amount"]
                    ),
                ],
                [
                    "Recorded Tips",
                    _money_millions(
                        business_summary["total_tip_amount"]
                    ),
                ],
                [
                    "Average Trip Distance",
                    f"{business_summary['avg_trip_distance']:.2f} mi",
                ],
            ]
        )
    )
    story.append(Spacer(1, 5 * mm))

    if revenue_zones:
        story.append(
            Paragraph(
                "Top Pickup Zones by Fare Revenue",
                styles["SubsectionTitle"],
            )
        )
        story.append(
            _table(
                [
                    [
                        "Zone",
                        "Borough",
                        "Trips",
                        "Fare Revenue",
                        "Avg Fare/Trip",
                    ]
                ]
                + [
                    [
                        row["Zone"],
                        row["Borough"],
                        f"{row['total_trips']:,}",
                        _money_millions(row["fare_amount"]),
                        _money(row["avg_fare_per_trip"]),
                    ]
                    for row in revenue_zones[:10]
                ],
                column_widths=[
                    56 * mm,
                    25 * mm,
                    27 * mm,
                    27 * mm,
                    27 * mm,
                ],
            )
        )

    if payments:
        story.append(
            Paragraph(
                "Payment Mix",
                styles["SubsectionTitle"],
            )
        )
        story.append(
            _table(
                [["Payment Method", "Trips", "Share"]]
                + [
                    [
                        row["payment_method"],
                        f"{row['total_trips']:,}",
                        f"{row['trip_share_pct']:.2f}%",
                    ]
                    for row in payments
                ],
                column_widths=[70 * mm, 45 * mm, 35 * mm],
            )
        )

    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            (
                f"Credit-card trips recorded "
                f"{_money_millions(tips['total_tips'])} in tips, "
                f"with an average recorded tip of "
                f"{_money(tips['avg_tip_per_trip'])} per trip and a "
                f"{tips['tip_to_fare_pct']:.2f}% tip-to-fare ratio. "
                f"Cash tips are not reliably captured in the source data "
                f"and should not be directly compared."
            ),
            styles["BodyText"],
        )
    )

    story.append(PageBreak())

    # 5. Strategic Insights
    story.append(
        Paragraph(
            "5. Strategic Insights",
            styles["SectionTitle"],
        )
    )

    if top_zones and revenue_zones:
        highest_demand = top_zones[0]
        highest_revenue = revenue_zones[0]

        insights = [
            (
                "<b>Where to operate:</b> "
                f"{highest_demand['Zone']} is the highest-demand zone in "
                f"the ranking. High-demand zones can support vehicle "
                f"utilization and reduce passenger-search time."
            ),
            (
                "<b>When to deploy vehicles:</b> "
                "Demand follows strong hourly and weekly patterns. Fleet "
                "capacity should therefore vary by expected demand rather "
                "than remain constant throughout the day."
            ),
            (
                "<b>Demand does not equal commercial value:</b> "
                f"{highest_revenue['Zone']} leads fare revenue, while the "
                f"highest-demand ranking is led by "
                f"{highest_demand['Zone']}. Fleet positioning should "
                f"consider both trip volume and expected trip value."
            ),
            (
                "<b>Airport strategy:</b> "
                "Airport pickup zones generate unusually high average "
                "fares per trip, making airport demand commercially "
                "important even when it is not the highest by trip volume."
            ),
            (
                "<b>Forecast-driven planning:</b> "
                "Historical demand patterns and the forecasting model can "
                "be combined to adjust fleet capacity before expected "
                "changes in demand occur."
            ),
        ]

        for insight in insights:
            story.append(
                KeepTogether(
                    [
                        Paragraph(insight, styles["BodyText"]),
                        Spacer(1, 4 * mm),
                    ]
                )
            )

    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            (
                "<b>Recommended operating strategy:</b> Optimize fleet "
                "allocation for expected demand and economic value "
                "together - not for trip volume alone."
            ),
            styles["BodyText"],
        )
    )

    doc.build(
        story,
        onFirstPage=_footer,
        onLaterPages=_footer,
    )

    buffer.seek(0)
    return buffer.getvalue()
