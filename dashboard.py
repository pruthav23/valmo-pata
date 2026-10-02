"""
Valmo Pata · address graph prototype (Meesho DICE S3, Team Prod Gods, IIT Kanpur)
Runs on the synthetic dataset calibrated to the case pack.  `streamlit run app.py`
"""
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pydeck as pdk
import altair as alt
import streamlit as st


FWD, REV = 50, 120            # case pack: forward cost per order, reverse cost per RTO
ANNUAL_SHIPMENTS = 1.6e9      # our deck (JM Financial / YourStory, Jan-26)
VERIFY_RADIUS_M = 15          # two taps within this distance = verified pin
M_LAT = 110850.0


def dist_m(lat1, lon1, lat2, lon2):
    return math.hypot((lat1 - lat2) * M_LAT, (lon1 - lon2) * 111320.0 * math.cos(math.radians(lat1)))


# ───────────────────────── data ─────────────────────────
HERE = Path(__file__).resolve().parent
CANDIDATES = [HERE / "data" / "valmo_synthetic_orders.csv.gz", HERE / "data" / "valmo_synthetic_orders.csv",
              HERE / "valmo_synthetic_orders.csv.gz", HERE / "valmo_synthetic_orders.csv"]


def find_data():
    for p in CANDIDATES:
        if p.exists():
            return p
    found = sorted(HERE.rglob("valmo_synthetic_orders.csv*"))   # anywhere in the repo
    return found[0] if found else None


@st.cache_data
def load(path):
    df = pd.read_csv(path, dtype={"pincode": str})
    df = df.sort_values(["order_date", "order_id"]).reset_index(drop=True)
    # Replay history: for each order, did its address already have a verified pin at dispatch?
    # A pin is verified once 2+ earlier DELIVERED taps at that address agree within 15 m.
    taps, status, n_prior = {}, [], []
    for aid, outcome, lat, lon in zip(df.address_id, df.outcome, df.rider_tap_lat, df.rider_tap_lon):
        prior = taps.get(aid, [])
        verified = False
        if len(prior) >= 2:
            mlat = float(np.median([p[0] for p in prior])); mlon = float(np.median([p[1] for p in prior]))
            verified = sum(dist_m(p[0], p[1], mlat, mlon) <= VERIFY_RADIUS_M for p in prior) >= 2
        status.append("Verified pin" if verified else ("Unconfirmed pin" if prior else "No pin yet"))
        n_prior.append(len(prior))
        if outcome == "Delivered":
            taps.setdefault(aid, []).append((lat, lon))
    df["pin_at_dispatch"] = status
    df["prior_delivered_taps"] = n_prior
    df["u"] = np.random.default_rng(7).random(len(df))   # fixed per-order draws so sliders move smoothly
    df["v"] = np.random.default_rng(8).random(len(df))
    return df


DATA = find_data()
if DATA is None:
    st.error("Data file not found. Upload **valmo_synthetic_orders.csv.gz** (or the .csv) into a folder called "
             "**data** in your GitHub repo, next to app.py.")
    st.caption("Files the app can see: " + ", ".join(sorted(p.name for p in HERE.iterdir())))
    st.stop()
df_all = load(str(DATA))

# ───────────────────────── sidebar ─────────────────────────
with st.sidebar:
    st.header("Controls")
    hub = st.selectbox("Hub", ["All hubs"] + sorted(df_all.hub_name.unique()))
    pata_on = st.toggle("Switch on Valmo Pata", value=True)
    st.caption("Riders see a verified pin before leaving the hub, for addresses where two earlier deliveries agree.")
    fix_rate = st.slider("Address failures avoided when a verified pin exists", 0, 100, 90, 5, format="%d%%",
                         disabled=not pata_on) / 100
    pin_drop_on = st.toggle("Also ask first-time customers to drop a pin", value=False, disabled=not pata_on,
                            help="Asked inside the Valmo Pakka WhatsApp confirmation, so no new step for the customer.")
    pin_drop = st.slider("First-time customers who share a pin", 0, 100, 30, 5, format="%d%%",
                         disabled=not (pata_on and pin_drop_on)) / 100
    st.divider()
    st.caption("Synthetic data calibrated to the Meesho DICE S3 case pack. Not real Meesho data. "
               "The sliders are assumptions, not measurements.")

df = df_all if hub == "All hubs" else df_all[df_all.hub_name == hub]

# ───────────────────────── scenario ─────────────────────────
addr_fail = (df.outcome == "RTO") & (df.rto_reason == "Address / wrong hub")
rescued = pd.Series(False, index=df.index)
if pata_on:
    rescued |= addr_fail & (df.pin_at_dispatch == "Verified pin") & (df.u < fix_rate)
    if pin_drop_on:
        rescued |= addr_fail & (df.first_time_address == "Yes") & (df.v < pin_drop) & (df.u < fix_rate)

n = len(df)
rto_before = (df.outcome == "RTO").sum()
rto_after = rto_before - rescued.sum()
addr_before, addr_after = addr_fail.sum(), addr_fail.sum() - rescued.sum()
cost_before = df.total_logistics_cost_inr.sum()
cost_after = cost_before - rescued.sum() * REV
cpd_before = cost_before / (n - rto_before)
cpd_after = cost_after / (n - rto_after)
saving_per_lakh = rescued.sum() * REV / n * 1e5
annual_cr = rescued.sum() / n * ANNUAL_SHIPMENTS * REV / 1e7

# ───────────────────────── header ─────────────────────────
st.title("Valmo Pata: every delivery teaches us where a home is")
st.markdown("When a rider taps **delivered**, their phone's GPS is saved as a DIGIPIN. Once two deliveries agree, "
            "the next parcel to that home leaves the hub with a **verified pin** instead of “मंदिर के पास”.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Overall RTO", f"{rto_after / n:.1%}", f"{(rto_after - rto_before) / n * 100:+.2f} pts", delta_color="inverse")
c2.metric("Address-related RTO", f"{addr_after / n:.2%}", f"{(addr_after - addr_before) / max(addr_before, 1):+.0%} of address failures",
          delta_color="inverse")
c3.metric("Cost per delivered order", f"₹{cpd_after:,.1f}", f"{cpd_after - cpd_before:+.2f} ₹ per order", delta_color="inverse")
c4.metric("Saved per 1 lakh orders", f"₹{saving_per_lakh:,.0f}", f"≈ ₹{annual_cr:,.0f} cr a year at Valmo scale",
          delta_color="off")

tab_map, tab_how, tab_why, tab_data = st.tabs(["Map", "How a pin gets verified", "Where address failures come from", "Data & caveats"])

# ───────────────────────── map ─────────────────────────
with tab_map:
    view = df.assign(status=np.where(rescued, "Rescued by Valmo Pata", np.where(df.outcome == "RTO", "RTO", "Delivered")))
    colors = {"Delivered": [120, 130, 135, 90], "RTO": [196, 18, 47, 200], "Rescued by Valmo Pata": [15, 160, 120, 255]}
    view["color"] = view.status.map(colors)
    view["radius"] = np.where(view.status == "Delivered", 25, 45)
    show = st.radio("Show", ["Only failures and rescues", "All orders"], horizontal=True, label_visibility="collapsed")
    if show != "All orders":
        view = view[view.status != "Delivered"]
    layer = pdk.Layer("ScatterplotLayer", data=view[["door_lat", "door_lon", "color", "radius", "status", "address_text",
                                                     "rto_reason", "door_digipin", "pin_at_dispatch", "hub_name"]],
                      get_position=["door_lon", "door_lat"], get_fill_color="color", get_radius="radius",
                      radius_min_pixels=1.5, radius_max_pixels=8, pickable=True)
    hubs = df_all.groupby("hub_name").apply(lambda g: pd.Series({
        "lat": g.door_lat.mean(), "lon": g.door_lon.mean()}), include_groups=False).reset_index()
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=view.door_lat.mean() if len(view) else 26.46,
                                         longitude=view.door_lon.mean() if len(view) else 80.33,
                                         zoom=10.5 if hub == "All hubs" else 11.5),
        map_provider="carto", map_style="light",
        tooltip={"html": "<b>{status}</b><br/>{address_text}<br/>{rto_reason}<br/>Door DIGIPIN {door_digipin}<br/>{pin_at_dispatch} at dispatch",
                 "style": {"fontSize": "12px"}}), height=520)
    st.caption("Grey: delivered · Red: returned (RTO) · Green: address failures Valmo Pata would have prevented. "
               "Hover a dot for the address as the customer typed it.")

# ───────────────────────── how it works ─────────────────────────
with tab_how:
    st.subheader("One address, delivery by delivery")
    counts = df.groupby("address_id").agg(n=("order_id", "size"), away=("rider_tap_type", lambda s: (s == "Away from door").any()))
    pool = counts[(counts.n >= 4)].sort_values(["away", "n"], ascending=False).index[:40]
    if len(pool) == 0:
        st.info("No address in this hub has enough repeat orders.")
    else:
        aid = st.selectbox("Pick an address with repeat orders", pool,
                           format_func=lambda a: f"{a} · {df.loc[df.address_id == a, 'address_text'].iloc[0][:60]}")
        hist = df[df.address_id == aid].copy()
        door_lat, door_lon = hist.door_lat.iloc[0], hist.door_lon.iloc[0]
        st.markdown(f"**Typed address:** {hist.address_text.iloc[0]}  \n**True door DIGIPIN:** `{hist.door_digipin.iloc[0]}`")
        left, right = st.columns([2, 3])
        with right:
            tbl = hist[["order_date", "outcome", "pin_at_dispatch", "rider_tap_type", "rider_tap_digipin", "tap_distance_from_door_m"]]
            tbl.columns = ["Date", "Outcome", "Pin at dispatch", "Where rider tapped", "Tap DIGIPIN", "Metres from door"]
            st.dataframe(tbl, hide_index=True, width="stretch")
            st.caption("Each tap lands in a different 4 m DIGIPIN square because phone GPS is off by several metres. "
                       "That's why we group taps by distance and only trust the pin once two agree.")
        with left:
            pts = hist.assign(label=[f"Order {i + 1}: {o}" for i, o in enumerate(hist.outcome)],
                              color=[[15, 120, 98, 230] if t == "At door" else [196, 18, 47, 230] for t in hist.rider_tap_type])
            door = pd.DataFrame([{"lat": door_lat, "lon": door_lon, "label": "True door"}])
            st.pydeck_chart(pdk.Deck(
                layers=[pdk.Layer("ScatterplotLayer", door, get_position=["lon", "lat"], get_fill_color=[230, 150, 20, 255],
                                  get_radius=3, pickable=True),
                        pdk.Layer("ScatterplotLayer", pts, get_position=["rider_tap_lon", "rider_tap_lat"], get_fill_color="color",
                                  get_radius=2, radius_min_pixels=5, pickable=True)],
                initial_view_state=pdk.ViewState(latitude=door_lat, longitude=door_lon, zoom=18),
                map_provider="carto", map_style="light", tooltip={"text": "{label}"}), height=380)
            st.caption("Orange: true door · Green: taps at the door · Red: taps away from the door (ignored).")

# ───────────────────────── why ─────────────────────────
with tab_why:
    st.subheader("Which address failures can Valmo Pata reach?")
    a = df[addr_fail].copy()
    a["group"] = np.where(a.first_time_address == "Yes", "First-time address",
                          np.where(a.pin_at_dispatch == "Verified pin", "Repeat, verified pin", "Repeat, no verified pin yet"))
    share = a.group.value_counts(normalize=True).reindex(["First-time address", "Repeat, no verified pin yet", "Repeat, verified pin"]).fillna(0)
    cols = st.columns(3)
    for col, (k, v) in zip(cols, share.items()):
        col.metric(k, f"{v:.0%}", help="Share of all address-related failures")
    st.markdown(
        f"Only the **{share['Repeat, verified pin']:.0%}** with a verified pin can be fixed by the address graph alone. "
        f"**{share['First-time address']:.0%}** happen on the first order to a home, before any rider has been there. "
        "That's why the pin request in the Valmo Pakka WhatsApp confirmation matters: it is the only way to reach them.")
    st.divider()
    def bars(series, order, color, title):
        d = series.reindex(order).rename("rate").reset_index()
        d.columns = ["group", "rate"]
        return (alt.Chart(d, title=title).mark_bar(color=color, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
                .encode(x=alt.X("group:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)),
                        y=alt.Y("rate:Q", title="RTO rate", axis=alt.Axis(format="%")),
                        tooltip=[alt.Tooltip("group:N", title=""), alt.Tooltip("rate:Q", format=".1%", title="RTO")])
                .properties(height=260))
    c1, c2 = st.columns(2)
    is_rto = df.outcome.eq("RTO")
    c1.altair_chart(bars(is_rto.groupby(df.address_quality).mean(), ["Complete", "Incomplete", "Landmark only"],
                         "#C4122F", "RTO rate by address quality"), width="stretch")
    c2.altair_chart(bars(is_rto.groupby(df.distance_band).mean(), ["Near (~2 km)", "Moderate (~5 km)", "Far (10 km+)"],
                         "#5B1A47", "RTO rate by distance from hub"), width="stretch")
    st.info(f"Ceiling check: address-related failures are **{addr_before / n * 100:.1f} points** of the "
            f"{rto_before / n:.1%} RTO. Even fixing every one of them leaves RTO at about {(rto_before - addr_before) / n:.1%}. "
            "The bigger causes, refusal and unavailability, are Valmo Pakka's job.")

# ───────────────────────── data & caveats ─────────────────────────
with tab_data:
    st.subheader("The data reproduces the case pack")
    rate = lambda m: (df_all.loc[m, "outcome"] == "RTO").mean()
    checks = pd.DataFrame([
        ("COD share", (df_all.payment_mode == "COD").mean(), 0.80),
        ("RTO, COD orders", rate(df_all.payment_mode == "COD"), 0.20),
        ("RTO, prepaid orders", rate(df_all.payment_mode == "Prepaid"), 0.05),
        ("RTO overall", rate(df_all.index == df_all.index), 0.17),
        ("RTO, near (~2 km)", rate(df_all.distance_band == "Near (~2 km)"), 0.15),
        ("RTO, moderate (~5 km)", rate(df_all.distance_band == "Moderate (~5 km)"), 0.17),
        ("RTO, far (10 km+)", rate(df_all.distance_band == "Far (10 km+)"), 0.22),
    ], columns=["Number", "In the data", "Case pack"])
    st.dataframe(checks.style.format({"In the data": "{:.1%}", "Case pack": "{:.0%}"}), hide_index=True, width="stretch")
    st.markdown(
        "**What is real:** the DIGIPIN encoding (India Post spec), the pin verification rule, and the cost maths "
        "(₹50 forward, ₹120 reverse).\n\n"
        "**What is assumed:** first-time addresses fail at 23% vs 13% for repeat ones; rider GPS is off by about 9 m; "
        "6% of delivered taps happen away from the door; and both sliders in the sidebar.\n\n"
        "**What a pilot would check:** real rider GPS accuracy at the delivered tap, the share of orders going to repeat "
        "addresses, and how many first-time customers actually share a pin.")
    with st.expander("Browse the orders"):
        st.dataframe(df.drop(columns=["u", "v"]).head(500), hide_index=True, width="stretch")
    st.download_button("Download the full dataset (CSV)", df_all.drop(columns=["u", "v"]).to_csv(index=False),
                       "valmo_synthetic_orders.csv", "text/csv")
