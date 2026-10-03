# Valmo Pata prototype

Meesho DICE S3 · Team Prod Gods, IIT Kanpur

Two pages:
- **Live demo**: customer phone → rider phone → address graph, updating as you click.
- **What it's worth**: 30,000 synthetic orders calibrated to the Meesho case pack (80% COD, 20% / 5% RTO, 15 / 17 / 22% by distance). Not real Meesho data.

## Files
    app.py               entry point (page menu)
    live_demo_page.py    page 1
    live_demo.html       the live demo itself (also works on its own in any browser)
    dashboard.py         page 2
    data/                synthetic orders
    requirements.txt
    .streamlit/config.toml   colours

## Run locally
    pip install -r requirements.txt
    streamlit run app.py

## Deploy on Streamlit Community Cloud
Push every file above to a public GitHub repo, then share.streamlit.io → Create app → main file `app.py` → Deploy.
