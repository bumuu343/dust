import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
import math
from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components
from fpdf import FPDF
import io
import base64
import googlemaps

# ==============================================================================
# 1. PAGE CONFIG & THEME
# ==============================================================================
st.set_page_config(
    page_title="SOLAVARIA | Command & Control",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS – Light & Vibrant, but unique
st.markdown("""
<style>
    /* Main background and text */
    .stApp {
        /* [EDIT 2] – Tukar background jadi warna nude profesional */
        background: linear-gradient(135deg, #faf0e6 0%, #fdfaf3 100%);
        font-family: 'Segoe UI', 'Inter', sans-serif;
    }
    /* Headers */
    h1, h2, h3, h4, h5 {
        color: #1e2a3e !important;
        font-weight: 600 !important;
        letter-spacing: -0.3px;
    }
    h1 {
        background: linear-gradient(120deg, #e83e8c, #6f42c1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    /* Cards and metrics */
    .stMetric {
        background-color: white;
        padding: 1.2rem;
        border-radius: 1.2rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.03), 0 2px 6px rgba(0,0,0,0.05);
        border: 1px solid rgba(232, 62, 140, 0.2);
        transition: all 0.2s;
    }
    .stMetric:hover {
        border-color: #e83e8c;
        box-shadow: 0 12px 28px rgba(232,62,140,0.1);
    }
    [data-testid="stMetricValue"] {
        color: #1e2a3e !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: #4a5b6e !important;
        font-weight: 500;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid rgba(232,62,140,0.2);
        box-shadow: 4px 0 12px rgba(0,0,0,0.02);
    }
    /* Buttons */
    .stButton button {
        background: linear-gradient(95deg, #e83e8c 0%, #6f42c1 100%);
        color: white;
        border: none;
        border-radius: 2rem;
        padding: 0.5rem 1.2rem;
        font-weight: 600;
        transition: 0.2s;
    }
    .stButton button:hover {
        transform: scale(1.02);
        box-shadow: 0 8px 18px rgba(232,62,140,0.3);
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
        background-color: white;
        padding: 0.5rem 1rem;
        border-radius: 3rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 2rem;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
        color: #4a5b6e;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(95deg, #e83e8c20, #6f42c120);
        color: #e83e8c;
    }
    /* Info/Warning boxes */
    .stAlert {
        border-radius: 1rem;
        border-left: 5px solid #e83e8c !important;
        background-color: #fff0f5 !important;
        color: #1e2a3e !important;
    }
    hr {
        margin: 1rem 0;
        border-color: #e0e4ec;
    }
    /* Image frame */
    .cad-frame {
        background: white;
        border-radius: 1.5rem;
        padding: 0.8rem;
        box-shadow: 0 12px 24px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Set Malaysia Timezone globally for the app
malaysia_tz = timezone(timedelta(hours=8))

# ==============================================================================
# 2. UTILITIES (Weather, Solar Position, PDF)
# ==============================================================================
@st.cache_data(ttl=600)
def get_weather_by_coords(lat, lon):
    """Fetch real-time weather based on coordinates"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        resp = requests.get(url, timeout=5)
        return resp.json()['current_weather']
    except:
        return None

@st.cache_data(ttl=3600)
def get_location_coords(query):
    """Smart Search engine for specific places like Google Maps"""
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
        headers = {'User-Agent': 'Solavaria_Dashboard/1.0'}
        resp = requests.get(url, headers=headers, timeout=10).json()
        if len(resp) > 0:
            data = resp[0]
            # Ambil nama pendek tempat tu
            place_name = data["display_name"].split(",")[0]
            return float(data["lat"]), float(data["lon"]), place_name
    except:
        pass
    return None, None, None

def compute_solar_position(lat=5.745, lon=101.865):
    now = datetime.now()
    hour = now.hour + now.minute/60
    day_of_year = now.timetuple().tm_yday
    dec = -23.45 * math.cos(math.radians(360/365 * (day_of_year + 10)))
    ha = math.radians(15 * (hour - 12))
    lat_rad = math.radians(lat)
    dec_rad = math.radians(dec)
    sin_alt = math.sin(lat_rad) * math.sin(dec_rad) + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha)
    elevation = math.degrees(math.asin(sin_alt))
    cos_az = (math.sin(dec_rad) - math.sin(lat_rad)*sin_alt) / (math.cos(lat_rad)*math.cos(math.radians(elevation)))
    cos_az = max(-1, min(1, cos_az))
    azimuth = math.degrees(math.acos(cos_az))
    if ha > 0:
        azimuth = 360 - azimuth
    return azimuth, elevation

def generate_pdf_report(dust_level, pm10, personnel_status, alert_msg, loss_rm):
    """Generate a downloadable PDF safety report"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(232, 62, 140)
    pdf.cell(0, 10, "SOLAVARIA PERSONAL SAFETY COMPLIANCE REPORT", ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    
    # Use MYT for PDF timestamp
    current_time_str = datetime.now(malaysia_tz).strftime('%Y-%m-%d %H:%M:%S')
    pdf.cell(0, 8, f"Date: {current_time_str} (MYT)", ln=True)
    pdf.cell(0, 8, f"Location: Jeli, Kelantan (5.7450, 101.8650)", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Dust & Air Quality", ln=True)
    pdf.set_font("Helvetica", "", 12)
    # Tukar • jadi -
    pdf.cell(0, 6, f"- Surface Occlusion: {dust_level:.1f}%", ln=True)
    pdf.cell(0, 6, f"- PM10 Concentration: {pm10:.1f} ug/m3", ln=True) 
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Personnel Safety Status", ln=True)
    pdf.set_font("Helvetica", "", 12)
    
    # Logic warna yang dah dibetulkan tadi
    if personnel_status != "NOMINAL":
        pdf.set_text_color(200, 0, 0)
    else:
        pdf.set_text_color(0, 150, 0)
        
    # Tukar • jadi -
    pdf.cell(0, 6, f"- Status: {personnel_status}", ln=True)
    pdf.set_text_color(0, 0, 0)
   # Logic warna yang dah dibetulkan tadi
    if personnel_status != "NOMINAL":
        pdf.set_text_color(200, 0, 0)
    else:
        pdf.set_text_color(0, 150, 0)
        
    # Tukar • jadi -
    pdf.cell(0, 6, f"- Status: {personnel_status}", ln=True)
    pdf.set_text_color(0, 0, 0)
    
    # BUANG EMOJI UNTUK PDF
    clean_alert = alert_msg.replace('✅', '').replace('🚨', '').replace('⚠️', '').strip()
    pdf.multi_cell(0, 6, f"- Alert: {clean_alert}")
    

    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Financial Impact", ln=True)
    pdf.set_font("Helvetica", "", 12)
    # Tukar • jadi -
    pdf.cell(0, 6, f"- Estimated daily revenue loss: RM {loss_rm:.2f}", ln=True)
    pdf.cell(0, 6, "- Early detection savings applied: See dashboard", ln=True)
    pdf.ln(8)
    
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "This report is system-generated and complies with ISO 45001 guidelines.", ln=True)
    pdf_output = pdf.output(dest='S').encode('latin1')
    return pdf_output# ==============================================================================
# 3. SESSION STATE INIT
# ==============================================================================
if 'sys_logs' not in st.session_state:
    dates = pd.date_range(end=datetime.now(), periods=24, freq='h')
    np.random.seed(42)
    st.session_state.sys_logs = pd.DataFrame({
        'Time': dates,
        'Irradiance': np.random.uniform(40, 95, 24),
        'Occlusion': np.random.uniform(20, 80, 24),
        'Voltage': np.random.uniform(8, 12, 24),
        'Power': np.random.uniform(30, 55, 24),
        'OHS_Status': np.random.choice(['NOMINAL', 'HAZARDOUS', 'EVACUATION'], 24)
    })
if 'alarm_active' not in st.session_state:
    st.session_state.alarm_active = False

# ==============================================================================
# 4. SIDEBAR CONTROLS
# ==============================================================================
with st.sidebar:
    st.image("https://i.pinimg.com/originals/18/35/0f/18350fe1cf8b43bb6eb823ba430f81d1.gif", width=80)
    st.markdown("## 🎛️ Operator Override")
    sim_ldr = st.slider("Photovoltaic Irradiance (%)", 0.0, 100.0, 88.0)
    sim_pm10 = st.slider("Atmospheric PM10 (µg/m³)", 0.0, 500.0, 110.0)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Log Current Reading", use_container_width=True):
            new_row = pd.DataFrame([{
                'Time': datetime.now(),
                'Irradiance': sim_ldr,
                'Occlusion': min(100.0, (sim_pm10 / 500.0) * 100 + np.random.uniform(0, 2)),
                'Voltage': 12.0 * (sim_ldr/100) * (1 - math.pow((min(100.0, (sim_pm10/500)*100)/100), 1.6)),
                'Power': 5.0 * 12.0 * (sim_ldr/100) * (1 - math.pow((min(100.0, (sim_pm10/500)*100)/100), 1.6)),
                'OHS_Status': "EVACUATION" if sim_pm10>=350 else ("HAZARDOUS" if sim_pm10>=150 else "NOMINAL")
            }])
            st.session_state.sys_logs = pd.concat([st.session_state.sys_logs, new_row], ignore_index=True)
            st.toast("Telemetry logged to ledger", icon="✅")
    with col2:
        if st.button("🔄 Reset Logs", use_container_width=True):
            st.session_state.sys_logs = st.session_state.sys_logs.iloc[0:0]
            st.rerun()
    
    st.markdown("---")
    st.caption("SOLAVARIA NODE v4.2 | Bright Edition")

# ==============================================================================
# 5. MAIN PHYSICS ENGINE
# ==============================================================================
occ_pct = min(100.0, (sim_pm10 / 500.0) * 100 + np.random.uniform(0, 1.5))
eff_factor = max(0.05, 1.0 - math.pow((occ_pct / 100.0), 1.6))
actual_v = (12.0 * (sim_ldr / 100.0)) * eff_factor
actual_w = actual_v * 5.0
efficiency = (actual_v / 12.0) * 100

potential_w = (12.0 * (sim_ldr/100.0)) * 5.0
loss_w = max(0, potential_w - actual_w)
daily_loss_rm = (loss_w * 24 / 1000) * 0.57  # RM per kWh

# OHS logic
if sim_pm10 >= 350:
    personnel_status = "EVACUATION"
    personnel_alert = "🚨 EVACUATE OPEN-PIT IMMEDIATELY"
elif sim_pm10 >= 150:
    personnel_status = "HAZARDOUS"
    personnel_alert = "⚠️ RESPIRATORS MANDATED"
else:
    personnel_status = "NOMINAL"
    personnel_alert = "✅ SAFE FOR OPERATIONS"

# Alarm trigger
if occ_pct >= 60 and not st.session_state.alarm_active:
    st.toast(f'⚠️ Dust level {occ_pct:.1f}% exceeds 60% threshold!', icon='🚨')
    st.session_state.alarm_active = True
elif occ_pct < 60:
    st.session_state.alarm_active = False

# ==============================================================================
# 6. HEADER
# ==============================================================================
# Use real Malaysian timezone logic
real_time_now = datetime.now(malaysia_tz)

col_h1, col_h2 = st.columns([1, 4])
with col_h1:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=70)
with col_h2:
    st.title("SOLAVARIA CENTRAL COMMAND")
    st.markdown(f"**NODE:** OP-JELI ALPHA | **SYSTEM TIME (MYT):** {real_time_now.strftime('%H:%M:%S %d-%b-%Y')}")
st.divider()

# ==============================================================================
# 7. TABS
# ==============================================================================
tab_exec, tab_tele, tab_geo, tab_roi, tab_audit = st.tabs(
    ["🚀 EXECUTIVE DASHBOARD", "📡 MISSION CRITICAL TELEMETRY", "🌍 GEOSPATIAL", "💰 ANALYTICS & ROI", "📋 AUDIT & COMPLIANCE"]
)

# ------------------------------------------------------------------------------
# TAB EXECUTIVE: Digital Twin + Live metrics
# ------------------------------------------------------------------------------
with tab_exec:
    col_a, col_b = st.columns([1.3, 1])
    with col_a:
        st.markdown("### 🛠️ DIGITAL TWIN – SOLIDWORKS ASSEMBLY")
        # Display the CAD image – replace with your actual file
        try:
            st.image("solavaria_cad.png", caption="Solavaria Miniature Node – Full Mechanical Assembly", use_container_width=True)
        except:
            st.warning("⚠️ Place 'solavaria_cad.png' in the app folder. Using placeholder.")
            st.image("https://placehold.co/800x500/f8f9ff/e83e8c?text=SOLAVARIA+CAD+MODEL", use_container_width=True)
        # Labeling with HTML tooltips
        st.markdown("""
        <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.5rem;">
            <span title="Generates 12V nominal" style="background:#f0e6ff; padding:0.2rem 1rem; border-radius:2rem;">🔋 Solar Panel</span>
            <span title="Tracks dust accumulation" style="background:#ffe6f0; padding:0.2rem 1rem; border-radius:2rem;">💨 PM10 Sensor</span>
            <span title="Stepper motor & shaft holder" style="background:#e6f7ff; padding:0.2rem 1rem; border-radius:2rem;">⚙️ Actuator Assembly</span>
            <span title="Arcylic protective plates" style="background:#f0fff0; padding:0.2rem 1rem; border-radius:2rem;">🛡️ Enclosure</span>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown("### ⚡ ASSET HEALTH")
        m1, m2 = st.columns(2)
        m1.metric("Output Voltage", f"{actual_v:.2f} V", f"{efficiency:.1f}% efficiency")
        m2.metric("Power Generation", f"{actual_w:.2f} W", f"-{loss_w:.1f} W loss", delta_color="inverse")

        # [EDIT 1] – Betulkan typo, tukar jadi "PERSONAL"
        st.markdown("### 👥 PERSONAL HEALTH & SAFETY")
        # Determine color and icon
        if personnel_status == "EVACUATION":
            bg_color = "#ffebee"
            border_color = "#d32f2f"
            icon = "☠️"
            status_text = "EVACUATION REQUIRED"
        elif personnel_status == "HAZARDOUS":
            bg_color = "#fff3e0"
            border_color = "#ff9800"
            icon = "😷"
            status_text = "HAZARDOUS – RESPIRATOR MANDATORY"
        else:
            bg_color = "#e8f5e9"
            border_color = "#4caf50"
            icon = "😊"
            status_text = "NOMINAL – SAFE FOR WORK"

        # Display big card
        pm10_percent = min(100, (sim_pm10 / 500) * 100)
        st.markdown(f"""
        <div style="background-color:{bg_color}; padding:1rem; border-radius:1rem; border-left:8px solid {border_color}; margin:0.5rem 0;">
            <div style="display:flex; align-items:center; gap:1rem;">
                <div style="font-size:3rem;">{icon}</div>
                <div>
                    <div style="font-size:1.8rem; font-weight:bold;">{status_text}</div>
                    <div style="font-size:1rem;">PM10 Concentration: <b>{sim_pm10:.1f} µg/m³</b></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Progress bar for PM10 exposure
        st.markdown("**Exposure Level:**")
        st.progress(int(pm10_percent))
        if sim_pm10 >= 150:
            st.warning("⚠️ **Safety Alert:** Prolonged exposure may cause respiratory issues. Use appropriate PPE.")
        if sim_pm10 >= 350:
            st.error("🚨 **CRITICAL:** Cease all outdoor activities immediately. Evacuate to shelter.")

        # [EDIT 3] – Enhancement: Trend analytics habuk/occlusion dalam historical data
        st.markdown("### 💨 Dust Sensor Analytics")
        if len(st.session_state.sys_logs) > 0:
            # Prepare sparkline data from Occlusion
            df_trend = st.session_state.sys_logs.copy().tail(12)
            # Create a small Plotly line chart (sparkline)
            fig_trend = go.Figure(go.Scatter(x=df_trend['Time'], y=df_trend['Occlusion'], mode='lines+markers', line_color='#e83e8c', marker_color='#6f42c1', name='Occlusion %'))
            fig_trend.update_layout(xaxis_title="Time", yaxis_title="Occlusion %", height=180, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(size=10))
            fig_trend.update_xaxes(showgrid=False, showticklabels=False)
            fig_trend.update_yaxes(showgrid=True, gridcolor='#e0e4ec')
            st.plotly_chart(fig_trend, use_container_width=True)
            # Add summary metrics
            c1, c2 = st.columns(2)
            c1.metric("Current Occlusion", f"{occ_pct:.1f}%")
            c2.metric("Avg. Occlusion (Past 12h)", f"{df_trend['Occlusion'].mean():.1f}%")
        else:
            st.info("Log data to see trends.")

        st.divider()
        # Diagnostic directive logic
        if occ_pct >= 60:
            st.error(f"🔴 **CRITICAL:** Surface occlusion {occ_pct:.1f}% – cleaning protocol required immediately.")
        else:
            st.success(f"✅ **NOMINAL:** Occlusion {occ_pct:.1f}% within safe limits.")

# ------------------------------------------------------------------------------
# TAB TELEMETRY: Heatmap (Efficiency by hour)
# ------------------------------------------------------------------------------
with tab_tele:
    st.markdown("## 📊 System Efficiency Heatmap")
    st.caption("Colour intensity represents efficiency (%) across different hours of the day. Log more data to enrich the heatmap.")
    if len(st.session_state.sys_logs) > 0:
        # Prepare data: extract hour and compute efficiency = (Voltage/12)*100
        df_heat = st.session_state.sys_logs.copy()
        df_heat['Hour'] = pd.to_datetime(df_heat['Time']).dt.hour
        df_heat['Efficiency'] = (df_heat['Voltage'] / 12.0) * 100
        # Pivot table
        pivot = df_heat.pivot_table(index='Hour', values='Efficiency', aggfunc='mean').fillna(0)
        # Create heatmap using plotly
        fig = go.Figure(data=go.Heatmap(
            z=[pivot['Efficiency'].tolist()],
            x=pivot.index.tolist(),
            y=['Efficiency %'],
            colorscale='Viridis',
            showscale=True,
            zmin=0, zmax=100,
            hovertemplate='Hour: %{x}<br>Efficiency: %{z:.1f}%<extra></extra>'
        ))
        fig.update_layout(title="Average Solar Efficiency by Hour of Day", xaxis_title="Hour (24h)", height=400, plot_bgcolor='white', paper_bgcolor='white', font=dict(color='#1e2a3e'))
        st.plotly_chart(fig, use_container_width=True)
        st.info("💡 Efficiency drops during early morning/late afternoon; dust accumulation reduces peak performance.")
    else:
        st.warning("No telemetry data yet. Use sidebar to **Log Current Reading** and build the heatmap.")

# ------------------------------------------------------------------------------
# TAB GEOSPATIAL (unchanged but fixed map placeholder)
# ------------------------------------------------------------------------------
with tab_geo:
    st.markdown("### 🔍 LOCATION OVERRIDE SYSTEM")
    search_col, info_col = st.columns([3, 1])
    
    with search_col:
        city_input = st.text_input("Enter tracking location (e.g., UMK Jeli, Kuala Lumpur, Johor Bahru):", value="UMK Jeli")
    
    # Smart Detection
