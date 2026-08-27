import sys
from pathlib import Path

import streamlit as st


# Bootstrap the repository root so `frontend.*` package imports work
# when Streamlit executes this file directly.
_repo_root = Path(__file__).resolve().parent.parent

if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))


from frontend.config.settings import PROJECT_ROOT
from frontend.utils.full_project_report import generate_full_project_report


st.set_page_config(
    page_title="NYC Taxi Demand Forecasting and Business Analytics",
    page_icon="🚕",
    layout="wide",
)


# --------------------------------------------------
# Pages
# --------------------------------------------------

pages = [
    st.Page(
        "pages/1_Overview.py",
        title="Overview",
        icon="🏠",
        default=True,
    ),
    st.Page(
        "pages/2_Demand_Explorer.py",
        title="Demand Explorer",
        icon="📊",
    ),
    st.Page(
        "pages/3_Forecast.py",
        title="Forecast",
        icon="🔮",
    ),
    st.Page(
        "pages/4_Business_Insights.py",
        title="Business Insights",
        icon="💼",
    ),
    st.Page(
        "pages/5_Strategic_Insights.py",
        title="Strategic Insights",
        icon="🎯",
    ),
]


# Hide Streamlit's automatic navigation.
navigation = st.navigation(
    pages,
    position="hidden",
)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:

    st.markdown(
        """
        <div style="
            font-weight: 700;
            font-size: 1.05rem;
            line-height: 1.35;
            margin-bottom: 0.8rem;
        ">
            NYC Taxi Demand Forecasting<br>
            and Business Analytics
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Navigation
    st.page_link(
        "pages/1_Overview.py",
        label="Overview",
        icon="🏠",
    )

    st.page_link(
        "pages/2_Demand_Explorer.py",
        label="Demand Explorer",
        icon="📊",
    )

    st.page_link(
        "pages/3_Forecast.py",
        label="Forecast",
        icon="🔮",
    )

    st.page_link(
        "pages/4_Business_Insights.py",
        label="Business Insights",
        icon="💼",
    )

    st.page_link(
        "pages/5_Strategic_Insights.py",
        label="Strategic Insights",
        icon="🎯",
    )

    st.divider()

    # Full Project Report
    st.markdown("**📄 Full Project Report**")

    if st.button(
        "Generate PDF",
        width="stretch",
        help=(
            "Create a user-facing PDF report from the "
            "analytics shown across the Streamlit application."
        ),
    ):
        with st.spinner("Generating full project report..."):
            try:
                st.session_state["full_project_report_pdf"] = (
                    generate_full_project_report()
                )
                st.success("Report ready.")

            except Exception as exc:
                st.error(
                    "The PDF report could not be generated."
                )
                st.exception(exc)

    if "full_project_report_pdf" in st.session_state:
        st.download_button(
            label="Download PDF",
            data=st.session_state[
                "full_project_report_pdf"
            ],
            file_name="NYC_Taxi_Full_Project_Report.pdf",
            mime="application/pdf",
            width="stretch",
        )


# --------------------------------------------------
# Run selected page
# --------------------------------------------------

navigation.run()