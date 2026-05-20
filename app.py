# -*- coding: utf-8 -*-
"""
app.py — Entry Point: Chọn vùng miền (Miền Bắc / Miền Nam) rồi gọi module tương ứng.
Hệ thống Đối Soát QC Cáp Quang — 2 Miền Độc Lập.
"""

import streamlit as st
import os
import threading
import time
from streamlit.runtime import Runtime

# =============================================================================
# RESOURCE MONITOR (auto-shutdown khi không có ai dùng)
# =============================================================================

def monitor_resource_usage():
    """Tự động tắt app sau 10s nếu không có tab trình duyệt nào đang kết nối."""
    def _check():
        time.sleep(20)
        inactive_count = 0
        while True:
            time.sleep(2)
            try:
                runtime = Runtime.instance()
                if runtime is None:
                    continue
                sessions = runtime.get_client_manager().list_sessions_data()
                if len(sessions) > 0:
                    inactive_count = 0
                else:
                    inactive_count += 2
                    if inactive_count >= 10:
                        os._exit(0)
            except Exception:
                pass
                
    if not any(t.name == "ResourceMonitor" for t in threading.enumerate()):
        t = threading.Thread(target=_check, name="ResourceMonitor", daemon=True)
        t.start()

monitor_resource_usage()

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Hệ thống Đối soát QC Cáp Quang",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# REGION SELECTOR
# =============================================================================

if 'region' not in st.session_state:
    st.session_state['region'] = None

def go_back_home():
    """Reset region và quay về trang chọn vùng."""
    st.session_state['region'] = None
    # Clear data_bucket khi chuyển vùng để không bị xung đột dữ liệu
    for key in ['data_bucket', 'cad_data', 'analysis_results', 'nav_state', 
                'recalculate_results', 'project_name', 'upload_session_id']:
        if key in st.session_state:
            del st.session_state[key]

# --- NHÁNH CHỌN VÙNG ---
if st.session_state['region'] is None:
    # Trang chọn vùng miền — 2 nút lớn
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        html, body { font-family: 'Inter', sans-serif; }
        .block-container {
            padding-top: 6rem !important;
            max-width: 900px !important;
            margin: auto;
        }
        [data-testid="stVerticalBlock"] > div {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        
        /* Style for Miền Bắc button */
        [data-testid="stHorizontalBlock"] > div:nth-child(1) button {
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%) !important;
            border-radius: 20px !important;
            border: none !important;
            box-shadow: 0 10px 40px rgba(59, 130, 246, 0.3) !important;
            height: 280px !important;
            transition: all 0.3s ease !important;
        }
        [data-testid="stHorizontalBlock"] > div:nth-child(1) button p {
            color: white !important;
            font-size: 2.8rem !important;
            font-weight: 800 !important;
            white-space: pre-wrap !important;
            line-height: 1.5 !important;
        }
        [data-testid="stHorizontalBlock"] > div:nth-child(1) button:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 50px rgba(59, 130, 246, 0.5) !important;
        }

        /* Style for Miền Nam button */
        [data-testid="stHorizontalBlock"] > div:nth-child(3) button {
            background: linear-gradient(135deg, #dc2626 0%, #f87171 100%) !important;
            border-radius: 20px !important;
            border: none !important;
            box-shadow: 0 10px 40px rgba(239, 68, 68, 0.3) !important;
            height: 280px !important;
            transition: all 0.3s ease !important;
        }
        [data-testid="stHorizontalBlock"] > div:nth-child(3) button p {
            color: white !important;
            font-size: 2.8rem !important;
            font-weight: 800 !important;
            white-space: pre-wrap !important;
            line-height: 1.5 !important;
        }
        [data-testid="stHorizontalBlock"] > div:nth-child(3) button:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 50px rgba(239, 68, 68, 0.5) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-size: 2.4rem; font-weight: 800; color: #1e3a8a; margin-bottom: 0.5rem;">
            ⚡ HỆ THỐNG ĐỐI SOÁT GPON
        </h1>
        <p style="font-size: 1.1rem; color: #64748b; font-weight: 400;">
            Chọn khu vực để bắt đầu đối soát nghiệm thu
        </p>
        <p style="font-size: 0.85rem; color: #94a3b8;">Copyright © by HungBV14</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_left, col_spacer, col_right = st.columns([1, 0.15, 1])
    
    with col_left:
        if st.button("🔵\nMIỀN BẮC", key="btn_mb", use_container_width=True):
            st.session_state['region'] = 'MB'
            st.rerun()
    
    with col_right:
        if st.button("🔴\nMIỀN NAM", key="btn_mn", use_container_width=True):
            st.session_state['region'] = 'MN'
            st.rerun()

# --- NHÁNH MIỀN BẮC ---
elif st.session_state['region'] == 'MB':
    import app_mb
    app_mb.main()

# --- NHÁNH MIỀN NAM ---
elif st.session_state['region'] == 'MN':
    import app_mn
    app_mn.main()
