"""Live demo: customer phone -> rider phone -> address graph, in one interactive page."""
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

HTML = Path(__file__).resolve().parent / "live_demo.html"
if not HTML.exists():
    st.error("live_demo.html not found. Upload it to the main folder of your GitHub repo, next to app.py.")
    st.stop()

st.markdown("<style>section[data-testid='stMain'] .block-container{padding-top:1.2rem;padding-left:1.2rem;padding-right:1.2rem;max-width:100%}</style>",
            unsafe_allow_html=True)
st.caption("Place an order, respond as the customer, deliver as the rider, and watch the address graph update. "
           "Open **Impact at scale** (top menu) for the 30,000-order view.")
components.html(HTML.read_text(encoding="utf-8"), height=1180, scrolling=True)
