import sys
import os

# Add parent folder (SmartTrafficSystem) to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from utils import get_lane_counts, get_predicted_density, get_traffic_lights, check_emergency, get_lane_history, get_vehicle_positions
import time
import pandas as pd
import altair as alt

st.set_page_config(page_title="Smart Traffic Dashboard", layout="wide")
st.title("🚦 Smart Traffic Management Dashboard")

# Sidebar
st.sidebar.header("Settings")
refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 0.5, 5.0, 1.0)

while True:
    # Fetch live data
    lane_counts = get_lane_counts()
    predictions = get_predicted_density()
    lights = get_traffic_lights()
    emergency = check_emergency()
    lane_history = get_lane_history()
    vehicle_positions = get_vehicle_positions()

    # Layout
    col1, col2 = st.columns([2,1])

    # Column 1: Mini-map + Traffic Lights
    with col1:
        st.subheader("Intersection Mini-Map")
        st_canvas = st.empty()
        st_canvas.image("assets/road_layout.png")  # Optional: background road image
        # Draw vehicles as dots on a canvas or chart
        for v in vehicle_positions:
            st.write(f"Vehicle at ({v['x']}, {v['y']}), color={v['color']}")

        st.subheader("Traffic Lights")
        st.write(lights)

    # Column 2: Stats
    with col2:
        st.subheader("Lane Vehicle Counts")
        st.write(lane_counts)

        st.subheader("Predicted Density")
        st.write(predictions)

        if emergency:
            st.warning("🚨 Emergency vehicle detected! Prioritize lane.")

        st.subheader("Lane History")
        for dir, values in lane_history.items():
            df = pd.DataFrame({"time": range(len(values)), "count": values})
            chart = alt.Chart(df).mark_line().encode(
                x="time", y="count", color=alt.value("blue" if dir in ["N","S"] else "red")
            ).properties(title=f"Lane {dir} Count History")
            st.altair_chart(chart, use_container_width=True)

    time.sleep(refresh_rate)
    st.experimental_rerun()
