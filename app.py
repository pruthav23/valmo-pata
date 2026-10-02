"""
Valmo Pata prototype · Meesho DICE S3 · Team Prod Gods, IIT Kanpur
Entry point: two pages, the live demo and the impact dashboard.   streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Valmo Pata prototype", page_icon="📍", layout="wide")

pg = st.navigation([
    st.Page("live_demo_page.py", title="Live demo", icon="📍", default=True),
    st.Page("dashboard.py", title="Impact at scale", icon="📊"),
], position="top")
pg.run()
