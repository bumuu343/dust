import streamlit as st
import pandas as pd
import numpy as np
import time

# ==========================================
# PAGE CONFIGURATION & CUSTOM CSS
# ==========================================
st.set_page_config(
    page_title="Mine Environment & Infrastructure Dashboard", 
    page_icon="⛏️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to make it look like a professional industrial dashboard
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #2c3e50; }
    .stAlert { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# HEADER SECTION
# ==========================================
st.title("⚙️ Mineral Technology Capstone Dashboard")
st.subheader("Open-Pit Mine: Environmental & Solar Infrastructure Monitoring")
st.markdown("Real-time telemetry for airborne particulate matter and photovoltaic efficiency.")
st.divider()

# ==========================================
# SIDEBAR: PRESENTER CONTROLS
# ==========================================
with st.sidebar:
    st.header("🎛️ Simulation Controls")
    st.markdown("Adjust parameters below to demonstrate system logic.")
    
    st.subheader("Environment")
    dust_density = st.slider("PM10 Dust Density (µg/m³)", min_value=0.0, max_value=500.0, value=85.0, step=5.0)
    ambient_light = st.slider("Ambient Solar Irradiance (%)", min_value=0.0, max_value=100.0, value=90.0, step=5.0)
    
    st.subheader("Hardware")
    solar_voltage = st.slider("Solar Panel Output (V)", min_value=0.0, max_value=12.0, value=11.8, step=0.1)

# ==========================================
# SYSTEM PARAMETERS
# ==========================================
DUST_WARNING_LEVEL = 150.0
DUST_DANGER_LEVEL = 300.0
BRIGHT_SUNLIGHT_THRESHOLD = 70.0
EXPECTED_MAX_VOLTAGE = 12.0
EFFICIENCY_DROP_ALERT = 0.60  # 60%

# ==========================================
# ROW 1: LIVE TELEMETRY METRICS
# ==========================================
st.markdown("### 📡 Live Telemetry")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Airborne Dust (PM)", value=f"{dust_density} µg/m³", delta="Optimal" if dust_density < DUST_WARNING_LEVEL else "Elevated", delta_color="inverse")
    st.progress(int((dust_density / 500) * 100))

with col2:
    st.metric(label="Solar Irradiance", value=f"{ambient_light} %", delta="High" if ambient_light >= 70 else "Low")
    st.progress(int(ambient_light))

with col3:
    efficiency = (solar_voltage / EXPECTED_MAX_VOLTAGE) * 100
    st.metric(label="Panel Output Voltage", value=f"{solar_voltage} V", delta=f"{efficiency:.1f}% Efficiency")
    st.progress(int(efficiency) if efficiency <= 100 else 100)

st.divider()

# ==========================================
# ROW 2: AUTOMATED DIAGNOSTICS & ALERTS
# ==========================================
st.markdown("### ⚠️ Automated Diagnostics")
status_col1, status_col2 = st.columns(2)

# --- 1. HUMAN SAFETY LOGIC ---
with status_col1:
    st.markdown("**Occupational Health & Safety (OHS)**")
    if dust_density >= DUST_DANGER_LEVEL:
        st.error("🚨 **CRITICAL HAZARD: Evacuation Protocol Initiated**\n\nParticulate matter exceeds safe thresholds. All personnel must evacuate the pit or equip heavy-duty respirators immediately.")
    elif dust_density >= DUST_WARNING_LEVEL:
        st.warning("⚠️ **WARNING: Elevated Particulates**\n\nAir quality is degrading. Mandate N95/P100 masks for all active surface workers.")
    else:
        st.success("✅ **Air Quality: Nominal**\n\nAtmospheric conditions are safe for standard mining operations.")

# --- 2. SOLAR INFRASTRUCTURE LOGIC ---
with status_col2:
    st.markdown("**Photovoltaic (PV) Maintenance**")
    if ambient_light >= BRIGHT_SUNLIGHT_THRESHOLD:
        current_efficiency = solar_voltage / EXPECTED_MAX_VOLTAGE
        
        if current_efficiency < EFFICIENCY_DROP_ALERT:
            st.error("🔧 **MAINTENANCE REQUIRED: Soiling Detected**\n\nHigh solar irradiance detected, but power output is critically low. Panels are heavily soiled by mining dust. Dispatch cleaning crew.")
        else:
            st.success("✅ **Hardware: Nominal**\n\nSolar panels are clean and operating at expected efficiency levels.")
    else:
        st.info("🌙 **Standby Mode**\n\nInsufficient solar irradiance to perform diagnostic efficiency tests.")

st.divider()

# ==========================================
# ROW 3: HISTORICAL DATA VISUALIZATION
# ==========================================
st.markdown("### 📊 24-Hour Trend Analysis (Simulated)")
# Generate a realistic looking trend graph for the presentation
chart_data = pd.DataFrame(
    np.random.randn(24, 2).cumsum(axis=0) * 10 + [50, 80],
    columns=['Average Dust Levels (µg/m³)', 'Solar Efficiency (%)']
)
st.line_chart(chart_data, use_container_width=True)