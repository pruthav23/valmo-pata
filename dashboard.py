"""
Impact at scale: Valmo Pata on 30,000 synthetic orders calibrated to the Meesho case pack.
Kept deliberately simple: two controls, four numbers, one map, one insight.
"""
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

FWD, REV = 50, 120            # case pack: ₹ forward per order, ₹ reverse per RTO
ANNUAL_SHIPMENTS = 1.6e9      # our deck (JM Financial / YourStory, Jan-26)
VERIFY_RADIUS_M = 15
M_LAT = 110850.0
HERE = Path(__file__).resolve().parent


def dist_m(lat1, lon1, lat2, lon2):
    return math.hypot((lat1 - lat2) * M_LAT, (lon1 - lon2) * 111320.0 * math.cos(math.radians(lat1)))


def find_data():
    for p in [HERE / "data" / "valmo_synthetic_orders.csv.gz", HERE / "data" / "valmo_synthetic_orders.csv",
              HERE / "valmo_synthetic_orders.csv.gz", HERE / "valmo_synthetic_orders.csv"]:
        if p.exists():
            return p
    found = sorted(HERE.rglob("valmo_synthetic_orders.csv*"))
    return found[0] if found else None


@st.cache_data
def load(path):
    df = pd.read_csv(path, dtype={"pincode": str}).sort_values(["order_date", "order_id"]).reset_index(drop=True)
    # Replay history: did this address already have a verified pin when the order left the hub?
    taps, status = {}, []
    for aid, outcome, lat, lon in zip(df.address_id, df.outcome, df.rider_tap_lat, df.rider_tap_lon):
        prior = taps.get(aid, [])
        ok = False
        if len(prior) >= 2:
            mlat, mlon = float(np.median([p[0] for p in prior])), float(np.median([p[1] for p in prior]))
            ok = sum(dist_m(p[0], p[1], mlat, mlon) <= VERIFY_RADIUS_M for p in prior) >= 2
        status.append("Verified pin" if ok else "No verified pin")
        if outcome == "Delivered":
            taps.setdefault(aid, []).append((lat, lon))
    df["pin_at_dispatch"] = status
    df["u"] = np.random.default_rng(7).random(len(df))
    df["v"] = np.random.default_rng(8).random(len(df))
    return df


DATA = find_data()
if DATA is None:
    st.error("Data file not found. Upload **valmo_synthetic_orders.csv.gz** into a folder called **data** next to app.py.")
    st.stop()
df = load(str(DATA))

# ───────────── controls ─────────────
with st.sidebar:
    st.header("Try it")
    pata_on = st.toggle("Valmo Pata switched on", value=True)
    share = st.slider("First-time customers who share their location", 0, 80, 30, 5, format="%d%%", disabled=not pata_on,
                      help="Asked once, inside the order-confirmation WhatsApp message. 0% = address graph alone.") / 100
    with st.expander("Assumption"):
        fix = st.slider("Address failures avoided when the rider has a pin", 50, 100, 90, 5, format="%d%%") / 100
    st.caption("Synthetic data calibrated to the Meesho case pack. Not real Meesho data.")

# ───────────── scenario ─────────────
addr_fail = (df.outcome == "RTO") & (df.rto_reason == "Address / wrong hub")
rescued = pd.Series(False, index=df.index)
if pata_on:
    rescued |= addr_fail & (df.pin_at_dispatch == "Verified pin") & (df.u < fix)
    rescued |= addr_fail & (df.first_time_address == "Yes") & (df.v < share) & (df.u < fix)

n = len(df)
rto0, saved = (df.outcome == "RTO").sum(), int(rescued.sum())
rto1 = rto0 - saved
cpd0 = df.total_logistics_cost_inr.sum() / (n - rto0)
cpd1 = (df.total_logistics_cost_inr.sum() - saved * REV) / (n - rto1)
annual_cr = saved / n * ANNUAL_SHIPMENTS * REV / 1e7

# ───────────── page ─────────────
st.title("What Valmo Pata is worth")
st.markdown("30,000 orders across three Kanpur hubs, built to match Meesho's numbers: **17% of parcels come back**, "
            "and **18% of those fail because of the address**. Switch Valmo Pata on and off in the sidebar.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Parcels that come back (RTO)", f"{rto1 / n:.1%}", f"{(rto1 - rto0) / n * 100:+.2f} points", delta_color="inverse")
c2.metric("Address failures avoided", f"{saved / max(addr_fail.sum(), 1):.0%}", f"{saved:,} parcels saved", delta_color="off")
c3.metric("Cost per delivered order", f"₹{cpd1:,.1f}", f"{cpd1 - cpd0:+.2f} ₹", delta_color="inverse")
c4.metric("Saved per year at Valmo scale", f"₹{annual_cr:,.0f} cr", "at 1.6 bn shipments a year", delta_color="off")

st.subheader("Where it helps")
view = df[(df.outcome == "RTO")].assign(status=np.where(rescued[df.outcome == "RTO"], "Saved by Valmo Pata", "Still returned"))
view["color"] = view.status.map({"Saved by Valmo Pata": [15, 160, 120, 255], "Still returned": [196, 18, 47, 150]})
view["radius"] = np.where(view.status == "Saved by Valmo Pata", 60, 35)
view = view.sort_values("status", ascending=False)   # draw saved (green) on top
st.pydeck_chart(pdk.Deck(
    layers=[pdk.Layer("ScatterplotLayer", data=view[["door_lat", "door_lon", "color", "radius", "status", "address_text", "rto_reason"]],
                      get_position=["door_lon", "door_lat"], get_fill_color="color", get_radius="radius",
                      radius_min_pixels=2, radius_max_pixels=9, pickable=True)],
    initial_view_state=pdk.ViewState(latitude=view.door_lat.mean(), longitude=view.door_lon.mean(), zoom=10.6),
    map_provider="carto", map_style="light",
    tooltip={"html": "<b>{status}</b><br/>{address_text}<br/>{rto_reason}", "style": {"fontSize": "12px"}}), height=460)
st.caption("Every dot is a parcel that came back. Green ones are address failures Valmo Pata would have prevented. Hover for the address as typed.")

st.subheader("Why the location request matters")
a = df[addr_fail]
first = (a.first_time_address == "Yes").mean()
ver = ((a.first_time_address == "No") & (a.pin_at_dispatch == "Verified pin")).mean()
k1, k2 = st.columns(2)
k1.metric("Address failures on a home's first order", f"{first:.0%}", "no rider has been there yet", delta_color="off")
k2.metric("Address failures where a verified pin already existed", f"{ver:.0%}", "what the address graph alone can fix", delta_color="off")
st.markdown(f"Most address failures happen **before any rider has visited the home**, so the graph can't help them yet. "
            f"Asking first-time customers to share their location once, in the confirmation message they already get, is what reaches them. "
            f"Move the slider to 0% to see the graph alone.")

with st.expander("About this data"):
    rate = lambda m: (df.loc[m, "outcome"] == "RTO").mean()
    checks = pd.DataFrame([
        ("COD share", (df.payment_mode == "COD").mean(), 0.80),
        ("RTO, COD / prepaid", f"{rate(df.payment_mode == 'COD'):.1%} / {rate(df.payment_mode == 'Prepaid'):.1%}", "20% / 5%"),
        ("RTO overall", rate(df.index == df.index), 0.17),
        ("RTO near / moderate / far from hub",
         " / ".join(f"{rate(df.distance_band == b):.1%}" for b in ["Near (~2 km)", "Moderate (~5 km)", "Far (10 km+)"]), "15% / 17% / 22%"),
    ], columns=["Number", "In the data", "Case pack"])
    checks["In the data"] = checks["In the data"].map(lambda x: f"{x:.1%}" if isinstance(x, float) else x)
    checks["Case pack"] = checks["Case pack"].map(lambda x: f"{x:.0%}" if isinstance(x, float) else x)
    st.dataframe(checks, hide_index=True, width="stretch")
    st.markdown("**Real:** DIGIPIN encoding, the pin-verification rule (two deliveries within 15 m), and the cost maths (₹50 forward, ₹120 reverse).  \n"
                "**Assumed:** first-time addresses fail more (23% vs 13%), rider GPS error about 9 m, and both sliders.  \n"
                "**A pilot would measure:** real GPS accuracy, the share of repeat addresses, and how many customers actually share a location.")
    st.download_button("Download the dataset (CSV)", df.drop(columns=["u", "v"]).to_csv(index=False), "valmo_synthetic_orders.csv", "text/csv")
