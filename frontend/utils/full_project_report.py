from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from frontend.utils.api_client import (
    get_business_summary,
    get_demand_by_hour,
    get_demand_by_weekday,
    get_demand_date_range,
    get_future_model_metrics,
    get_metrics,
    get_payment_breakdown,
    get_revenue_by_zone,
    get_tip_analysis,
    get_top_zones,
)


REPORT_TITLE = "NYC Taxi Demand Forecasting and Business Analytics"


def _money(value):
    """Format a numeric value as US-dollar currency with two decimal places."""
    return f"${value:,.2f}"


def _money_millions(value):
    """Format a numeric dollar value in millions with one decimal place."""
    return f"${value / 1_000_000:.1f}M"


def _table(rows, widths=None):
    """Build a consistently styled ReportLab table for the project report."""
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EEF5")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
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


def _footer(canvas, doc):
    """Draw the report title and current page number in the PDF footer."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(18 * mm, 10 * mm, REPORT_TITLE)
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_full_project_report():
    """Build the current user-facing PDF report from production API analytics.

    Returns
    -------
    bytes
        Complete in-memory PDF document.

    Notes
    -----
    The function retrieves current demand, model and business metrics from the
    API, formats the report with ReportLab tables and narrative sections, adds
    page footers, and returns the generated PDF bytes without writing a file.
    """
    data_range = get_demand_date_range()
    historical_metrics = get_metrics()
    future_metrics = sorted(
        get_future_model_metrics(),
        key=lambda row: (row["mae"], row["rmse"], row["model"]),
    )
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
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=21,
            leading=26,
            alignment=TA_CENTER,
            spaceAfter=10,
        )
    )
    story = [
        Paragraph(REPORT_TITLE, styles["ReportTitle"]),
        Paragraph("Live Project Report", styles["Heading2"]),
        Spacer(1, 5 * mm),
        Paragraph(
            f"Data coverage: {data_range['min_date']} through {data_range['max_date']}. "
            "Values are loaded from the same FastAPI production endpoints used by the Streamlit application.",
            styles["BodyText"],
        ),
        Spacer(1, 8 * mm),
        Paragraph("1. Forecasting validation", styles["Heading1"]),
        Paragraph("Historical model evaluation", styles["Heading2"]),
        _table(
            [["Model", "MAE", "RMSE"]]
            + [[row["model"], f"{row['mae']:.2f}", f"{row['rmse']:.2f}"] for row in historical_metrics],
            [75 * mm, 38 * mm, 38 * mm],
        ),
        Spacer(1, 5 * mm),
        Paragraph("True-future model selection", styles["Heading2"]),
        _table(
            [["Model", "MAE", "RMSE", "Status"]]
            + [
                [
                    row["model"],
                    f"{row['mae']:.2f}",
                    f"{row['rmse']:.2f}",
                    "Production" if index == 0 else "Candidate",
                ]
                for index, row in enumerate(future_metrics)
            ],
            [65 * mm, 30 * mm, 30 * mm, 35 * mm],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            "The future production model is selected automatically by lowest rolling-holdout MAE, "
            "with RMSE as tie-breaker. Only forecast-safe features are used for arbitrary future dates.",
            styles["BodyText"],
        ),
        Spacer(1, 8 * mm),
        Paragraph("2. Demand patterns", styles["Heading1"]),
    ]

    if demand_by_hour:
        peak = max(demand_by_hour, key=lambda row: row["avg_demand"])
        story.append(
            Paragraph(
                f"Peak average hourly demand occurs around {peak['hour']:02d}:00.",
                styles["BodyText"],
            )
        )
    if demand_by_weekday:
        peak_day = max(demand_by_weekday, key=lambda row: row["avg_demand"])
        story.append(
            Paragraph(
                f"{peak_day['weekday']} currently has the highest observed average weekday demand.",
                styles["BodyText"],
            )
        )
    if top_zones:
        story.extend(
            [
                Spacer(1, 4 * mm),
                _table(
                    [["Top zone", "Borough", "Total demand"]]
                    + [[row["Zone"], row["Borough"], f"{row['total_demand']:,}"] for row in top_zones[:5]],
                    [75 * mm, 40 * mm, 45 * mm],
                ),
            ]
        )

    story.extend(
        [
            Spacer(1, 8 * mm),
            Paragraph("3. Business analytics", styles["Heading1"]),
            _table(
                [
                    ["Metric", "Value"],
                    ["Total trips", f"{business_summary['total_trips']:,}"],
                    ["Fare revenue", _money_millions(business_summary["total_fare_amount"])],
                    ["Total collected", _money_millions(business_summary["total_amount"])],
                    ["Recorded tips", _money_millions(business_summary["total_tip_amount"])],
                    ["Average trip distance", f"{business_summary['avg_trip_distance']:.2f} mi"],
                ],
                [85 * mm, 65 * mm],
            ),
        ]
    )

    if revenue_zones:
        story.extend(
            [
                Spacer(1, 5 * mm),
                Paragraph("Top pickup zones by fare revenue", styles["Heading2"]),
                _table(
                    [["Zone", "Borough", "Trips", "Fare revenue"]]
                    + [
                        [row["Zone"], row["Borough"], f"{row['total_trips']:,}", _money_millions(row["fare_amount"])]
                        for row in revenue_zones[:5]
                    ],
                    [65 * mm, 35 * mm, 30 * mm, 35 * mm],
                ),
            ]
        )

    if payments:
        story.extend(
            [
                Spacer(1, 5 * mm),
                Paragraph("Payment mix", styles["Heading2"]),
                _table(
                    [["Payment method", "Trips", "Share"]]
                    + [[row["payment_method"], f"{row['total_trips']:,}", f"{row['trip_share_pct']:.2f}%"] for row in payments],
                    [70 * mm, 45 * mm, 35 * mm],
                ),
            ]
        )

    story.extend(
        [
            Spacer(1, 5 * mm),
            Paragraph(
                f"Recorded card tips average {_money(tips['avg_tip_per_trip'])} per trip, "
                f"with a {tips['tip_to_fare_pct']:.2f}% tip-to-fare ratio. Cash tips are not reliably captured.",
                styles["BodyText"],
            ),
            Spacer(1, 8 * mm),
            Paragraph("4. Interpretation", styles["Heading1"]),
            Paragraph(
                "The application combines historical demand analysis, model validation, true-future forecasting "
                "and commercial trip analytics. Forecasts are planning signals rather than guarantees and should "
                "be interpreted together with operational context.",
                styles["BodyText"],
            ),
        ]
    )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buffer.seek(0)
    return buffer.getvalue()
