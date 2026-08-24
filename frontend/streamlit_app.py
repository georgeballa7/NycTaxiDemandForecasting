import requests
import streamlit as st


API_BASE_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="NYC Taxi Demand Forecasting",
    layout="wide",
)


st.title("NYC Taxi Demand Forecasting")


@st.cache_data(ttl=60)
def check_api_health():
    response = requests.get(
        f"{API_BASE_URL}/health",
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


try:
    health = check_api_health()

    if health.get("status") == "ok":
        st.success("FastAPI connection successful.")
    else:
        st.warning("FastAPI responded, but status is not OK.")

except requests.RequestException:
    st.error(
        "FastAPI is not reachable. "
        "Make sure the API server is running."
    )