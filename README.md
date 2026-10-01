# Valmo Pata · address graph prototype

Meesho DICE S3 · Team Prod Gods, IIT Kanpur

Interactive demo of Valmo Pata on 30,000 synthetic orders calibrated to the Meesho case pack (80% COD, 20% / 5% RTO, 15 / 17 / 22% by distance). Not real Meesho data.

## Run locally
    pip install -r requirements.txt
    streamlit run app.py

## Deploy on Streamlit Community Cloud
1. Create a public GitHub repo and upload everything in this folder (keep the data/ folder).
2. Go to share.streamlit.io, sign in with GitHub, click Create app.
3. Pick the repo, branch main, main file app.py, and click Deploy.
