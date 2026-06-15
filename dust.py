import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
import math
from datetime import datetime, timedelta, timezone
import base64
from fpdf import FPDF
import streamlit.components.v1 as components  # <--- INI YANG TERTINGGAL TADI!

# ==============================================================================
# 1. PAGE CONFIG & THEME
# ==============================================================================
st.set_page_config(
    page_title="SOLAVARIA | Command & Control",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #faf0e6 0%, #fdfaf3 100%);
        font-family: 'Segoe UI', 'Inter', sans-serif;
    }
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
    [data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid rgba(232,62,140,0.2);
        box-shadow: 4px 0 12px rgba(0,0,0,0.02);
    }
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
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

malaysia_tz = timezone(timedelta(hours=8))

# ==============================================================================
# 2. UTILITIES
# ==============================================================================
@st.cache_data(ttl=600)
def get_weather_by_coords(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        resp = requests.get(url, timeout=5)
        return resp.json()['current_weather']
    except:
        return None

@st.cache_data(ttl=3600)
def get_location_coords(query):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
        headers = {'User-Agent': 'Solavaria_Dashboard/1.0'}
        resp = requests.get(url, headers=headers, timeout=10).json()
        if len(resp) > 0:
            data = resp[0]
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
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(232, 62, 140)
    pdf.cell(0, 10, "SOLAVARIA PERSONAL SAFETY COMPLIANCE REPORT", ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    
    current_time_str = datetime.now(malaysia_tz).strftime('%Y-%m-%d %H:%M:%S')
    pdf.cell(0, 8, f"Date: {current_time_str} (MYT)", ln=True)
    pdf.cell(0, 8, f"Location: Jeli, Kelantan (5.7450, 101.8650)", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Dust & Air Quality", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 6, f"- Surface Occlusion: {dust_level:.1f}%", ln=True)
    pdf.cell(0, 6, f"- PM10 Concentration: {pm10:.1f} ug/m3", ln=True) 
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Personnel Safety Status", ln=True)
    pdf.set_font("Helvetica", "", 12)
    
    if personnel_status != "NOMINAL":
        pdf.set_text_color(200, 0, 0)
    else:
        pdf.set_text_color(0, 150, 0)
        
    pdf.cell(0, 6, f"- Status: {personnel_status}", ln=True)
    pdf.set_text_color(0, 0, 0)
    
    clean_alert = alert_msg.replace('✅', '').replace('🚨', '').replace('⚠️', '').strip()
    pdf.multi_cell(0, 6, f"- Alert: {clean_alert}")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Financial Impact", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 6, f"- Estimated daily revenue loss: RM {loss_rm:.2f}", ln=True)
    pdf.cell(0, 6, "- Early detection savings applied: See dashboard", ln=True)
    pdf.ln(8)
    
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "This report is system-generated and complies with ISO 45001 guidelines.", ln=True)
    
    try:
        pdf_output = pdf.output(dest='S').encode('latin1')
    except AttributeError:
        pdf_output = bytes(pdf.output())
        
    return pdf_output

# ==============================================================================
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
        if st.button("📝 Log Current Reading", width="stretch"):
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
        if st.button("🔄 Reset Logs", width="stretch"):
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
daily_loss_rm = (loss_w * 24 / 1000) * 0.57

if sim_pm10 >= 350:
    personnel_status = "EVACUATION"
    personnel_alert = "🚨 EVACUATE OPEN-PIT IMMEDIATELY"
elif sim_pm10 >= 150:
    personnel_status = "HAZARDOUS"
    personnel_alert = "⚠️ RESPIRATORS MANDATED"
else:
    personnel_status = "NOMINAL"
    personnel_alert = "✅ SAFE FOR OPERATIONS"

if occ_pct >= 60 and not st.session_state.alarm_active:
    st.toast(f'⚠️ Dust level {occ_pct:.1f}% exceeds 60% threshold!', icon='🚨')
    st.session_state.alarm_active = True
elif occ_pct < 60:
    st.session_state.alarm_active = False

# ==============================================================================
# 6. HEADER
# ==============================================================================
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
# TAB EXECUTIVE
# ------------------------------------------------------------------------------
with tab_exec:
    col_a, col_b = st.columns([1.3, 1])
    with col_a:
        st.markdown("### 🛠️ DIGITAL TWIN – SOLIDWORKS ASSEMBLY")
        try:
            st.image("solavaria_cad.png", caption="Solavaria Miniature Node – Full Mechanical Assembly", width="stretch")
        except:
            st.warning("⚠️ Place 'solavaria_cad.png' in the app folder. Using placeholder.")
            st.image("https://placehold.co/800x500/f8f9ff/e83e8c?text=SOLAVARIA+CAD+MODEL", width="stretch")
        st.markdown("""
        <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.5rem;">
            <span style="background:#f0e6ff; padding:0.2rem 1rem; border-radius:2rem;">🔋 Solar Panel</span>
            <span style="background:#ffe6f0; padding:0.2rem 1rem; border-radius:2rem;">💨 PM10 Sensor</span>
            <span style="background:#e6f7ff; padding:0.2rem 1rem; border-radius:2rem;">⚙️ Actuator Assembly</span>
            <span style="background:#f0fff0; padding:0.2rem 1rem; border-radius:2rem;">🛡️ Enclosure</span>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown("### ⚡ ASSET HEALTH")
        m1, m2 = st.columns(2)
        m1.metric("Output Voltage", f"{actual_v:.2f} V", f"{efficiency:.1f}% efficiency")
        m2.metric("Power Generation", f"{actual_w:.2f} W", f"-{loss_w:.1f} W loss", delta_color="inverse")

        st.markdown("### 👥 PERSONAL HEALTH & SAFETY")
        if personnel_status == "EVACUATION":
            bg_color, border_color, icon, status_text = "#ffebee", "#d32f2f", "☠️", "EVACUATION REQUIRED"
        elif personnel_status == "HAZARDOUS":
            bg_color, border_color, icon, status_text = "#fff3e0", "#ff9800", "😷", "HAZARDOUS (USE PPE)"
        else:
            bg_color, border_color, icon, status_text = "#e8f5e9", "#4caf50", "😊", "NOMINAL – SAFE"

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

        st.markdown("**Exposure Level:**")
        st.progress(int(pm10_percent))
        if sim_pm10 >= 150:
            st.warning("⚠️ **Safety Alert:** Prolonged exposure may cause respiratory issues. Use appropriate PPE.")
        if sim_pm10 >= 350:
            st.error("🚨 **CRITICAL:** Cease all outdoor activities immediately. Evacuate to shelter.")

        st.markdown("### 💨 Dust Sensor Analytics")
        if len(st.session_state.sys_logs) > 0:
            df_trend = st.session_state.sys_logs.copy().tail(12)
            fig_trend = go.Figure(go.Scatter(x=df_trend['Time'], y=df_trend['Occlusion'], mode='lines+markers', line_color='#e83e8c', marker_color='#6f42c1', name='Occlusion %'))
            fig_trend.update_layout(xaxis_title="Time", yaxis_title="Occlusion %", height=180, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(size=10))
            st.plotly_chart(fig_trend, width="stretch")
            c1, c2 = st.columns(2)
            c1.metric("Current Occlusion", f"{occ_pct:.1f}%")
            c2.metric("Avg. Occlusion (Past 12h)", f"{df_trend['Occlusion'].mean():.1f}%")
        else:
            st.info("Log data to see trends.")

        st.divider()
        if occ_pct >= 60:
            st.error(f"🔴 **CRITICAL:** Surface occlusion {occ_pct:.1f}% – cleaning protocol required immediately.")
        else:
            st.success(f"✅ **NOMINAL:** Occlusion {occ_pct:.1f}% within safe limits.")

# ------------------------------------------------------------------------------
# TAB TELEMETRY
# ------------------------------------------------------------------------------
with tab_tele:
    st.markdown("## 📊 System Efficiency Heatmap")
    st.caption("Colour intensity represents efficiency (%) across different hours of the day.")
    if len(st.session_state.sys_logs) > 0:
        df_heat = st.session_state.sys_logs.copy()
        df_heat['Hour'] = pd.to_datetime(df_heat['Time']).dt.hour
        df_heat['Efficiency'] = (df_heat['Voltage'] / 12.0) * 100
        pivot = df_heat.pivot_table(index='Hour', values='Efficiency', aggfunc='mean').fillna(0)
        fig = go.Figure(data=go.Heatmap(
            z=[pivot['Efficiency'].tolist()],
            x=pivot.index.tolist(),
            y=['Efficiency %'],
            colorscale='Viridis',
            showscale=True,
            zmin=0, zmax=100
        ))
        fig.update_layout(title="Average Solar Efficiency by Hour of Day", xaxis_title="Hour (24h)", height=400)
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("No telemetry data yet. Use sidebar to **Log Current Reading**.")

# ------------------------------------------------------------------------------
# TAB GEOSPATIAL (MAP & WEATHER FIX)
# ------------------------------------------------------------------------------
with tab_geo:
    st.markdown("### 🔍 LOCATION OVERRIDE SYSTEM")
    
    search_col, info_col = st.columns([3, 1])
    
    with search_col:
        city_input = st.text_input("Enter tracking location (e.g., UiTM Shah Alam, UMK Jeli, Kuala Lumpur):", value="UMK Jeli")
    
    lat, lon, display_name = get_location_coords(city_input)
    
    if lat and lon:
        with info_col:
            st.markdown(f"""
            <div style="background-color: #f1f3f9; padding: 0.6rem; border-radius: 0.5rem; border-left: 5px solid #e83e8c;">
                <small style="color: #6c757d; font-weight: bold;">📍 Active Coordinates:</small><br>
                <span style="font-size: 0.85rem; font-weight: 600; color: #1e2a3e;">{display_name.upper()}</span><br>
                <small style="color: #4a5b6e;">({lat:.4f}, {lon:.4f})</small>
            </div>
            """, unsafe_allow_html=True)
            
        st.divider()
        
        map_col, weather_col = st.columns([2.3, 1.7])
        
        with map_col:
            st.markdown(f"##### 🛰️ SATELLITE TOPOLOGY: {display_name.upper()}")
            map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
            st.map(map_data, zoom=14, width="stretch")
            
        with weather_col:
            st.markdown("##### 🌧️ REAL-TIME WEATHER RADAR")
            weather_data = get_weather_by_coords(lat, lon)
            
            if weather_data:
                w1, w2 = st.columns(2)
                with w1:
                    st.metric(label="Temperature", value=f"{weather_data['temperature']} °C")
                with w2:
                    st.metric(label="Wind Speed", value=f"{weather_data['windspeed']} km/h")
                
                # --- PETA KECIL ANIMASI CUACA (WINDY) ---
                windy_html = f"""<iframe width="100%" height="200" src="https://embed.windy.com/embed.html?type=map&location=coordinates&metricRain=mm&metricTemp=%C2%B0C&metricWind=km/h&zoom=10&overlay=wind&product=ecmwf&level=surface&lat={lat}&lon={lon}" frameborder="0" style="border-radius: 1rem; border: 1px solid #e9ecef; margin-top: 0.5rem;"></iframe>"""
                components.html(windy_html, height=210)
                
                st.markdown("##### ☀️ SOLAR POSITION")
                az, el = compute_solar_position(lat, lon)
                c_s1, c_s2 = st.columns(2)
                c_s1.metric("Azimuth", f"{az:.1f}°")
                c_s2.metric("Elevation", f"{el:.1f}°")
            else:
                st.warning("⚠️ Data cuaca tidak dapat dimuat turun buat masa ini.")
    else:
        st.error("⚠️ Lokasi tidak dijumpai. Sila masukkan nama tempat yang lebih spesifik.")

# ------------------------------------------------------------------------------
# TAB ANALYTICS & ROI
# ------------------------------------------------------------------------------
with tab_roi:
    st.markdown("## 💰 Financial & Operational Analytics")
    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("Energy Deficit", f"{loss_w:.2f} W", delta="Real-time loss")
    col_r2.metric("Daily Energy Loss", f"{(loss_w*24/1000):.2f} kWh")
    col_r3.metric("Projected Daily Revenue Loss", f"RM {daily_loss_rm:.2f}")
    
    if occ_pct >= 60:
        early_detection = True
        cleaning_cost, loss_if_ignored = 50, 200  
        savings = loss_if_ignored - cleaning_cost
        savings_text = f"RM {savings:.0f} (monthly)"
    else:
        early_detection = False
        savings, savings_text = 0, "RM 0"
    
    st.markdown("### 💡 Operational Cost Savings (Early Dust Detection)")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("Cleaning Cost (at 60% occlusion)", "RM 50")
        st.metric("Potential Monthly Loss if Ignored", "RM 200")
    with col_s2:
        st.metric("💰 Projected Monthly Savings", savings_text, delta="Smart Maintenance" if early_detection else "Not triggered")
        if early_detection: st.success("✅ Early detection active – cleaning recommended to avoid RM200 loss.")
        
    st.markdown("### 📈 Degradation Forecast (Next 7 Days)")
    forecast_days = np.arange(1, 8)
    predict_occ = np.clip(occ_pct + (forecast_days * (sim_pm10/50)), 0, 100)
    fig = go.Figure(go.Bar(x=[f"Day +{d}" for d in forecast_days], y=predict_occ, marker_color='#e83e8c', text=[f"{x:.0f}%" for x in predict_occ], textposition='auto'))
    fig.add_hline(y=60, line_dash="dash", line_color="#6f42c1", annotation_text="CLEANING TRIGGER")
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(color='#1e2a3e'), yaxis=dict(title="Predicted Occlusion %", range=[0, 100]))
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------------------
# TAB AUDIT & COMPLIANCE
# ------------------------------------------------------------------------------
with tab_audit:
    st.markdown("## 📄 Safety Compliance Reporting")
    st.caption("Generate an OHS report compliant with ISO 45001 standards.")
    
    col_p1, col_p2 = st.columns([1, 1])
    with col_p1:
        if st.button("📄 GENERATE OHS COMPLIANCE REPORT (PDF)", width="stretch"):
            pdf_bytes = generate_pdf_report(occ_pct, sim_pm10, personnel_status, personnel_alert, daily_loss_rm)
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="Solavaria_OHS_Report_{datetime.now(malaysia_tz).strftime("%Y%m%d")}.pdf">📥 Click here to download PDF report</a>'
            st.markdown(href, unsafe_allow_html=True)
            st.success("Report generated successfully!")
    with col_p2:
        st.info("Report includes: dust level, PM10, personnel status, financial loss estimate, and timestamp.")
    
    st.markdown("### 📋 Secure Telemetry Ledger (Last 10 records)")
    if len(st.session_state.sys_logs) > 0:
        st.dataframe(st.session_state.sys_logs.tail(10).sort_values('Time', ascending=False).style.format({
            'Voltage': '{:.2f}', 'Power': '{:.2f}', 'Occlusion': '{:.1f}%', 'Irradiance': '{:.1f}%'
        }), width="stretch")
    else:
        st.info("No logs recorded. Use the sidebar to log data.")
