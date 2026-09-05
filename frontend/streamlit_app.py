import sys
from pathlib import Path

import streamlit as st


_repo_root = Path(__file__).resolve().parent.parent

if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))


from frontend.utils.full_project_report import generate_full_project_report
from frontend.utils.theme import apply_streamlit_theme


st.set_page_config(
    page_title="NYC Taxi Demand Forecasting and Business Analytics",
    page_icon="🚕",
    layout="wide",
)

apply_streamlit_theme()


pages = [
    st.Page("pages/1_Overview.py", title="Overview", icon="🏠", default=True),
    st.Page("pages/2_Demand_Explorer.py", title="Demand Explorer", icon="📊"),
    st.Page("pages/3_Forecast.py", title="Forecast", icon="🔮"),
    st.Page("pages/4_Business_Insights.py", title="Business Insights", icon="💼"),
    st.Page("pages/5_Strategic_Insights.py", title="Strategic Insights", icon="🎯"),
]

navigation = st.navigation(pages, position="hidden")


with st.sidebar:
    st.markdown(
        """
        <div style="font-weight:700;font-size:1.05rem;line-height:1.35;margin-bottom:0.8rem;">
            🚕 NYC Taxi Demand Forecasting<br>
            <span style="font-weight:500;color:#6B6F73;">Business Analytics</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.page_link("pages/1_Overview.py", label="Overview", icon="🏠")
    st.page_link("pages/2_Demand_Explorer.py", label="Demand Explorer", icon="📊")
    st.page_link("pages/3_Forecast.py", label="Forecast", icon="🔮")
    st.page_link("pages/4_Business_Insights.py", label="Business Insights", icon="💼")
    st.page_link("pages/5_Strategic_Insights.py", label="Strategic Insights", icon="🎯")

    st.divider()
    st.markdown("**📄 Full Project Report**")

    if st.button(
        "Generate PDF",
        width="stretch",
        help="Create a user-facing PDF report from the analytics shown across the Streamlit application.",
    ):
        with st.spinner("Generating full project report..."):
            try:
                st.session_state["full_project_report_pdf"] = generate_full_project_report()
                st.success("Report ready.")
            except Exception as exc:
                st.error("The PDF report could not be generated.")
                st.exception(exc)

    if "full_project_report_pdf" in st.session_state:
        st.download_button(
            label="Download PDF",
            data=st.session_state["full_project_report_pdf"],
            file_name="NYC_Taxi_Full_Project_Report.pdf",
            mime="application/pdf",
            width="stretch",
        )


navigation.run()
