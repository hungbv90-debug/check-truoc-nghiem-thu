# -*- coding: utf-8 -*-
"""
app_mn.py — Giao diện Streamlit Đối Soát Nghiệm Thu — MIỀN NAM.
Layout: New Sidebar Structure + Main Area Uploads + Discrepancy Tab.
"""

import streamlit as st
import pandas as pd
import os
import threading
from datetime import datetime
from io import BytesIO
import time
import importlib
import data_processor_mn as data_processor
import cad_processor_mn as cad_processor
import streamlit.components.v1 as components
# Force reload to pick up new methods if cached
importlib.reload(data_processor)
from data_processor_mn import QALogic
from streamlit.runtime import Runtime
import tempfile
import re

STYLING = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body { font-family: 'Inter', sans-serif; font-size: 16px; }
    
    /* Header */
    h1 { color: #1e3a8a; font-weight: 800; font-size: 2rem; margin-bottom: 0.5rem; }
    h2 { font-size: 1.5rem; color: #334155; }
    h3 { font-size: 1.25rem; font-weight: 700; color: #475569; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Logo / Title Area in Sidebar */
    .brand-logo {
        padding: 1rem 0;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Custom Radio Button as Navigation Menu */
    div[role="radiogroup"] label {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        transition: all 0.2s;
        border: 1px solid transparent;
        font-weight: 600;
        color: #64748b;
        background-color: transparent;
    }
    
    div[role="radiogroup"] label:hover {
        background-color: #f1f5f9;
        color: #334155;
    }
    
    /* Active State */
    div[role="radiogroup"] div[aria-checked="true"] + div label {
        background-color: #eff6ff !important;
        color: #2563eb !important;
        border: 1px solid #dbeafe;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    /* Upload Card Styles */
    .upload-card {
        background-color: white;
        border: 1px dashed #cbd5e1;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        transition: border 0.2s;
    }
    .upload-card:hover {
        border-color: #3b82f6;
        background-color: #f8fafc;
    }
    
    /* Table Overrides for Full Visibility */
    table {
        width: 100% !important;
        border-collapse: collapse;
        table-layout: auto !important;
    }
    th {
        background-color: #f8fafc !important;
        color: #475569 !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        vertical-align: middle !important;
        text-align: left !important;
        padding: 10px !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 10 !important;
    }
    td {
        vertical-align: middle !important;
        padding: 8px !important;
        text-align: left !important;
        border-bottom: 1px solid #e2e8f0;
    }
    
    /* Table Index Column (STT) */
    th[scope="row"], th.blank {
        width: 1% !important;
        white-space: nowrap !important;
        text-align: center !important;
    }
    
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* General Spacing & Typography */
    .block-container {
        padding-top: 4rem !important; /* Tăng padding để không bị che bởi header bar */
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }
    
    /* Reset max-width if necessary */
    /* Reduce spacing between elements globally */
    [data-testid="stVerticalBlock"] > div {
        margin-top: -0.5rem !important;
        padding-top: 0 !important;
    }
    
    /* Tighter dividers */
    hr {
        margin-top: 0.75rem !important;
        margin-bottom: 0.75rem !important;
        border: 0;
        border-top: 1px solid #e2e8f0 !important;
        opacity: 0.5;
    }
    
    /* Tighter Alert/Info boxes */
    .stAlert {
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
        padding: 0.5rem 1rem !important;
    }
    
    /* Correct header margins */
    h1, h2, h3 {
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* File uploader tightening */
    [data-testid="stFileUploader"] {
        padding-top: 0 !important;
        margin-top: -0.5rem !important;
    }
</style>
"""
st.markdown(STYLING, unsafe_allow_html=True)

# =============================================================================
# LOGIC & HELPERS
# =============================================================================

# @st.cache_resource (Removed to ensure live reload of logic changes)
def get_qa_logic():
    return QALogic()

# State Management
if 'data_bucket' not in st.session_state:
    st.session_state['data_bucket'] = {
        'map_d': {},
        'map_b': {},
        'logs': [],
        'has_data': False
    }
    st.session_state['project_name'] = ""
    st.session_state['analysis_results'] = {}
    st.session_state['recalculate_results'] = True

def process_files(files_design, files_bbnt):
    """Process uploaded files and update session state."""
    qa = get_qa_logic()
    map_d = {}
    map_b = {}
    logs = []
    
    # Capture Project Name: Prioritize BBNT (especially Vật tư), then Design
    p_name = ""
    all_files = (files_bbnt or []) + (files_design or [])
    
    # Priority 1: Find "BB Vật tư" (Material Handover Record)
    vattu_file = None
    for f in all_files:
        fn = f.name.lower()
        if any(kw in fn for kw in ['vat_tu', 'vattu', 'vt']) and 'bbnt' in fn:
            vattu_file = f
            break
            
    if vattu_file:
        try:
            # Extract characters before first underscore, as requested
            base_name = vattu_file.name.rsplit('.', 1)[0]
            parts = base_name.split('_')
            p_name = parts[0]
            
            # If the first part is just a number (e.g., "06_HNI..."), take the second part as the plan code
            if p_name.isdigit() and len(parts) > 1:
                p_name = parts[1]
        except: pass
        
    # Priority 2: Fallback to any other BBNT file if still no prefix or it's "Template"
    if not p_name or p_name.lower() == 'template':
        for f in all_files:
            if 'bbnt' in f.name.lower():
                try:
                    base_name = f.name.rsplit('.', 1)[0]
                    parts = base_name.split('_')
                    temp_name = parts[0]
                    if temp_name.isdigit() and len(parts) > 1: temp_name = parts[1]
                    
                    if temp_name and temp_name.lower() != 'template':
                        p_name = temp_name
                        break
                except: pass
                
    # Priority 3: Last fallback to any Design file
    if not p_name or p_name.lower() == 'template':
        for f in all_files:
            try:
                base_name = f.name.rsplit('.', 1)[0]
                parts = base_name.split('_')
                temp_name = parts[0]
                if temp_name.isdigit() and len(parts) > 1: temp_name = parts[1]
                
                if temp_name and temp_name.lower() != 'template':
                    p_name = temp_name
                    break
            except: pass
            
    # Priority 4: Final generic fallback if everything else is still "Template" or empty
    if not p_name or p_name.lower() == 'template':
        p_name = "BaoCao"

    if p_name:
        st.session_state['project_name'] = p_name
    
    # Helper to process list of files and distribute to correct maps
    def _proc_and_distribute(flist):
        logs = []
        if not flist: return logs
        for f in flist:
            try:
                f.seek(0)
                sheets_dict = qa.read_excel(f)
                
                if not sheets_dict:
                    logs.append(f"⚠️ {f.name}: TRỐNG/LỖI")
                    continue
                
                for sname, df in sheets_dict.items():
                    if df.empty: continue
                    ftype = qa.identify_file_type(df, filename=f.name, sheet_name=sname)
                    df.attrs['name'] = f"{f.name} ({sname})"
                    
                    msg = f"✅ {f.name} [{sname}] → {ftype}"
                    
                    # Phân phối vào đúng bucket dựa trên type
                    target_map = map_b # Mặc định là BBNT
                    if ftype in ['thiet_ke', 'Form_import', 'Form_import_cap']:
                        target_map = map_d
                    
                    if ftype in target_map:
                        target_map[ftype] = pd.concat([target_map[ftype], df], ignore_index=True).drop_duplicates()
                        msg += " (Gộp & Lọc trùng)"
                    else:
                        target_map[ftype] = df
                    logs.append(msg)
                    
            except Exception as e:
                logs.append(f"❌ {f.name}: {str(e)}")
        return logs

    all_uploaded = (files_design or []) + (files_bbnt or [])
    logs = _proc_and_distribute(all_uploaded)

    # --- TỰ ĐỘNG ĐỒNG BỘ PREFIX (BƯỚC ĐẦU TIÊN) ---
    # User Request: "Bổ sung thêm file BBNT hàn nối vào để phân tích để tránh trường hợp BBNT đối tượng không có"
    df_bbnt_dt = map_b.get('doi_tuong', pd.DataFrame())
    df_bbnt_han = map_b.get('han_noi', pd.DataFrame())
    
    if (not df_bbnt_dt.empty or not df_bbnt_han.empty) and map_d:
        for k in map_d:
            # Sync all Design-related files using both BBNT sources
            map_d[k] = qa.sync_design_prefixes(map_d[k], df_bbnt_dt, df_bbnt_han)
        logs.append("⚙️ Tự động đồng bộ Prefix từ BBNT (Đối tượng & Hàn nối) sang file Thiết kế/Import.")

    # Update Session State
    st.session_state['data_bucket']['map_d'] = map_d
    st.session_state['data_bucket']['map_b'] = map_b
    st.session_state['data_bucket']['logs'] = logs
    st.session_state['data_bucket']['has_data'] = bool(map_d or map_b)
    st.session_state['upload_session_id'] = str(int(time.time()))
    st.session_state['recalculate_results'] = True

def highlight_rows(row):
    """
    User Request: Không tô xanh/đỏ cả dòng, chỉ tô ô có giá trị. Cảnh báo màu vàng.
    Logic: 
    - ❌ -> Đỏ.
    - ⚠️ -> Vàng.
    - ✅ hoặc (Row OK and has value) -> Xanh.
    """
    styles = []
    status = str(row.get('Trạng thái Lỗi', ''))
    row_str = " ".join(row.astype(str))
    
    # Identify if the row is generally error-prone or success-prone
    is_err_row = '❌' in row_str or any(x in status for x in ['Lệch', 'Thiếu', 'Thừa', 'Cảnh báo', 'Quá tải', 'Lỗi'])
    is_ok_row = '✅' in row_str or 'Khớp' in status
    
    red_style = 'background-color: #fee2e2; color: #991b1b'    # Light Red
    yellow_style = 'background-color: #fef9c3; color: #854d0e' # Light Yellow (Warning)
    green_style = 'background-color: #dcfce7; color: #166534'  # Light Green
    
    colorable_cols = [
        "Vị trí",
        "Check Công suất/Mở port", 
        "Dung lượng (Thiết kế/Import)", 
        "Mã hộp (Thiết kế/Import)",
        "Dung lượng (TT/TK)", 
        "Loại (TT/TK)", 
        "C.dài thi công",
        "Dự toán tool/ Thiết kế", 
        "Trạng thái Lỗi"
    ]
    
    for col in row.index:
        col_name = str(col)
        val = str(row[col])
        style = ''
        
        if col_name in colorable_cols:
            if '❌' in val:
                style = red_style
            elif '⚠️' in val:
                style = yellow_style
            elif '✅' in val:
                style = green_style
            elif col_name == 'Trạng thái Lỗi':
                if is_err_row: 
                    if '⚠️' in val or 'Cảnh báo' in val: style = yellow_style
                    else: style = red_style
                elif is_ok_row: style = green_style
            elif val.strip() != '' and val.strip() != 'nan' and val.strip() != '-':
                style = green_style
                
        styles.append(style)
            
    return styles

def to_excel(df: pd.DataFrame, pre_rows: list = None) -> BytesIO:
    output = BytesIO()
    df_out = df.copy()
    for c in df_out.columns:
        if "SL" in c and df_out[c].dtype in ['float64', 'float32']:
            df_out[c] = df_out[c].round(1)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        start_row = 0
        if pre_rows:
            # Set up the sheet with pre-rows
            if 'Ket_qua' not in writer.book.sheetnames:
                writer.book.create_sheet('Ket_qua', 0)
            ws = writer.book['Ket_qua']
            for i, txt in enumerate(pre_rows):
                ws.cell(row=i+1, column=1, value=txt)
                start_row += 1
            writer.sheets['Ket_qua'] = ws
            
        df_out.to_excel(writer, index=False, sheet_name='Ket_qua', startrow=start_row)
        
        # Thêm các file thiết kế/import gốc nếu có
        bucket = st.session_state.get('data_bucket', {})
        map_d = bucket.get('map_d', {})
        
        if 'Form_import' in map_d and not map_d['Form_import'].empty:
            map_d['Form_import'].to_excel(writer, index=False, sheet_name='FormImport_Goc')
        if 'thiet_ke' in map_d and not map_d['thiet_ke'].empty:
            map_d['thiet_ke'].to_excel(writer, index=False, sheet_name='ThietKe_Goc')
            
    output.seek(0)
    return output

# Removed CSS logic for expanding sidebar

# =============================================================================
# MAIN LAYOUT
# =============================================================================

def main():
    # Guarantee Session State keys are fully initialized on every call (crucial when switching regions)
    if 'data_bucket' not in st.session_state:
        st.session_state['data_bucket'] = {
            'map_d': {},
            'map_b': {},
            'logs': [],
            'has_data': False
        }
    if 'project_name' not in st.session_state:
        st.session_state['project_name'] = ""
    if 'analysis_results' not in st.session_state:
        st.session_state['analysis_results'] = {}
    if 'recalculate_results' not in st.session_state:
        st.session_state['recalculate_results'] = True

    with st.sidebar:
        # Region indicator + Back button
        col_back, col_badge = st.columns([1, 2])
        with col_back:
            if st.button("◀ Về", key="back_home_mn", use_container_width=True):
                st.session_state['region'] = None
                for key in ['data_bucket', 'cad_data', 'analysis_results', 'nav_state',
                            'recalculate_results', 'project_name', 'upload_session_id']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        with col_badge:
            st.markdown('<div style="background:linear-gradient(135deg,#dc2626,#f87171);color:white;padding:6px 12px;border-radius:8px;text-align:center;font-weight:700;font-size:0.85rem;">🔴 MIỀN NAM</div>', unsafe_allow_html=True)
        
        # Custom Logo Area
        st.markdown("""
        <div class="brand-logo">
            <h2 style="margin:0; color:#3b82f6;">⚡ PHÂN TÍCH ĐỐI SOÁT NGHIỆM THU</h2>
            <p style="font-size:0.8rem; color:#64748b;">Copyright © by HungBV14</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        if 'nav_state' not in st.session_state:
            st.session_state['nav_state'] = "Nhật ký & File"
            
        # Đồng bộ hóa ngược từ nav_state vào radio_nav TRƯỚC khi radio widget được vẽ
        st.session_state['radio_nav'] = st.session_state['nav_state']
            
        def on_nav_change():
            st.session_state['nav_state'] = st.session_state['radio_nav']
            # Reset sync flags and clear old bridge data when navigation occurs
            st.session_state['_notes_auto_synced'] = False
            st.session_state['_sai_lech_auto_synced'] = False
            st.session_state['_tc_sai_lech_synced'] = False
            
            # Quan trọng: Xóa dữ liệu cũ trong bridge & cả Widget state để ép JS đồng bộ lại dữ liệu mới nhất
            st.session_state['_user_notes_data'] = ''
            st.session_state['_sync_bridge_data'] = ''
            st.session_state['notes_bridge_input'] = ''
            st.session_state['sync_bridge_input'] = ''
            
            # Force result refresh to use updated notes
            st.session_state['recalculate_results'] = True
            
        nav_opts = ["Nhật ký & File", "Kết quả phân tích", "Số liệu sai lệch"]
        try:
            cur_idx = nav_opts.index(st.session_state['nav_state'])
        except ValueError:
            cur_idx = 0
            
        st.radio(
            "Menu",
            nav_opts,
            key="radio_nav",
            on_change=on_nav_change,
            label_visibility="collapsed"
        )
        nav = st.session_state['nav_state']
        
        st.markdown("---")
        
        # --- SIDEBAR SYNC BRIDGE (Always runs on every page) ---
        upload_id = st.session_state.get('upload_session_id', st.session_state['data_bucket'].get('upload_session_id', 'default_session_id'))
        
        # Hidden text_input to receive data from JS (hidden via CSS)
        st.markdown('<style>div.sync-bridge-wrapper { position: absolute; opacity: 0; height: 0; overflow: hidden; pointer-events: none; } div:has(> div > input[aria-label="DataSync_Bridge"]) { position: absolute; opacity: 0; height: 0; overflow: hidden; pointer-events: none; }</style>', unsafe_allow_html=True)
        sync_bridge_val = st.text_input("DataSync_Bridge", key="sync_bridge_input", label_visibility="collapsed")
        
        # Bridge cho Ghi chú nhập liệu từ các tab
        st.markdown('<style>div:has(> div > input[aria-label="GhiChu_Bridge"]) { position: absolute; opacity: 0; height: 0; overflow: hidden; pointer-events: none; }</style>', unsafe_allow_html=True)
        notes_bridge_val = st.text_input("GhiChu_Bridge", key="notes_bridge_input", label_visibility="collapsed")
        
        # Bridge cho Hàn nối Highlights
        st.markdown('<style>div:has(> div > input[aria-label="HN_Bridge"]) { position: absolute; opacity: 0; height: 0; overflow: hidden; pointer-events: none; }</style>', unsafe_allow_html=True)
        hn_hl_bridge_val = st.text_input("HN_Bridge", key="hn_bridge_input", label_visibility="collapsed")
        
        # Store bridge values in session_state for use on all pages
        if sync_bridge_val and len(sync_bridge_val) > 2:
            st.session_state['_sync_bridge_data'] = sync_bridge_val
        if notes_bridge_val and len(notes_bridge_val) > 2:
            st.session_state['_user_notes_data'] = notes_bridge_val
        if hn_hl_bridge_val and len(hn_hl_bridge_val) > 2:
            st.session_state['_hn_hl_data'] = hn_hl_bridge_val

    # --- GLOBAL CONSTANTS & VALIDATION ---
    REQUIRED_TYPES = {
        'Form_import': 'Form Import Đối tượng',
        'Form_import_cap': 'Form Import Cáp',
        'thiet_ke': 'Thiết kế',
        'doi_tuong': 'BBNT Đối tượng',
        'TUYEN_CAP': 'BBNT Tuyến cáp',
        'han_noi': 'BBNT Hàn nối',
        'vat_tu': 'BBNT Vật tư'
    }
    
    bucket = st.session_state['data_bucket']
    map_d = bucket['map_d']
    map_b = bucket['map_b']
    
    # Check what we have
    present_types = set(map_d.keys()) | set(map_b.keys())
    missing_types = [REQUIRED_TYPES[k] for k in REQUIRED_TYPES if k not in present_types]
    is_fully_loaded = len(missing_types) == 0
    is_any_loaded = len(present_types) > 0

    # Auto-collapse sidebar removed per user request

    # --- PAGE 1: IMPORT DỮ LIỆU ---
    if nav == "Nhật ký & File":
        st.title("📂 Import Dữ Liệu")
        st.markdown("Tải lên các file Thiết kế và Biên bản nghiệm thu để bắt đầu đối soát.")
        
        # --- TEMPLATE DOWNLOAD SECTION (COLLAPSIBLE) ---
        with st.expander("📥 Tải Template mẫu", expanded=False):
            t_col_main, t_col_empty = st.columns([1, 1])
            with t_col_main:
                # File gộp mới
                template_combined = "Templates/01_thiet_ke_import_MN.xlsx"
                if os.path.exists(template_combined):
                    with open(template_combined, "rb") as f:
                        st.download_button(
                            label="📄 Template Thiết kế & Import",
                            data=f,
                            file_name="Template_Thiet_Ke_Import.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else: 
                    st.error("⚠️ Lỗi: Không tìm thấy file Template gộp trong thư mục Templates")
            
            st.markdown("<br>", unsafe_allow_html=True)
            t_bbnt1, t_bbnt2, t_bbnt3, t_bbnt4 = st.columns(4)
            bbnt_templates = [
                ("03_HNI.I.M.PP.181225.37_BBNT_DT.xlsx", "📄 BBNT Đối tượng", "Template_BBNT_DoiTuong.xlsx"),
                ("05_HNI.I.M.PP.181225.37_BBNT_TuyenCap.xlsx", "📄 BBNT Tuyến cáp", "Template_BBNT_TuyenCap.xlsx"),
                ("04_HNI.I.M.PP.181225.37_BBNT_HanNoi.xlsx", "📄 BBNT Hàn nối", "Template_BBNT_HanNoi.xlsx"),
                ("06_HNI.I.M.PP.181225.37_BBNT_VatTu.xlsx", "📄 BBNT Vật tư", "Template_BBNT_VatTu.xlsx")
            ]
            cols_bbnt = [t_bbnt1, t_bbnt2, t_bbnt3, t_bbnt4]
            for i, (fname, label, outname) in enumerate(bbnt_templates):
                with cols_bbnt[i]:
                    path = os.path.join("Templates", fname)
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            st.download_button(label=label, data=f, file_name=outname, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

        st.divider()
        
        st.info("🔹 Vui lòng tải lên toàn bộ file Thiết kế (FormImport, Bản vẽ...) và file BBNT (Đối tượng, Cáp, Hàn, Vật tư)...")
        u_all_files = st.file_uploader(
            "Kéo thả tất cả các file vào đây",
            type=['xls', 'xlsx', 'dxf'],
            accept_multiple_files=True,
            key='main_u_all'
        )
            
        # Processing Trigger with Progress Bar
        if u_all_files:
            progress_bar = st.progress(0, text="⏳ Bắt đầu xử lý...")
            time.sleep(0.05)
            
            f_d = []
            f_b = []
            # --- FILTER DUPLICATES BY FILENAME (UI FIX) ---
            unique_files = {}
            has_dupes = False
            cad_file = None
            for f in u_all_files:
                if f.name.lower().endswith('.dxf'):
                    cad_file = f
                elif f.name in unique_files:
                    has_dupes = True
                else:
                    unique_files[f.name] = f
            filtered_files = list(unique_files.values())
            
            if has_dupes:
                st.warning("⚠️ Đã phát hiện một số file trùng tên. Hệ thống tự động lọc và chỉ giữ lại 1 bản cho mỗi tên file.")

            for f in filtered_files:
                # Không phân loại cứng dựa trên tên nữa, cho vào một rổ để đọc nội dung
                f_d.append(f)
            
            if cad_file:
                progress_bar.progress(5, text="⏳ Xử lý bản vẽ CAD...")
                try: cad_file.seek(0)
                except: pass
                with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
                    tmp.write(cad_file.read())
                    tmp_path = tmp.name
                st.session_state['cad_data'] = cad_processor.extract_gpon_topology(tmp_path)
                try: os.remove(tmp_path)
                except: pass

            progress_bar.progress(10, text="⏳ 10% — Phân loại file...")
            time.sleep(0.05)
            
            process_files(f_d, f_b)
            
            progress_bar.progress(50, text="⏳ 50% — Đọc file xong, bắt đầu phân tích...")
            time.sleep(0.05)
            
            # --- SOFT VALIDATION BEFORE RERUN ---
            p_types = set(st.session_state['data_bucket']['map_d'].keys()) | set(st.session_state['data_bucket']['map_b'].keys())
            
            if p_types:
                progress_bar.progress(100, text="✅ Đã tải file! Đang chuyển trang...")
                time.sleep(0.5)
                st.session_state['nav_state'] = "Kết quả phân tích"
                st.session_state['auto_download'] = True
                st.rerun()
            else:
                progress_bar.empty()
                st.error("⚠️ Không nhận diện được file nào. Vui lòng kiểm tra lại file upload.")
            
        # Show Status Board for 6 Required Files
        bucket = st.session_state['data_bucket']
        st.divider()
        col_status, col_logs = st.columns([1, 1.3])
        
        with col_status:
            st.subheader("📊 Trạng thái Hồ sơ (Cần đủ 6 file)")
            s_cols = st.columns(2)
            for i, (k, label) in enumerate(REQUIRED_TYPES.items()):
                with s_cols[i % 2]:
                    is_ok = k in present_types
                    if is_ok:
                        st.success(f"✅ {label}")
                    else:
                        st.warning(f"❌ {label}")
        
        with col_logs:
            if bucket['logs']:
                st.subheader("📋 Nhật ký Xử lý Chi tiết")
                # Using a container with scrolling for logs if they get long
                with st.container(height=320, border=False):
                    for l in bucket['logs']:
                        if "✅" in l: st.success(l)
                        elif "❌" in l: st.error(l)
                        else: st.warning(l)
        
    # --- PREPARE DATA FOR ANALYSIS ---
    qa = get_qa_logic()
    
    # Retrieve DFs
    df_std_tk = map_d.get('thiet_ke', pd.DataFrame())
    df_imp = map_d.get('Form_import', map_d.get('doi_tuong', pd.DataFrame()))
    df_imp_cap = map_d.get('Form_import_cap', pd.DataFrame())
    
    df_tk_cap = map_d.get('TUYEN_CAP', df_std_tk if not df_std_tk.empty else pd.DataFrame())
    df_tk_han = map_d.get('han_noi', df_std_tk if not df_std_tk.empty else pd.DataFrame())
    # Correct fallback logic for han/cap if empty
    if df_tk_han.empty and not df_tk_cap.empty: df_tk_han = df_tk_cap
    
    df_tk_vt = map_d.get('vat_tu', df_std_tk if not df_std_tk.empty else pd.DataFrame())

    df_bbnt_dt = map_b.get('doi_tuong', pd.DataFrame())
    df_bbnt_cap = map_b.get('TUYEN_CAP', pd.DataFrame())
    df_bbnt_han = map_b.get('han_noi', pd.DataFrame())
    df_bbnt_vt = map_b.get('vat_tu', pd.DataFrame())

    all_errors, errors_dict = [], {}
    
    # --- PERFORMANCE OPTIMIZATION: CACHE ANALYSIS RESULTS ---
    if is_any_loaded:
        if st.session_state.get('recalculate_results', True):
            # Calculate Results only if key files are present
            cad_data = st.session_state.get('cad_data', {})
            res_doi_tuong = qa.check_doi_tuong(df_imp, df_bbnt_dt, df_std_tk, cad_data=cad_data) if 'doi_tuong' in present_types else pd.DataFrame()
            res_tuyen_cap = qa.check_tuyen_cap(df_tk_cap, df_bbnt_cap, df_imp_cap) if 'TUYEN_CAP' in present_types else pd.DataFrame()
            res_han_noi = qa.check_han_noi(df_tk_han, df_bbnt_han, df_imp) if 'han_noi' in present_types else pd.DataFrame()
            res_vat_tu = qa.check_vat_tu(df_bbnt_vt, df_bbnt_dt, df_bbnt_cap) if 'vat_tu' in present_types else pd.DataFrame()
            res_design_cap = qa.check_design_capacity(df_imp, df_std_tk) if 'Form_import' in present_types and 'thiet_ke' in present_types else pd.DataFrame()
            
            st.session_state['analysis_results'] = {
                'doi_tuong': res_doi_tuong,
                'tuyen_cap': res_tuyen_cap,
                'han_noi': res_han_noi,
                'vat_tu': res_vat_tu,
                'design_cap': res_design_cap
            }
            st.session_state['recalculate_results'] = False
        else:
            res_doi_tuong = st.session_state['analysis_results'].get('doi_tuong', pd.DataFrame())
            res_tuyen_cap = st.session_state['analysis_results'].get('tuyen_cap', pd.DataFrame())
            res_han_noi = st.session_state['analysis_results'].get('han_noi', pd.DataFrame())
            res_vat_tu = st.session_state['analysis_results'].get('vat_tu', pd.DataFrame())
            res_design_cap = st.session_state['analysis_results'].get('design_cap', pd.DataFrame())

        # --- PROCESS CAD DATA IF AVAILABLE ---
        cad_data = st.session_state.get('cad_data', {})
        cad_map = {str(k).upper(): v for k, v in cad_data.items()} if cad_data else {}
        
        # Avoid mutating the pristine cached DataFrames from st.session_state
        if not res_doi_tuong.empty:
            res_doi_tuong = res_doi_tuong.copy()
            
        if not res_tuyen_cap.empty:
            res_tuyen_cap = res_tuyen_cap.copy()
            
            # 1. Update Tuyến cáp
            diem_cuoi_col = next((c for c in res_tuyen_cap.columns if c.lower() == 'điểm cuối (key)' or c.lower() == 'điểm cuối'), None)
            diem_dau_col = next((c for c in res_tuyen_cap.columns if c.lower() == 'điểm đầu'), None)
            
            if diem_cuoi_col and diem_dau_col:
                idx = res_tuyen_cap.columns.get_loc(diem_dau_col)
                def get_cad_diem_dau(key):
                    if not cad_map: return ""
                    if pd.isna(key): return ""
                    key_str = str(key).strip().upper()
                    
                    if key_str in cad_map:
                        return cad_map[key_str]['parent']
                    prefix_key = key_str.split('/')[0] if '/' in key_str else key_str
                    if prefix_key in cad_map:
                        return cad_map[prefix_key]['parent']
                        
                    # Extremely robust regex-based key lookup (works for HNI570.0379, HNIP570.0379, P570.0379, etc.)
                    match = re.search(r'P?\d{2,4}\.\d{4}', key_str)
                    if match:
                        core_key = match.group(0)
                        if not core_key.startswith('P'):
                            core_key = 'P' + core_key
                        
                        suffix = ""
                        if '/' in key_str:
                            suffix = '/' + key_str.split('/')[-1]
                            
                        k1 = core_key + suffix
                        if k1 in cad_map: return cad_map[k1]['parent']
                        
                        k2 = core_key
                        if k2 in cad_map: return cad_map[k2]['parent']
                    return ""
                
                if 'Điểm đầu cad' not in res_tuyen_cap.columns:
                    res_tuyen_cap.insert(idx + 1, 'Điểm đầu cad', res_tuyen_cap[diem_cuoi_col].apply(get_cad_diem_dau))
                
                # --- UPDATE PARENTS RECONCILIATION ---
                new_diem_dau = []
                new_cad_diem_dau = []
                new_chi_tiet = []
                new_trang_thai = []
                
                for _, row in res_tuyen_cap.iterrows():
                    diem_dau_val = str(row.get(diem_dau_col, "")).strip()
                    cad_val = str(row.get('Điểm đầu cad', "")).strip()
                    chi_tiet_val = str(row.get('Chi tiết', "")).strip()
                    trang_thai_val = str(row.get('Trạng thái Lỗi', "")).strip()
                    
                    if diem_dau_val.lower() == 'nan': diem_dau_val = ""
                    if cad_val.lower() == 'nan': cad_val = ""
                    if chi_tiet_val.lower() == 'nan': chi_tiet_val = ""
                    if trang_thai_val.lower() == 'nan': trang_thai_val = ""
                    
                    if not cad_val:
                        new_diem_dau.append(diem_dau_val)
                        new_cad_diem_dau.append(cad_val)
                        new_chi_tiet.append(chi_tiet_val)
                        new_trang_thai.append(trang_thai_val)
                        continue
                    
                    def get_p_val(val):
                        val_str = str(val).strip().upper()
                        p_idx = val_str.find('P')
                        if p_idx != -1:
                            return val_str[p_idx:]
                        return val_str
                        
                    p_dau = get_p_val(diem_dau_val)
                    p_cad = get_p_val(cad_val)
                    
                    prefix_dau = p_dau.split('/')[0] if '/' in p_dau else p_dau
                    prefix_cad = p_cad.split('/')[0] if '/' in p_cad else p_cad
                    
                    is_match = (prefix_dau == prefix_cad)
                    
                    # Check conflict flag
                    conflict_val = False
                    key_for_conflict = str(row.get(diem_cuoi_col, "")).strip().upper()
                    if cad_map:
                        k_c = None
                        c_match = re.search(r'P?\d{2,4}\.\d{4}', key_for_conflict)
                        if c_match:
                            c_core = c_match.group(0)
                            if not c_core.startswith('P'):
                                c_core = 'P' + c_core
                            suffix_c = ""
                            if '/' in key_for_conflict:
                                suffix_c = '/' + key_for_conflict.split('/')[-1]
                            k_c = c_core + suffix_c
                            
                        if k_c:
                            if k_c in cad_map:
                                conflict_val = cad_map[k_c].get('conflict', False)
                            else:
                                prefix_c = k_c.split('/')[0] if '/' in k_c else k_c
                                if prefix_c in cad_map:
                                    conflict_val = cad_map[prefix_c].get('conflict', False)
                    
                    if is_match:
                        new_diem_dau.append(diem_dau_val)
                        new_cad_diem_dau.append(f"✅ {cad_val}" if not cad_val.startswith('✅') else cad_val)
                        
                        if conflict_val:
                            geom_p = "Không tìm thấy"
                            if k_c in cad_map:
                                geom_p = cad_map[k_c].get('geom_parent', 'Không tìm thấy')
                            else:
                                prefix_c = k_c.split('/')[0] if '/' in k_c else k_c
                                if prefix_c in cad_map:
                                    geom_p = cad_map[prefix_c].get('geom_parent', 'Không tìm thấy')
                            
                            warn_msg = f"Điểm đầu theo Text CAD khớp nhưng lệch với nét vẽ (LINE: {geom_p})"
                            if warn_msg not in chi_tiet_val:
                                chi_tiet_val = f"{chi_tiet_val}\n- ⚠️ {warn_msg}" if chi_tiet_val else f"⚠️ {warn_msg}"
                            if "✅" in trang_thai_val or not trang_thai_val or "Khớp" in trang_thai_val:
                                trang_thai_val = "⚠️ Cảnh báo"
                                
                        new_chi_tiet.append(chi_tiet_val)
                        new_trang_thai.append(trang_thai_val)
                    else:
                        new_diem_dau.append(diem_dau_val)
                        new_cad_diem_dau.append(f"❌ {cad_val}" if not cad_val.startswith('❌') else cad_val)
                        
                        err_msg = f"Kiểm tra điểm đầu: Sai lệch so với CAD (CAD: {cad_val})"
                        if err_msg not in chi_tiet_val:
                            if chi_tiet_val:
                                chi_tiet_val = f"{chi_tiet_val}\n- {err_msg}"
                            else:
                                chi_tiet_val = f"- {err_msg}"
                        new_chi_tiet.append(chi_tiet_val)
                        new_trang_thai.append("❌ Sai lệch")
                        
                res_tuyen_cap[diem_dau_col] = new_diem_dau
                res_tuyen_cap['Điểm đầu cad'] = new_cad_diem_dau
                res_tuyen_cap['Chi tiết'] = new_chi_tiet
                res_tuyen_cap['Trạng thái Lỗi'] = new_trang_thai

        # 2. Update Hàn nối
        if not res_han_noi.empty:
            vi_tri_col = next((c for c in res_han_noi.columns if c.lower() == 'vị trí'), None)
            if vi_tri_col:
                idx = res_han_noi.columns.get_loc(vi_tri_col)
                def get_cad_han(key):
                    if not cad_map: return ""
                    if pd.isna(key): return ""
                    key_str = str(key).strip().upper()
                    
                    if key_str in cad_map:
                        return cad_map[key_str]['splices']
                    prefix_key = key_str.split('/')[0] if '/' in key_str else key_str
                    if prefix_key in cad_map:
                        return cad_map[prefix_key]['splices']
                        
                    p_idx = key_str.find('P')
                    if p_idx != -1:
                        k = key_str[p_idx:]
                        if k in cad_map: return cad_map[k]['splices']
                        prefix = k.split('/')[0] if '/' in k else k
                        if prefix in cad_map: return cad_map[prefix]['splices']
                    return ""
                
                if 'SL hàn cad' not in res_han_noi.columns:
                    res_han_noi.insert(idx + 1, 'SL hàn cad', res_han_noi[vi_tri_col].apply(get_cad_han))
                
                # --- UPDATE SPLICES RECONCILIATION ---
                new_sl_tk = []
                new_sl_tt = []
                new_cad_sl_han = []
                new_chi_tiet = []
                new_trang_thai = []
                
                sl_tk_col = next((c for c in res_han_noi.columns if c.lower() == 'sl thiết kế'), None)
                sl_tt_col = next((c for c in res_han_noi.columns if c.lower() == 'sl đề nghị'), None)
                
                if sl_tk_col and sl_tt_col:
                    for _, row in res_han_noi.iterrows():
                        tk_val = str(row.get(sl_tk_col, "")).strip()
                        tt_val = str(row.get(sl_tt_col, "")).strip()
                        cad_val = str(row.get('SL hàn cad', "")).strip()
                        chi_tiet_val = str(row.get('Chi tiết', "")).strip()
                        trang_thai_val = str(row.get('Trạng thái Lỗi', "")).strip()
                        
                        if tk_val.lower() == 'nan': tk_val = "0"
                        if tt_val.lower() == 'nan': tt_val = "0"
                        if cad_val.lower() == 'nan': cad_val = ""
                        if chi_tiet_val.lower() == 'nan': chi_tiet_val = ""
                        if trang_thai_val.lower() == 'nan': trang_thai_val = ""
                        
                        if not cad_val:
                            new_sl_tk.append(tk_val)
                            new_sl_tt.append(tt_val)
                            new_cad_sl_han.append(cad_val)
                            new_chi_tiet.append(chi_tiet_val)
                            new_trang_thai.append(trang_thai_val)
                            continue
                        
                        def to_float_safe(v):
                            try:
                                return float(str(v).replace('✅', '').replace('❌', '').strip())
                            except:
                                return None
                                
                        num_tk = to_float_safe(tk_val)
                        num_tt = to_float_safe(tt_val)
                        num_cad = to_float_safe(cad_val)
                        
                        disp_tk = str(int(num_tk)) if num_tk is not None and num_tk.is_integer() else tk_val
                        disp_tt = str(int(num_tt)) if num_tt is not None and num_tt.is_integer() else tt_val
                        disp_cad = str(int(num_cad)) if num_cad is not None and num_cad.is_integer() else cad_val
                        
                        pref_tk = "❌"
                        pref_tt = "❌"
                        pref_cad = "❌"
                        
                        if num_cad is not None and num_tk is not None and num_tt is not None:
                            if num_cad == num_tk == num_tt:
                                pref_cad = "✅"
                                pref_tk = "✅"
                                pref_tt = "✅"
                            elif num_cad == num_tk:
                                pref_cad = "✅"
                                pref_tk = "✅"
                                pref_tt = "❌"
                            elif num_cad == num_tt:
                                pref_cad = "✅"
                                pref_tk = "❌"
                                pref_tt = "✅"
                            elif num_tk == num_tt:
                                pref_cad = "❌"
                                pref_tk = "✅"
                                pref_tt = "✅"
                            else:
                                pref_cad = "❌"
                                pref_tk = "❌"
                                pref_tt = "❌"
                        elif num_tk is not None and num_tt is not None:
                            if num_tk == num_tt:
                                pref_tk = "✅"
                                pref_tt = "✅"
                                pref_cad = "❌"
                            else:
                                pref_tk = "❌"
                                pref_tt = "❌"
                                pref_cad = "❌"
                        else:
                            pref_cad = "❌"
                            pref_tk = "❌"
                            pref_tt = "❌"

                        def format_with_pref(pref, val):
                            if not val or val.lower() == 'nan': return ""
                            val_clean = str(val).replace('✅', '').replace('❌', '').strip()
                            return f"{pref} {val_clean}"

                        disp_tk_final = format_with_pref(pref_tk, disp_tk)
                        disp_tt_final = format_with_pref(pref_tt, disp_tt)
                        disp_cad_final = format_with_pref(pref_cad, disp_cad)

                        new_sl_tk.append(disp_tk_final)
                        new_sl_tt.append(disp_tt_final)
                        new_cad_sl_han.append(disp_cad_final)

                        if pref_cad == "✅" and pref_tk == "✅" and pref_tt == "✅":
                            new_chi_tiet.append(chi_tiet_val)
                            new_trang_thai.append(trang_thai_val)
                        else:
                            if cad_val == "Không tìm thấy" or not cad_val:
                                err_msg = f"Kiểm tra mối hàn: Không tìm thấy số lượng trên CAD (Đề nghị: {disp_tt}, Thiết kế: {disp_tk})"
                            else:
                                err_msg = f"Kiểm tra mối hàn: Sai lệch số lượng (CAD: {disp_cad}, Đề nghị: {disp_tt}, Thiết kế: {disp_tk})"
                                
                            if err_msg not in chi_tiet_val:
                                if chi_tiet_val:
                                    chi_tiet_val = f"{chi_tiet_val}\n- {err_msg}"
                                else:
                                    chi_tiet_val = f"- {err_msg}"
                            new_chi_tiet.append(chi_tiet_val)
                            new_trang_thai.append("❌ Sai lệch")
                            
                    res_han_noi[sl_tk_col] = new_sl_tk
                    res_han_noi[sl_tt_col] = new_sl_tt
                    res_han_noi['SL hàn cad'] = new_cad_sl_han
                    res_han_noi['Chi tiết'] = new_chi_tiet
                    res_han_noi['Trạng thái Lỗi'] = new_trang_thai

        # 3. Update Đối tượng (CAD data comparison disabled per MN request)
        pass

        # --- MERGE USER NOTES FROM BRIDGE ---
        user_notes_json = st.session_state.get('_user_notes_data', '')
        if user_notes_json and len(user_notes_json) > 2:
            try:
                import json as _json_parser
                user_notes_dict = _json_parser.loads(user_notes_json)
                
                def merge_notes(df, tab_key):
                    if df.empty or tab_key not in user_notes_dict: return df
                    df_c = df.copy()
                    notes = user_notes_dict[tab_key]
                    for idx_str, note_val in notes.items():
                        try:
                            # idx from JS is 1-based, matching our Excel/Display index
                            idx_int = int(idx_str)
                            # Find the row where index (STT) matches
                            # Since we reset index to 1..N elsewhere, let's be safe
                            if idx_int <= len(df_c):
                                df_c.iloc[idx_int-1, df_c.columns.get_loc("Ghi chú")] = note_val
                        except: pass
                    return df_c
                
                res_doi_tuong = merge_notes(res_doi_tuong, 'dt')
                res_tuyen_cap = merge_notes(res_tuyen_cap, 'tc')
                res_han_noi = merge_notes(res_han_noi, 'hn')
                res_vat_tu = merge_notes(res_vat_tu, 'vt')
            except: pass

        # --- APPLY MANUAL HN HIGHLIGHTS ---
        hn_hl_val = st.session_state.get('_hn_hl_data', '')
        if hn_hl_val and len(hn_hl_val) > 2:
            try:
                import json as _j_hn
                hn_idxs = _j_hn.loads(hn_hl_val)
                for h_idx in hn_idxs:
                    i_h = int(h_idx)
                    if i_h <= len(res_han_noi):
                         res_han_noi.iloc[i_h-1, res_han_noi.columns.get_loc("Trạng thái Lỗi")] = '❌ Lỗi thực tế'
            except: pass

        # Clean-up NaN in Ghi chú for display
        for df in [res_doi_tuong, res_tuyen_cap, res_han_noi, res_vat_tu]:
            if not df.empty and "Ghi chú" in df.columns:
                df["Ghi chú"] = df["Ghi chú"].replace(["nan", "NaN", "None"], "").fillna("")

        def collect_err(df, cat):
            if df.empty: return
            mask = pd.Series([False] * len(df), index=df.index)
            if 'Trạng thái Lỗi' in df.columns:
                 mask |= df['Trạng thái Lỗi'].astype(str).str.contains("Lệch|Thiếu|Thừa|Cảnh báo|Quá tải|Lỗi", na=False, case=False)
            elif 'Lỗi' in df.columns:
                 mask |= df['Lỗi'].astype(str).str.contains("Lệch|Thiếu|Thừa|Cảnh báo|Quá tải|Lỗi", na=False, case=False)
            try:
                emoji_mask = pd.Series([False] * len(df), index=df.index)
                for c in df.columns:
                    emoji_mask |= df[c].astype(str).str.contains("❌|⚠️", na=False)
                mask |= emoji_mask
            except: pass
            if mask.any():
                errs = df[mask].copy()
                errs.insert(0, "Hạng mục", cat)
                all_errors.append(errs)
                errors_dict[cat] = errs
                
        collect_err(res_doi_tuong, "DoiTuong")
        collect_err(res_tuyen_cap, "TuyenCap")
        # Filter HanNoi for global error list (exclude positions missing in BBNT per user request)
        res_han_noi_err = res_han_noi[res_han_noi['Trạng thái Lỗi'] != "❌ Thiếu trong biên bản"] if not res_han_noi.empty else res_han_noi
        collect_err(res_han_noi_err, "HanNoi")
        collect_err(res_vat_tu, "VatTu")
        collect_err(res_design_cap, "DungLuong")
    else:
        # Reset results if files missing
        res_doi_tuong, res_tuyen_cap, res_han_noi, res_vat_tu, res_design_cap = [pd.DataFrame()] * 5
        st.session_state['recalculate_results'] = True
    
    def to_excel_multiple_sheets(dfs, filter_errors_only=False, include_warnings=False, pre_rows=None):
         output = BytesIO()
         if pre_rows is None: pre_rows = {}
         with pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
             workbook = writer.book
             # Styles
             wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'vcenter'})
             normal_format = workbook.add_format({'valign': 'vcenter'})
             highlight_format = workbook.add_format({'bg_color': '#ffeeb2', 'font_color': '#995c00', 'bold': True, 'valign': 'vcenter'})
             error_format = workbook.add_format({'bg_color': '#fee2e2', 'font_color': '#b91c1c', 'valign': 'vcenter'})
             warn_format = workbook.add_format({'bg_color': '#fef9c3', 'font_color': '#854d0e', 'valign': 'vcenter'})
             ok_format = workbook.add_format({'bg_color': '#dcfce7', 'font_color': '#166534', 'valign': 'vcenter'})
             summary_format = workbook.add_format({'bold': True, 'font_size': 12, 'valign': 'vcenter'})
             
             for sheet_name, df in dfs.items():
                 df_out = df.copy()
                 
                 # Kiểm tra nếu là sheet dữ liệu gốc thì không phân loại/lọc lỗi
                 is_raw = "Goc" in str(sheet_name) or "Gốc" in str(sheet_name)
                 
                 # Add classification column for easier filtering in Excel
                 def classify(row):
                     rs = " ".join(row.astype(str))
                     st = str(row.get('Trạng thái Lỗi', ''))
                     if '❌' in rs or any(x in st for x in ['Lệch', 'Thiếu', 'Thừa', 'Quá tải', 'Lỗi']):
                         return "🔴 LỖI"
                     if '⚠️' in rs or 'Cảnh báo' in st:
                         return "🟡 CẢNH BÁO"
                     if '✅' in rs or 'Khớp' in st:
                         return "🟢 ĐẠT"
                     return "⚪ KHÁC"
                 
                 if len(df_out) > 0 and not is_raw:
                     df_out.insert(0, 'Phân loại', df_out.apply(classify, axis=1))
 
                 for c in df_out.columns:
                     if "SL" in c and df_out[c].dtype in ['float64', 'float32']:
                         df_out[c] = df_out[c].round(1)
                 
                 if 'Hạng mục' in df_out.columns:
                     df_out = df_out.drop(columns=['Hạng mục'])
                 
                 # Write summary rows if provided
                 start_row = 0
                 if sheet_name in pre_rows:
                     # Create worksheet explicitly to write pre-rows
                     worksheet = workbook.add_worksheet(sheet_name)
                     writer.sheets[sheet_name] = worksheet
                     for txt in pre_rows[sheet_name]:
                         worksheet.write(start_row, 0, txt, summary_format)
                         start_row += 1
                 
                 df_out.to_excel(writer, sheet_name=sheet_name, index=False, startrow=start_row)
                 worksheet = writer.sheets[sheet_name]
                 
                 # Apply cell-level formatting based on content
                 for row_idx in range(len(df_out)):
                     row_data = df_out.iloc[row_idx]
                     row_str = " ".join(row_data.astype(str))
                     status_val = str(row_data.get('Trạng thái Lỗi', ''))
                     
                     is_err_row = ('❌' in row_str or any(x in status_val for x in ['Lệch', 'Thiếu', 'Thừa', 'Cảnh báo', 'Quá tải', 'Lỗi']))
                     is_ok_row = ('✅' in row_str or 'Khớp' in status_val)
                     
                     colorable_cols = [
                         "Kiểm tra Vị trí", 
                         "Check Công suất/Mở port", 
                         "Dung lượng (Thiết kế/Import)", 
                         "Mã hộp (Thiết kế/Import)",
                         "Dung lượng (TT/TK)", 
                         "Loại (TT/TK)", 
                         "C.dài thi công / Dự toán / Thiết kế", 
                         "Trạng thái Lỗi"
                     ]
                     
                     for col_idx, col_name in enumerate(df_out.columns):
                         val = str(row_data[col_idx])
                         cell_fmt = normal_format
                         
                         if not is_raw and col_name in colorable_cols:
                             if '❌' in val:
                                 cell_fmt = error_format
                             elif '⚠️' in val:
                                 cell_fmt = warn_format
                             elif '✅' in val:
                                 cell_fmt = ok_format
                             elif col_name == 'Trạng thái Lỗi':
                                 if is_err_row: 
                                     if '⚠️' in val or 'Cảnh báo' in val: cell_fmt = warn_format
                                     else: cell_fmt = error_format
                                 elif is_ok_row: cell_fmt = ok_format
                             elif val.strip() != '' and val.strip() != 'nan' and val.strip() != '-':
                                 cell_fmt = ok_format
                         
                         # Overwrite cell with both value and the specific format
                         val_to_write = row_data[col_idx]
                         if pd.isna(val_to_write):
                             val_to_write = ""
                         worksheet.write(row_idx + start_row + 1, col_idx, val_to_write, cell_fmt)
                     
                     if filter_errors_only and not is_raw:
                         is_err = str(row_data[0]) == "🔴 LỖI"
                         is_warn = str(row_data[0]) == "🟡 CẢNH BÁO"
                         if not is_err and not (include_warnings and is_warn):
                             worksheet.set_row(row_idx + start_row + 1, options={'hidden': True})
 
                 # Enable AutoFilter
                 worksheet.autofilter(start_row, 0, len(df_out) + start_row, len(df_out.columns) - 1)
                 if filter_errors_only and not is_raw:
                     _f_c = 'x == "🔴 LỖI"'
                     if include_warnings: _f_c += ' or x == "🟡 CẢNH BÁO"'
                     worksheet.filter_column(0, _f_c)
                 
                 for i, col in enumerate(df_out.columns):
                     if i == len(df_out.columns) - 1:
                         worksheet.set_column(i, i, 45, wrap_format)
                     else:
                         max_len = max(df_out[col].astype(str).map(len).max(), len(str(col))) + 2
                         if pd.isna(max_len): max_len = 15
                         worksheet.set_column(i, i, min(max_len, 35), normal_format)
         return output.getvalue()



    # --- PAGE 2: KẾT QUẢ PHÂN TÍCH ---
    if nav == "Kết quả phân tích":
        # Match Sidebar H2 styling: color:#3b82f6 -> blueish, size 1.5rem
        # Adjust main title to match size/color roughly or exactly as requested (size of QC analytic)
        
        if not is_any_loaded:
            st.warning("⚠️ CHƯA CÓ HỒ SƠ: Bạn cần upload ít nhất 1 loại file tại tab 'Nhật ký & File' để thực hiện đối soát.")
            st.stop()
            
        st.title("📊 Kết quả Phân tích")
            
        t1, t2, t3, t4 = st.tabs(["📦 Đối tượng", "🔗 Tuyến cáp", "⚡ Hàn nối", "🛠 Vật tư"])
        
        def render_tab(tab, df, name):
            with tab:
                if df.empty:
                    st.info("Chưa có kết quả (Thiếu dữ liệu đầu vào).")
                else:
                    # Logic 1: Handle Errors
                    if 'Trạng thái Lỗi' in df.columns:
                        display_df = df.style.apply(highlight_rows, axis=1)
                    elif 'Lỗi' in df.columns:
                        display_df = df
                        st.error("⚠️ Phát hiện lỗi cấu trúc dữ liệu:")
                    else:
                        display_df = df
                    
                    # Logic 2: Reset Index to start from 1 (STT)
                    df.index = range(1, len(df) + 1)
                    
                    # Logic 3: Selective Styling for Word Wrap & Newlines
                    wrap_cols = [c for c in df.columns if any(x in c for x in ["Chi tiết", "Tên vật tư", "Ghi chú"])]
                    nowrap_cols = [c for c in df.columns if c not in wrap_cols]
                    
                    if 'Trạng thái Lỗi' in df.columns:
                        styled_df = df.style.apply(highlight_rows, axis=1)
                    else:
                        styled_df = df.style
                        
                    styled_df = styled_df.set_properties(subset=nowrap_cols, **{'white-space': 'nowrap', 'width': '1%', 'overflow': 'hidden'})
                    if wrap_cols:
                        styled_df = styled_df.set_properties(subset=wrap_cols, **{'white-space': 'pre-wrap', 'word-wrap': 'break-word', 'min-width': '250px'})

                    # Style headers specifically to ensure columns shrink-to-fit
                    th_styles = []
                    for i, c in enumerate(df.columns):
                        if c in wrap_cols:
                            th_styles.append({'selector': f'th.col{i}', 'props': [('white-space', 'normal')]})
                        else:
                            th_styles.append({'selector': f'th.col{i}', 'props': [('white-space', 'nowrap'), ('width', '1%')]})
                    styled_df = styled_df.set_table_styles(th_styles, overwrite=False)

                    # Format SL columns to 1 decimal place
                    sl_fmt = {c: "{:.1f}" for c in df.columns if "SL" in c and df[c].dtype in ['float64', 'float32']}
                    if sl_fmt:
                        styled_df = styled_df.format(sl_fmt)

                    # Fix underlying data bug with Native Table
                    display_df = styled_df

                    # Logic 4: Full View - Native HTML Table wrap
                    with st.container(height=600, border=True):
                        st.table(display_df)
                    
                    fn = f"Result_{name}_{datetime.now().strftime('%H%M')}.xlsx"
                    st.download_button("📥 Tải Excel", to_excel(df), fn, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # --- Tab Đối tượng: Interactive Sort & Sticky Header ---
        with t1:
            if res_doi_tuong.empty:
                st.info("Chưa có kết quả (Thiếu dữ liệu đầu vào).")
            elif "Lỗi" in res_doi_tuong.columns:
                st.error(f"⚠️ Không thể đối soát Đối tượng: {res_doi_tuong['Lỗi'].iloc[0]}")
            else:
                res_doi_tuong.index = range(1, len(res_doi_tuong) + 1)
                import json as _json_dt
                upload_id = st.session_state.get('upload_session_id', 'default_session_id')
                
                # Convert dataframe to list of dicts for JS
                dt_rows = []
                for idx, row in res_doi_tuong.iterrows():
                    dt_rows.append({
                        "idx": idx,
                        "doi_tuong": str(row.get("Đối tượng", "")),
                        "power": str(row.get("Check Công suất/Mở port", "")),
                        "dung_luong": str(row.get("Dung lượng (Thiết kế/Import)", "")),
                        "ma_hop": str(row.get("Mã hộp (Thiết kế/Import)", "")),
                        "chi_tiet": str(row.get("Chi tiết Lỗi khác", "")),
                        "ghi_chu": str(row.get("Ghi chú", ""))
                    })
                dt_json = _json_dt.dumps(dt_rows, ensure_ascii=False)
                
                
                tong_dt_tk = 0
                tk_valid_keys = []
                if len(df_std_tk.columns) > 8:
                    col_obj_tk = df_std_tk.columns[1]
                    for _, row in df_std_tk.iterrows():
                        val_h = row.iloc[8] if len(row) > 8 else pd.NA
                        if pd.notna(val_h) and str(val_h).strip() != "":
                            tong_dt_tk += 1
                            raw_obj = str(row[col_obj_tk]).strip()
                            if raw_obj and raw_obj.lower() != 'nan':
                                key = raw_obj.split('-')[0].strip()
                                key = qa._normalize_text(key)
                                tk_valid_keys.append(key)
                
                tong_dt_tc = len(res_doi_tuong)
                
                def format_short_node_dt(name):
                    name = str(name).strip()
                    if '.' in name:
                        name = name.split('.')[-1]
                    parts = name.split('/')
                    if parts[0]:
                        parts[0] = parts[0].lstrip('0')
                    return '/'.join(parts)
                
                diff_text = ""
                bbnt_keys = res_doi_tuong['Đối tượng'].dropna().apply(lambda x: str(x).split('-')[0].strip()).apply(qa._normalize_text).tolist()
                
                if tong_dt_tc > tong_dt_tk:
                    tk_keys_temp = tk_valid_keys.copy()
                    thua_raw = []
                    for k in bbnt_keys:
                        if k in tk_keys_temp:
                            tk_keys_temp.remove(k)
                        else:
                            thua_raw.append(k)
                    if thua_raw:
                        thua_items = []
                        for k in thua_raw:
                            short_k = format_short_node_dt(k)
                            if short_k not in thua_items:
                                thua_items.append(short_k)
                        diff_text = f", Đối tượng thừa so thiết kế: {', '.join(thua_items)}"
                        
                elif tong_dt_tc < tong_dt_tk:
                    bbnt_keys_temp = bbnt_keys.copy()
                    thieu_raw = []
                    for k in tk_valid_keys:
                        if k in bbnt_keys_temp:
                            bbnt_keys_temp.remove(k)
                        else:
                            thieu_raw.append(k)
                    if thieu_raw:
                        thieu_items = []
                        for k in thieu_raw:
                            short_k = format_short_node_dt(k)
                            if short_k not in thieu_items:
                                thieu_items.append(short_k)
                        diff_text = f", Đối tượng thiếu so thiết kế: {', '.join(thieu_items)}"

                dt_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                    body {{ font-family: 'Inter', 'Segoe UI', Arial, sans-serif; font-size: 14px; }}
                    table.dt-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 5px;
                        table-layout: fixed;
                    }}
                    table.dt-table th {{
                        background-color: #f6f8fa;
                        padding: 10px;
                        text-align: center;
                        font-weight: 600;
                        color: #24292f;
                        font-size: 14px;
                        border: 1px solid #d0d7de;
                        position: sticky;
                        top: 0;
                        z-index: 10;
                        white-space: nowrap;
                        overflow: hidden;
                    }}
                    table.dt-table th.sortable {{
                        cursor: pointer;
                        user-select: none;
                    }}
                    table.dt-table th.sortable:hover {{
                        background-color: #ebf0f5;
                    }}
                    table.dt-table td {{
                        border: 1px solid #d0d7de;
                        padding: 8px 10px;
                        text-align: center;
                        vertical-align: middle;
                        white-space: pre-wrap; /* For newlines */
                        word-wrap: break-word;
                    }}
                    /* Column widths */
                    table.dt-table th:nth-child(1), table.dt-table td:nth-child(1) {{ width: 40px; }}
                    table.dt-table th:nth-child(2), table.dt-table td:nth-child(2) {{ width: 140px; text-align: left; }}
                    .clamp-3 {{
                        display: -webkit-box;
                        -webkit-line-clamp: 3;
                        -webkit-box-orient: vertical;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        line-height: 1.4em;
                        max-height: 4.2em;
                    }}
                    table.dt-table th:nth-child(3), table.dt-table td:nth-child(3),
                    table.dt-table th:nth-child(4), table.dt-table td:nth-child(4),
                    table.dt-table th:nth-child(5), table.dt-table td:nth-child(5) {{
                        width: 120px;
                        white-space: normal;
                        word-wrap: break-word;
                    }}
                    /* Cột 10,11: Chi tiết & Ghi chú - tự co giãn theo không gian còn lại */
                    table.dt-table td.chi-tiet {{
                        text-align: left;
                        white-space: normal;
                        word-wrap: break-word;
                    }}
                    table.dt-table tr {{ transition: background-color 0.15s; }}
                    table.dt-table tr:hover {{ background-color: #f0f4ff !important; }}
                    table.dt-table tr.err-row {{ background-color: #ffe0e0; }}
                    table.dt-table tr.ok-row {{ background-color: #e6f9e6; }}
                    .dt-hint {{ font-size: 13px; color: #555; margin-bottom: 8px; }}
                    .sort-icon {{ font-size: 11px; margin-left: 5px; opacity: 0.6; }}
                </style>
                </head>
                <body>
                <table class="dt-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th class="sortable" id="sort-doi_tuong">
                                Đối tượng <span class="sort-icon">⇅</span>
                                <div style="margin-top: 5px;">
                                    <input type="text" id="dt-search" placeholder="Tìm..." style="width: 100%; padding: 4px; border: 1px solid #d0d7de; border-radius: 4px; font-weight: normal; font-size: 11px;">
                                </div>
                            </th>
                            <th>Check Công suất/Mở port</th>
                            <th>Dung lượng (Thiết kế/Import)</th>
                            <th>Mã hộp (Thiết kế/Import)</th>
                            <th>Chi tiết Lỗi khác</th>
                            <th style="min-width: 150px;">Ghi chú (Nhập mới)</th>
                        </tr>
                    </thead>
                    <tbody id="dt-body"></tbody>
                </table>
                
                <script>
                    let dtData = {dt_json};
                    let currentSort = {{ column: null, direction: 'asc' }};
                    let searchTerm = '';
                    
                    function getSortValue(val) {{
                        if (!val) return "";
                        // Remove markers for sorting
                        let str = String(val).replace(/[✅❌⚠️]\s*/g, '');
                        const dotIdx = str.indexOf('.');
                        const slashIdx = str.indexOf('/');
                        if (dotIdx !== -1 && slashIdx !== -1 && dotIdx < slashIdx) {{
                            return str.substring(dotIdx + 1, slashIdx);
                        }}
                        return str;
                    }}

                    function getImportCapacity(val) {{
                        if (!val) return "";
                        let clean = String(val).replace(/[✅❌⚠️]\s*/g, '').trim();
                        let parts = clean.split('/');
                        if (parts.length > 1) {{
                            return parts[1].trim().toUpperCase();
                        }}
                        return clean.toUpperCase();
                    }}

                    function getImportBoxCode(val) {{
                        if (!val) return "";
                        let clean = String(val).replace(/[✅❌⚠️]\s*/g, '').trim();
                        let parts = clean.split('/');
                        if (parts.length > 1) {{
                            return parts[1].trim().toUpperCase();
                        }}
                        return clean.toUpperCase();
                    }}

                    function handleSort(col) {{
                        if (currentSort.column === col) {{
                            currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                        }} else {{
                            currentSort.column = col;
                            currentSort.direction = 'asc';
                        }}
                        
                        const el = document.getElementById('sort-doi_tuong');
                        const icon = el.querySelector('.sort-icon');
                        if (col === 'doi_tuong') {{
                            icon.textContent = currentSort.direction === 'asc' ? '▲' : '▼';
                            icon.style.opacity = '1';
                        }} else {{
                            icon.textContent = '⇅';
                            icon.style.opacity = '0.6';
                        }}

                        renderTable();
                    }}

                    document.getElementById('sort-doi_tuong').addEventListener('click', () => handleSort('doi_tuong'));
                    document.getElementById('dt-search').addEventListener('input', (e) => {{
                        searchTerm = e.target.value.toLowerCase();
                        renderTable();
                    }});
                    document.getElementById('dt-search').addEventListener('click', (e) => e.stopPropagation());
                    
                    function renderTable() {{
                        restoreNotes();
                        const tbody = document.getElementById('dt-body');
                        
                        let dataToRender = [...dtData];
                        if (searchTerm) {{
                            dataToRender = dataToRender.filter(r => String(r.doi_tuong).toLowerCase().includes(searchTerm));
                        }}
                        if (currentSort.column) {{
                            dataToRender.sort((a, b) => {{
                                const valA = getSortValue(a[currentSort.column]);
                                const valB = getSortValue(b[currentSort.column]);
                                const numA = parseFloat(valA);
                                const numB = parseFloat(valB);
                                if (!isNaN(numA) && !isNaN(numB)) {{
                                    return currentSort.direction === 'asc' ? numA - numB : numB - numA;
                                }}
                                return currentSort.direction === 'asc' 
                                    ? valA.localeCompare(valB) 
                                    : valB.localeCompare(valA);
                            }});
                        }}

                        tbody.innerHTML = '';
                        dataToRender.forEach(r => {{
                            const tr = document.createElement('tr');
                            
                            // Row statuses for fallback
                            const allContent = r.doi_tuong + r.power + r.dung_luong + r.ma_hop + r.chi_tiet;
                            const isErrRow = allContent.includes('❌') || 
                                           ((allContent.includes('⚠️') || allContent.includes('Lệch')) );
                            const isOkRow = allContent.includes('✅') || allContent.includes('Khớp');

                            function getCellClass(val, isStatusCol = false) {{
                                let v = String(val);
                                if (v.includes('❌')) return 'class="err-cell" style="background-color: #fee2e2; color: #991b1b"';
                                if (v.includes('⚠️')) return 'class="warn-cell" style="background-color: #fef9c3; color: #854d0e"';
                                if (v.includes('✅')) return 'class="ok-cell" style="background-color: #dcfce7; color: #166534"';
                                if (isStatusCol) {{
                                    if (isErrRow) {{
                                        if (v.includes('⚠️')) return 'class="warn-cell" style="background-color: #fef9c3; color: #854d0e"';
                                        return 'class="err-cell" style="background-color: #fee2e2; color: #991b1b"';
                                    }}
                                    if (isOkRow) return 'class="ok-cell" style="background-color: #dcfce7; color: #166534"';
                                }}
                                if (v.trim() !== '' && v.toLowerCase() !== 'nan' && v !== '-' && v !== 'Không tìm thấy') {{
                                    return 'class="ok-cell" style="background-color: #dcfce7; color: #166534"';
                                }}
                                return '';
                            }}

                            tr.innerHTML = `
                                <td class="row-num">${{r.idx}}</td>
                                <td>${{r.doi_tuong}}</td>
                                <td ${{getCellClass(r.power)}}>${{r.power}}</td>
                                <td ${{getCellClass(r.dung_luong)}}>${{r.dung_luong}}</td>
                                <td ${{getCellClass(r.ma_hop)}}>${{r.ma_hop}}</td>
                                <td class="chi-tiet">${{r.chi_tiet}}</td>
                                <td class="chi-tiet editable-cell" contenteditable="true" data-idx="${{r.idx}}" data-tab="dt">${{r.ghi_chu}}</td>
                            `;
                            tbody.appendChild(tr);
                        }});
                    }}
                    function saveUserNote(tab, idx, val) {{
                        const key = "user_notes_" + "{upload_id}";
                        let notes = JSON.parse(localStorage.getItem(key) || "{{}}");
                        if (!notes[tab]) notes[tab] = {{}};
                        notes[tab][idx] = val;
                        localStorage.setItem(key, JSON.stringify(notes));
                    }}

                    function syncNotesToBridge() {{
                        const key = "user_notes_" + "{upload_id}";
                        const data = localStorage.getItem(key);
                        if (!data) return;
                        
                        const parentDoc = window.parent.document;
                        const target = Array.from(parentDoc.querySelectorAll('input')).find(i =>
                            i.getAttribute('aria-label') === 'GhiChu_Bridge'
                        );
                        if (target && target.value !== data) {{
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            setter.call(target, data);
                            target.focus();
                            target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            target.blur();
                        }}
                    }}

                    function restoreNotes() {{
                        const key = "user_notes_" + "{upload_id}";
                        let notes = JSON.parse(localStorage.getItem(key) || "{{}}");
                        if (notes['dt']) {{
                            dtData.forEach(r => {{
                                if (notes['dt'][r.idx]) r.ghi_chu = notes['dt'][r.idx];
                            }});
                        }}
                    }}

                    document.getElementById('dt-body').addEventListener('input', (e) => {{
                        if (e.target.classList.contains('editable-cell')) {{
                            saveUserNote('dt', e.target.dataset.idx, e.target.innerText.trim());
                        }}
                    }});

                    restoreNotes();
                    renderTable();
                </script>
                </body>
                </html>
                """
                st.components.v1.html(dt_html, height=620, scrolling=True)
                
                fn_dt = f"Result_DoiTuong_{datetime.now().strftime('%H%M')}.xlsx"
                st.download_button("📥 Tải Excel", to_excel(res_doi_tuong), fn_dt, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # --- Tab Tuyến cáp: Interactive Row Selection ---
        with t2:
            if res_tuyen_cap.empty:
                st.info("Chưa có kết quả (Thiếu dữ liệu đầu vào).")
            elif "Lỗi" in res_tuyen_cap.columns:
                st.error(f"⚠️ Không thể đối soát Tuyến cáp: {res_tuyen_cap['Lỗi'].iloc[0]}")
            else:
                # Basic reconciliation logic (Excel only)
                res_tuyen_cap.index = range(1, len(res_tuyen_cap) + 1)
                import json as _json_tc
                _upload_id_tc = st.session_state.get('upload_session_id', 'default_session_id')
                
                # Convert dataframe to list of dicts for JS
                tc_rows = []
                for idx, row in res_tuyen_cap.iterrows():
                    tc_rows.append({
                        "idx": idx,
                        "tuyen_cap": str(row.get("Tuyến cáp", "")),
                        "diem_dau": str(row.get("Điểm đầu", "")),
                        "cad_diem_dau": str(row.get("Điểm đầu cad", "")),
                        "diem_cuoi": str(row.get("Điểm cuối (Key)", "")),
                        "dung_luong": str(row.get("Dung lượng (TT/TK)", "")),
                        "loai": str(row.get("Loại (TT/TK)", "")),
                        "c_dai_tc": str(row.get("C.dài thi công", "")),
                        "c_dai_dt": str(row.get("Dự toán tool/ Thiết kế", "")),
                        "cs_dau": str(row.get("Chỉ số đầu", "")),
                        "cs_cuoi": str(row.get("Chỉ số cuối", "")),
                        "trang_thai": str(row.get("Trạng thái Lỗi", "")),
                        "chi_tiet": str(row.get("Chi tiết", "")),
                        "ghi_chu": str(row.get("Ghi chú", ""))
                    })
                tc_json = _json_tc.dumps(tc_rows, ensure_ascii=False)
                
                total_design_len = qa.calculate_total_design_length(df_tk_cap)
                total_construction_count = len(res_tuyen_cap)
                
                def format_short_node(name):
                    name = str(name).strip()
                    if '.' in name:
                        name = name.split('.')[-1]
                    parts = name.split('/')
                    if parts[0]:
                        parts[0] = parts[0].lstrip('0')
                    return '/'.join(parts)
                
                diff_text = ""
                # 1. Parse valid TK keys
                col = qa._find_column(df_tk_cap, ["Số lượng", "Chiều dài"])
                if not col and len(df_tk_cap.columns) > 4:
                    col = df_tk_cap.columns[4]
                
                tk_valid_keys = []
                col_obj_tk = qa._find_column(df_tk_cap, ["Tên đối tượng", "Đối tượng"])
                if not col_obj_tk and len(df_tk_cap.columns) > 0:
                    col_obj_tk = df_tk_cap.columns[0]
                    
                if col and col_obj_tk:
                    for _, row in df_tk_cap.iterrows():
                        val = row[col]
                        if pd.isna(val): continue
                        digits = "".join(filter(str.isdigit, str(val).strip()))
                        if digits:
                            raw_obj = row[col_obj_tk]
                            key = str(raw_obj).split('-')[0].strip()
                            key = qa._normalize_text(key)
                            tk_valid_keys.append(key)
                
                # 2. Parse valid BBNT keys
                bbnt_keys = res_tuyen_cap['Điểm cuối (Key)'].dropna().tolist()
                
                if total_construction_count > total_design_len:
                    # Find thua
                    tk_keys_temp = tk_valid_keys.copy()
                    thua_raw = []
                    for k in bbnt_keys:
                        if k in tk_keys_temp:
                            tk_keys_temp.remove(k)
                        else:
                            thua_raw.append(k)
                    
                    if thua_raw:
                        thua_items = []
                        for k in thua_raw:
                            short_k = format_short_node(k)
                            if short_k not in thua_items:
                                thua_items.append(short_k)
                        diff_text = f", Tuyến thừa so thiết kế: {', '.join(thua_items)}"
                        
                elif total_construction_count < total_design_len:
                    # Find thieu
                    bbnt_keys_temp = bbnt_keys.copy()
                    thieu_raw = []
                    for k in tk_valid_keys:
                        if k in bbnt_keys_temp:
                            bbnt_keys_temp.remove(k)
                        else:
                            thieu_raw.append(k)
                            
                    if thieu_raw:
                        thieu_items = []
                        for k in thieu_raw:
                            short_k = format_short_node(k)
                            if short_k not in thieu_items:
                                thieu_items.append(short_k)
                        diff_text = f", Tuyến thiếu so thiết kế: {', '.join(thieu_items)}"

                tc_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                    body {{ font-family: 'Inter', 'Segoe UI', Arial, sans-serif; font-size: 14px; }}
                    table.tc-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 5px;
                    }}
                    table.tc-table th {{
                        background-color: #f6f8fa;
                        padding: 10px;
                        text-align: center;
                        font-weight: 600;
                        color: #24292f;
                        font-size: 14px;
                        border: 1px solid #d0d7de;
                        position: sticky;
                        top: 0;
                        z-index: 10;
                        white-space: nowrap;
                    }}
                    /* Column widths specific configuration */
                    table.tc-table th:nth-child(1), table.tc-table td:nth-child(1),
                    table.tc-table th:nth-child(4), table.tc-table td:nth-child(4),
                    table.tc-table th:nth-child(6), table.tc-table td:nth-child(6),
                    table.tc-table th:nth-child(7), table.tc-table td:nth-child(7),
                    table.tc-table th:nth-child(8), table.tc-table td:nth-child(8),
                    table.tc-table th:nth-child(9), table.tc-table td:nth-child(9),
                    table.tc-table th:nth-child(10), table.tc-table td:nth-child(10) {{
                        width: 1%;
                        white-space: nowrap;
                    }}
                    table.tc-table th.sortable {{
                        cursor: pointer;
                        user-select: none;
                    }}
                    table.tc-table th.sortable:hover {{
                        background-color: #ebf0f5;
                    }}
                    table.tc-table td {{
                        border: 1px solid #d0d7de;
                        padding: 8px 10px;
                        text-align: center;
                        vertical-align: middle;
                        white-space: nowrap;
                    }}
                    table.tc-table td.row-num {{
                        background-color: #f6f8fa;
                        color: #656d76;
                        font-weight: 500;
                        width: 40px;
                        text-align: center;
                    }}
                    table.tc-table td.chi-tiet {{
                        text-align: left;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        min-width: 250px;
                    }}
                    table.tc-table td.clickable-hl {{
                        cursor: pointer;
                    }}
                    table.tc-table td.clickable-hl:hover {{
                        color: #1e40af;
                        background-color: #eff6ff !important;
                    }}
                    table.tc-table tr {{ transition: background-color 0.15s; }}
                    table.tc-table tr:hover {{ background-color: #f8fafc; }}
                    table.tc-table tr.highlighted {{ background-color: #ffeeb2 !important; }}
                    table.tc-table tr.highlighted:hover {{ background-color: #ffe080 !important; }}
                    table.tc-table tr.err-row {{ background-color: #ffe0e0; }}
                    table.tc-table tr.ok-row {{ background-color: #e6f9e6; }}
                    table.tc-table tr.highlighted.err-row,
                    table.tc-table tr.highlighted.ok-row {{ background-color: #ffeeb2 !important; }}
                    .tc-hint {{ font-size: 13px; color: #555; margin-bottom: 8px; }}
                    .sort-icon {{ font-size: 11px; margin-left: 5px; opacity: 0.6; }}
                </style>
                </head>
                <body>
                <table class="tc-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th class="sortable" id="sort-tuyen_cap">Tuyến cáp <span class="sort-icon">⇅</span></th>
                            <th class="sortable" id="sort-diem_dau">Điểm đầu <span class="sort-icon">⇅</span></th>
                            <th class="sortable" id="sort-diem_cuoi">
                                Điểm cuối (Key) <span class="sort-icon">⇅</span>
                                <input type="text" id="search-diem_cuoi" placeholder="Tìm..." style="width: 100%; margin-top: 5px; padding: 4px; border: 1px solid #d0d7de; border-radius: 4px; font-weight: normal; font-size: 12px; display: block;">
                            </th>
                            <th>Dung lượng (TT/TK)</th>
                            <th>Loại (TT/TK)</th>
                            <th>C.dài thi công</th>
                            <th>Dự toán tool/ Thiết kế</th>
                            <th>Chỉ số đầu</th>
                            <th>Chỉ số cuối</th>
                            <th>Trạng thái Lỗi</th>
                            <th>Chi tiết</th>
                            <th style="min-width: 150px;">Ghi chú (Nhập mới)</th>
                        </tr>
                    </thead>
                    <tbody id="tc-body"></tbody>
                </table>
                
                <script>
                    let tcData = {tc_json};
                    const storageKey = "tc_highlighted_{_upload_id_tc}";
                    let currentSort = {{ column: null, direction: 'asc' }};
                    let searchTerm = "";
                    let highlightedSet = new Set();
                    let foundCounts = {{}};
                    let lastFoundTerm = "";
                    let lastFoundIdx = null;
                    
                    try {{
                        const savedHL = localStorage.getItem(storageKey);
                        if (savedHL) highlightedSet = new Set(JSON.parse(savedHL));
                        
                        const savedFound = localStorage.getItem("tc_found_counts_{_upload_id_tc}");
                        if (savedFound) foundCounts = JSON.parse(savedFound);
                    }} catch(e) {{}}
                    
                    function saveState() {{
                        localStorage.setItem(storageKey, JSON.stringify([...highlightedSet]));
                        localStorage.setItem("tc_found_counts_{_upload_id_tc}", JSON.stringify(foundCounts));
                        syncToBridge();
                    }}
                    
                    // Filter input logic
                    function setupSearchListener() {{
                        const searchInput = document.getElementById('search-diem_cuoi');
                        if (searchInput) {{
                            searchInput.addEventListener('input', (e) => {{
                                searchTerm = e.target.value.toLowerCase();
                                renderTable();
                            }});
                            searchInput.addEventListener('click', (e) => e.stopPropagation());
                            searchInput.addEventListener('keydown', (e) => {{
                                if (e.key === 'Enter') {{
                                    e.preventDefault();
                                    searchInput.value = "";
                                    searchTerm = "";
                                    renderTable();
                                }}
                            }});
                        }}
                    }}
                    
                    function syncToBridge() {{
                        try {{
                            const parentDoc = window.parent.document;
                            const bridge = Array.from(parentDoc.querySelectorAll('input')).find(i =>
                                i.getAttribute('aria-label') === 'DataSync_Bridge'
                            );
                            if (bridge) {{
                                const tcPayload = [];
                                tcData.forEach(r => {{
                                    if (highlightedSet.has(r.idx)) {{
                                        tcPayload.push({{
                                            _type: 'tc_highlight',
                                            idx: r.idx,
                                            tuyen_cap: r.tuyen_cap,
                                            diem_dau: r.diem_dau,
                                            diem_cuoi: r.diem_cuoi,
                                            dung_luong: r.dung_luong,
                                            loai: r.loai,
                                            c_dai_tc: r.c_dai_tc,
                                            c_dai_dt: r.c_dai_dt,
                                            cad_diem_dau: r.cad_diem_dau,
                                            cad_check: r.cad_check,
                                            trang_thai: r.trang_thai,
                                            chi_tiet_orig: r.chi_tiet,
                                            ghi_chu: r.ghi_chu
                                        }});
                                    }}
                                }});
                                localStorage.setItem("tc_errors_{_upload_id_tc}", JSON.stringify(tcPayload));
                            }}
                        }} catch(e) {{}}
                    }}

                    function getSortValue(val) {{
                        if (!val) return "";
                        // Remove markers for sorting
                        let str = String(val).replace(/[✅❌⚠️]\s*/g, '');
                        // Lấy phần giữa dấu . và dấu /
                        const dotIdx = str.indexOf('.');
                        const slashIdx = str.indexOf('/');
                        if (dotIdx !== -1 && slashIdx !== -1 && dotIdx < slashIdx) {{
                            return str.substring(dotIdx + 1, slashIdx);
                        }}
                        return str;
                    }}

                    function handleSort(col) {{
                        if (currentSort.column === col) {{
                            currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                        }} else {{
                            currentSort.column = col;
                            currentSort.direction = 'asc';
                        }}
                        
                        // Update UI icons
                        ['tuyen_cap', 'diem_dau', 'diem_cuoi'].forEach(id => {{
                            const el = document.getElementById('sort-' + id);
                            const icon = el.querySelector('.sort-icon');
                            if (id === col) {{
                                icon.textContent = currentSort.direction === 'asc' ? '▲' : '▼';
                                icon.style.opacity = '1';
                            }} else {{
                                icon.textContent = '⇅';
                                icon.style.opacity = '0.6';
                            }}
                        }});

                        renderTable();
                    }}

                    document.getElementById('sort-tuyen_cap').addEventListener('click', () => handleSort('tuyen_cap'));
                    document.getElementById('sort-diem_dau').addEventListener('click', () => handleSort('diem_dau'));
                    document.getElementById('sort-diem_cuoi').addEventListener('click', () => handleSort('diem_cuoi'));
                    
                    function renderTable() {{
                        restoreNotes();
                        const tbody = document.getElementById('tc-body');
                        
                        let dataToRender = [...tcData];
                        
                        // Apply filter
                        if (searchTerm) {{
                            const s = searchTerm.toLowerCase();
                            const isNum = /^\d+$/.test(s);
                            dataToRender = dataToRender.filter(r => {{
                                const v = String(r.diem_cuoi).toLowerCase();
                                if (isNum) {{
                                    const match = v.match(/\.(\d+)(\/|$)/);
                                    if (match) {{
                                        const nodeNum = match[1].replace(/^0+/, "") || "0";
                                        const searchNum = s.replace(/^0+/, "") || "0";
                                        if (nodeNum === searchNum) return true;
                                    }}
                                }}
                                return v.includes(s);
                            }});
                        }}
                        
                        // Apply sort
                        if (currentSort.column) {{
                            dataToRender.sort((a, b) => {{
                                const valA = getSortValue(a[currentSort.column]);
                                const valB = getSortValue(b[currentSort.column]);
                                // Number sort if both are numbers
                                const numA = parseFloat(valA);
                                const numB = parseFloat(valB);
                                if (!isNaN(numA) && !isNaN(numB)) {{
                                    return currentSort.direction === 'asc' ? numA - numB : numB - numA;
                                }}
                                return currentSort.direction === 'asc' 
                                    ? valA.localeCompare(valB) 
                                    : valB.localeCompare(valA);
                            }});
                        }}

                        const singleResult = dataToRender.length === 1 && searchTerm !== "";
                        if (singleResult) {{
                            const fIdx = dataToRender[0].idx;
                            if (lastFoundIdx !== fIdx || lastFoundTerm !== searchTerm) {{
                                foundCounts[fIdx] = (foundCounts[fIdx] || 0) + 1;
                                lastFoundIdx = fIdx;
                                lastFoundTerm = searchTerm;
                                saveState();
                                if (foundCounts[fIdx] > 1) {{
                                    alert("Ô này đã được tìm " + foundCounts[fIdx] + " lần");
                                }}
                            }}
                        }} else if (searchTerm === "") {{
                            lastFoundIdx = null;
                            lastFoundTerm = "";
                        }}

                        tbody.innerHTML = '';
                        dataToRender.forEach(r => {{
                            const tr = document.createElement('tr');
                            const isHL = highlightedSet.has(r.idx);
                            
                            // Row statuses for fallback
                            const isErrRow = r.trang_thai.includes('❌') || r.trang_thai.includes('Sai') || r.trang_thai.includes('Lệch');
                            const isOkRow = r.trang_thai.includes('✅') || r.trang_thai.includes('Khớp');

                             function getCellClass(val, isStatusCol = false) {{
                                if (isHL) return ''; // Manual priority
                                let v = String(val);
                                if (v.includes('❌')) return 'class="err-cell" style="background-color: #fee2e2; color: #991b1b"';
                                if (v.includes('⚠️')) return 'class="warn-cell" style="background-color: #fef9c3; color: #854d0e"';
                                if (v.includes('✅')) return 'class="ok-cell" style="background-color: #dcfce7; color: #166534"';
                                if (isStatusCol) {{
                                    if (isErrRow) {{
                                        if (v.includes('⚠️')) return 'class="warn-cell" style="background-color: #fef9c3; color: #854d0e"';
                                        return 'class="err-cell" style="background-color: #fee2e2; color: #991b1b"';
                                    }}
                                    if (isOkRow) return 'class="ok-cell" style="background-color: #dcfce7; color: #166534"';
                                }}
                                if (v.trim() !== '' && v.toLowerCase() !== 'nan' && v !== '-') {{
                                    return 'class="ok-cell" style="background-color: #dcfce7; color: #166534"';
                                }}
                                return '';
                            }}

                            if (isHL) tr.classList.add('highlighted');

                            let chiTiet = r.chi_tiet || '';
                            if (isHL) {{
                                chiTiet = chiTiet ? chiTiet + '; Sai điểm đầu' : 'Sai điểm đầu';
                            }}
                            
                            // Highlight "Diem Dau" if only one result OR previously found
                            const isFound = foundCounts[r.idx] > 0;
                            const diemDauStyle = isFound 
                                ? 'class="ok-cell" style="background-color: #4ade80 !important; color: #064e3b !important; font-weight: bold;"' 
                                : '';

                            tr.innerHTML = `
                                <td class="row-num">${{r.idx}}</td>
                                <td class="clickable-hl">${{r.tuyen_cap}}</td>
                                <td class="clickable-hl" ${{diemDauStyle}}>${{r.diem_dau}}</td>
                                <td class="clickable-hl">${{r.diem_cuoi}}</td>
                                <td ${{getCellClass(r.dung_luong)}}>${{r.dung_luong}}</td>
                                <td ${{getCellClass(r.loai)}}>${{r.loai}}</td>
                                <td ${{getCellClass(r.c_dai_tc)}}>${{r.c_dai_tc}}</td>
                                <td ${{getCellClass(r.c_dai_dt)}}>${{r.c_dai_dt}}</td>
                                <td>${{r.cs_dau}}</td>
                                <td>${{r.cs_cuoi}}</td>
                                <td ${{getCellClass(r.trang_thai, true)}}>${{r.trang_thai}}</td>
                                <td class="chi-tiet">${{chiTiet}}</td>
                                <td class="chi-tiet editable-cell" contenteditable="true" data-idx="${{r.idx}}" data-tab="tc" onclick="event.stopPropagation()" onmousedown="event.stopPropagation()">${{r.ghi_chu}}</td>
                            `;
                            
                            tr.addEventListener('click', (e) => {{
                                if (e.target.classList.contains('clickable-hl')) {{
                                    if (highlightedSet.has(r.idx)) {{
                                        highlightedSet.delete(r.idx);
                                    }} else {{
                                        highlightedSet.add(r.idx);
                                    }}
                                    saveState();
                                    renderTable();
                                }}
                            }});
                            
                            tbody.appendChild(tr);
                        }});
                    }}
                    
                    function saveUserNote(tab, idx, val) {{
                        const key = "user_notes_" + "{_upload_id_tc}";
                        let notes = JSON.parse(localStorage.getItem(key) || "{{}}");
                        if (!notes[tab]) notes[tab] = {{}};
                        notes[tab][idx] = val;
                        localStorage.setItem(key, JSON.stringify(notes));
                    }}

                    function syncNotesToBridge() {{
                        const key = "user_notes_" + "{_upload_id_tc}";
                        const data = localStorage.getItem(key);
                        if (!data) return;
                        
                        const parentDoc = window.parent.document;
                        const target = Array.from(parentDoc.querySelectorAll('input')).find(i =>
                            i.getAttribute('aria-label') === 'GhiChu_Bridge'
                        );
                        if (target && target.value !== data) {{
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            setter.call(target, data);
                            target.focus();
                            target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            target.blur();
                        }}
                    }}

                    function restoreNotes() {{
                        const key = "user_notes_" + "{_upload_id_tc}";
                        let notes = JSON.parse(localStorage.getItem(key) || "{{}}");
                        if (notes['tc']) {{
                            tcData.forEach(r => {{
                                if (notes['tc'][r.idx]) r.ghi_chu = notes['tc'][r.idx];
                            }});
                        }}
                    }}

                    document.getElementById('tc-body').addEventListener('input', (e) => {{
                        if (e.target.classList.contains('editable-cell')) {{
                            saveUserNote('tc', e.target.dataset.idx, e.target.innerText.trim());
                        }}
                    }});

                    // Tab to search in Tuyến cáp
                    document.getElementById('tc-body').addEventListener('keydown', (e) => {{
                        if (e.key === 'Tab' && !e.shiftKey && e.target.classList.contains('editable-cell')) {{
                            e.preventDefault();
                            const s = document.getElementById('search-diem_cuoi');
                            if (s) {{ s.focus(); s.select(); }}
                        }}
                    }});

                    restoreNotes();
                    setupSearchListener();
                    renderTable();
                    syncToBridge();
                </script>
                </body>
                </html>
                """
                st.components.v1.html(tc_html, height=620, scrolling=True)
                
                fn_tc = f"Result_TuyenCap_{datetime.now().strftime('%H%M')}.xlsx"
                st.download_button("📥 Tải Excel", to_excel(res_tuyen_cap), fn_tc, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with t3:
            if res_han_noi.empty:
                st.info("Chưa có kết quả (Thiếu dữ liệu đầu vào).")
            elif "Lỗi" in res_han_noi.columns:
                st.error(f"⚠️ Không thể đối soát Hàn nối: {res_han_noi['Lỗi'].iloc[0]}")
            else:
                # Calculate totals and missing list for header (using FULL data)
                res_han_full = res_han_noi.copy()
                sum_dn = int(pd.to_numeric(res_han_full['SL đề nghị'], errors='coerce').fillna(0).sum())
                sum_tk = int(pd.to_numeric(res_han_full['SL Thiết kế'], errors='coerce').fillna(0).sum())
                
                # Format short node helper
                def format_short_node_hn(name):
                    name = str(name).strip()
                    if '.' in name:
                        name = name.split('.')[-1]
                    parts = name.split('/')
                    if parts[0]:
                        parts[0] = parts[0].lstrip('0')
                    return '/'.join(parts)

                # Identify missing items for summary header
                thieu_bbnt = res_han_full[res_han_full['Trạng thái Lỗi'] == "❌ Thiếu trong biên bản"]['Vị trí'].tolist()
                thieu_tk = res_han_full[res_han_full['Trạng thái Lỗi'] == "❌ Thiếu trong thiết kế"]['Vị trí'].tolist()
                
                diff_text = ""
                if thieu_bbnt:
                    items = [format_short_node_hn(i) for i in thieu_bbnt]
                    diff_text += f", Thiếu trong Đề nghị: {', '.join(items)}"
                if thieu_tk:
                    items = [format_short_node_hn(i) for i in thieu_tk]
                    diff_text += f", Chưa có ở Thiết kế: {', '.join(items)}"
                
                # --- FILTER DATA FOR DISPLAY & EXCEL (Only take positions present in BBNT) ---
                res_han_noi_filtered = res_han_full[res_han_full['Trạng thái Lỗi'] != "❌ Thiếu trong biên bản"].copy()
                res_han_noi_filtered.index = range(1, len(res_han_noi_filtered) + 1)
                
                import json as _json_hn
                upload_id = st.session_state.get('upload_session_id', 'default_session_id')
                
                # Convert filtered dataframe to list of dicts for JS
                hn_rows = []
                for idx, row in res_han_noi_filtered.iterrows():
                    hn_rows.append({
                        "idx": idx,
                        "vi_tri": str(row.get("Vị trí", "")),
                        "cad_sl_han": str(row.get("SL hàn cad", "")),
                        "sl_tk": str(row.get("SL Thiết kế", "")),
                        "sl_tt": str(row.get("SL đề nghị", "")),
                        "trang_thai": str(row.get("Trạng thái Lỗi", "")),
                        "chi_tiet": str(row.get("Chi tiết", "")),
                        "ghi_chu": str(row.get("Ghi chú", ""))
                    })
                hn_json = _json_hn.dumps(hn_rows, ensure_ascii=False)
                
                hn_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                    body {{ font-family: 'Inter', 'Segoe UI', Arial, sans-serif; font-size: 14px; }}
                    table.hn-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 5px;
                    }}
                    table.hn-table th {{
                        background-color: #f6f8fa;
                        padding: 10px;
                        text-align: center;
                        font-weight: 600;
                        color: #24292f;
                        font-size: 14px;
                        border: 1px solid #d0d7de;
                        position: sticky;
                        top: 0;
                        z-index: 10;
                        white-space: nowrap;
                    }}
                    table.hn-table td {{
                        border: 1px solid #d0d7de;
                        padding: 8px 10px;
                        text-align: center;
                        vertical-align: middle;
                        white-space: nowrap;
                    }}
                    table.hn-table td.row-num {{
                        background-color: #f6f8fa;
                        color: #656d76;
                        font-weight: 500;
                        width: 40px;
                        text-align: center;
                    }}
                    table.hn-table td.chi-tiet {{
                        text-align: left;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        min-width: 250px;
                    }}
                    table.hn-table tr {{ background-color: white; transition: background-color 0.15s; }}
                    table.hn-table tr:hover {{ background-color: #f8fafc !important; }}
                    
                    /* Cột Vị trí styles */
                    table.hn-table td.clickable-hl {{ cursor: pointer; text-decoration: none; border-left: 3px solid transparent; }}
                    table.hn-table td.clickable-hl:hover {{ background-color: #f0f4ff !important; }}
                    
                    /* Màu xanh: Đã tìm thấy qua search (duy nhất) */
                    table.hn-table td.found-green {{ background-color: #dcfce7 !important; color: #15803d !important; font-weight: bold; }}
                    
                    /* Màu vàng: Đã click kiểm tra */
                    table.hn-table td.checked-yellow {{ background-color: #fef9c3 !important; color: #a16207 !important; font-weight: bold; border-left: 3px solid #eab308 !important; }}
                    
                    /* Cột Vị trí tự co theo dữ liệu */
                    table.hn-table th:nth-child(2), table.hn-table td:nth-child(2) {{
                        width: 1%;
                        white-space: nowrap;
                    }}

                    .hn-hint {{ font-size: 13px; color: #555; margin-bottom: 8px; }}
                    .sort-icon {{ font-size: 11px; margin-left: 5px; opacity: 0.6; }}
                    .search-container {{ margin-top: 6px; padding: 0 4px; }}
                    .vi-tri-search {{
                        width: 120px;
                        padding: 5px 8px;
                        font-size: 12px;
                        border: 1px solid #d1d5db;
                        border-radius: 4px;
                        font-weight: normal;
                    }}
                </style>
                </head>
                <body>
                <table class="hn-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th class="sortable" id="sort-vi_tri">
                                Vị trí <span class="sort-icon">⇅</span>
                                <div class="search-container">
                                    <input type="text" id="vi-tri-search" class="vi-tri-search" placeholder="Tìm..." onclick="event.stopPropagation()">
                                </div>
                            </th>
                            <th>SL đề nghị</th>
                            <th>SL Thiết kế</th>
                            <th>Trạng thái Lỗi</th>
                            <th>Chi tiết</th>
                            <th>Ghi chú (Nhập mới)</th>
                        </tr>
                    </thead>
                    <tbody id="hn-body"></tbody>
                </table>
                
                <script>
                    let hnData = {hn_json};
                    let currentSort = {{ column: null, direction: 'asc' }};
                    let searchTerm = '';
                    let highlightedSet = new Set();
                    let foundCounts = {{}};
                    let lastFoundTerm = "";
                    let lastFoundIdx = null;
                    
                    const HL_KEY = "hn_manual_hl_" + "{upload_id}";
                    const FOUND_KEY = "hn_found_" + "{upload_id}";
                    function saveState() {{
                        localStorage.setItem(HL_KEY, JSON.stringify([...highlightedSet]));
                        localStorage.setItem(FOUND_KEY, JSON.stringify(foundCounts));
                    }}
                    function restoreState() {{
                        const hSaved = localStorage.getItem(HL_KEY);
                        if (hSaved) highlightedSet = new Set(JSON.parse(hSaved));
                        const fSaved = localStorage.getItem(FOUND_KEY);
                        if (fSaved) foundCounts = JSON.parse(fSaved);
                    }}

                    function getSortValue(val) {{
                        if (!val) return "";
                        return String(val).replace(/[✅❌⚠️]\s*/g, '');
                    }}

                    function handleSort(col) {{
                        if (currentSort.column === col) {{
                            currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                        }} else {{
                            currentSort.column = col;
                            currentSort.direction = 'asc';
                        }}
                        
                        const el = document.getElementById('sort-vi_tri');
                        const icon = el.querySelector('.sort-icon');
                        if (col === 'vi_tri') {{
                            icon.textContent = currentSort.direction === 'asc' ? '▲' : '▼';
                            icon.style.opacity = '1';
                        }} else {{
                            icon.textContent = '⇅';
                            icon.style.opacity = '0.6';
                        }}

                        renderTable();
                    }}

                    function renderTable() {{
                        restoreNotes();
                        restoreState();
                        const tbody = document.getElementById('hn-body');
                        
                        let dataToRender = [...hnData];
                        
                        if (searchTerm) {{
                            const s = searchTerm.toLowerCase();
                            const isNum = /^\d+$/.test(s);
                            dataToRender = dataToRender.filter(r => {{
                                const v = String(r.vi_tri).toLowerCase();
                                if (isNum) {{
                                    const match = v.match(/\.(\d+)(\/|$)/);
                                    if (match) {{
                                        const nodeNum = match[1].replace(/^0+/, "") || "0";
                                        const searchNum = s.replace(/^0+/, "") || "0";
                                        if (nodeNum === searchNum) return true;
                                    }}
                                }}
                                return v.includes(s);
                            }});
                        }}

                        if (currentSort.column) {{
                            dataToRender.sort((a, b) => {{
                                const valA = getSortValue(a[currentSort.column]);
                                const valB = getSortValue(b[currentSort.column]);
                                const numA = parseFloat(valA);
                                const numB = parseFloat(valB);
                                if (!isNaN(numA) && !isNaN(numB)) {{
                                    return currentSort.direction === 'asc' ? numA - numB : numB - numA;
                                }}
                                return currentSort.direction === 'asc' ? String(valA).localeCompare(String(valB)) : String(valB).localeCompare(String(valA));
                            }});
                        }}

                        const singleResult = dataToRender.length === 1 && searchTerm.trim() !== "";
                        if (singleResult) {{
                            const fIdx = dataToRender[0].idx;
                            if (lastFoundIdx !== fIdx || lastFoundTerm !== searchTerm) {{
                                foundCounts[fIdx] = (foundCounts[fIdx] || 0) + 1;
                                lastFoundIdx = fIdx;
                                lastFoundTerm = searchTerm;
                                saveState();
                                if (foundCounts[fIdx] > 1) {{
                                    alert("Ô này đã được tìm " + foundCounts[fIdx] + " lần");
                                }}
                            }}
                        }} else if (searchTerm === "") {{
                            lastFoundIdx = null;
                            lastFoundTerm = "";
                        }}

                        tbody.innerHTML = '';
                        
                        dataToRender.forEach(r => {{
                            const tr = document.createElement('tr');
                            const isHL = highlightedSet.has(r.idx);
                            const displayedStatus = isHL ? "❌ Lỗi thực tế" : r.trang_thai;
                            
                            const getStatusCellClass = (v) => {{
                                if (v.includes('❌')) return 'class="err-cell" style="background-color: #fee2e2; color: #991b1b"';
                                if (v.includes('✅')) return 'class="ok-cell" style="background-color: #dcfce7; color: #166534"';
                                return '';
                            }};

                            let viTriClass = "clickable-hl";
                            if (isHL) viTriClass += " checked-yellow";
                            else if (r.trang_thai.includes('Trùng vị trí')) viTriClass += " err-cell";
                            else if (foundCounts[r.idx] > 0) viTriClass += " found-green";
                            
                            tr.innerHTML = `
                                <td class="row-num">${{r.idx}}</td>
                                <td class="${{viTriClass}}">${{r.vi_tri}}</td>
                                <td ${{getStatusCellClass(r.sl_tt)}}>${{r.sl_tt}}</td>
                                <td ${{getStatusCellClass(r.sl_tk)}}>${{r.sl_tk}}</td>
                                <td ${{getStatusCellClass(displayedStatus)}}>${{displayedStatus}}</td>
                                <td class="chi-tiet">${{r.chi_tiet}}</td>
                                <td class="chi-tiet editable-cell" contenteditable="true" data-idx="${{r.idx}}" data-tab="hn">${{r.ghi_chu}}</td>
                            `;

                            const clickable = tr.querySelector('.clickable-hl');
                            if (clickable) {{
                                clickable.addEventListener('click', (e) => {{
                                    e.stopPropagation();
                                    if (highlightedSet.has(r.idx)) {{
                                        highlightedSet.delete(r.idx);
                                        if (r.ghi_chu === "kiểm tra mối hàn") {{
                                            r.ghi_chu = "";
                                            saveUserNote('hn', r.idx, "");
                                        }}
                                    }} else {{
                                        highlightedSet.add(r.idx);
                                        if (!r.ghi_chu || r.ghi_chu.trim() === '') {{
                                            r.ghi_chu = "kiểm tra mối hàn";
                                            saveUserNote('hn', r.idx, r.ghi_chu);
                                        }}
                                    }}
                                    saveState();
                                    renderTable();
                                }});
                            }}

                            tbody.appendChild(tr);
                        }});
                    }}

                    function saveUserNote(tab, idx, val) {{
                        const key = "user_notes_" + "{upload_id}";
                        let notes = JSON.parse(localStorage.getItem(key) || "{{}}");
                        if (!notes[tab]) notes[tab] = {{}};
                        notes[tab][idx] = val;
                        localStorage.setItem(key, JSON.stringify(notes));
                    }}

                    function syncNotesToBridge() {{
                        const key = "user_notes_" + "{upload_id}";
                        const data = localStorage.getItem(key);
                        const hlKey = "hn_manual_hl_" + "{upload_id}";
                        const hls = localStorage.getItem(hlKey) || "[]";
                        
                        const parentDoc = window.parent.document;
                        
                        // Sync Notes
                        const target = Array.from(parentDoc.querySelectorAll('input')).find(i =>
                            i.getAttribute('aria-label') === 'GhiChu_Bridge'
                        );
                        if (target && target.value !== data) {{
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            setter.call(target, data);
                            target.focus();
                            target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            target.blur();
                        }}
                        
                        // Sync Highlights
                        const hnTarget = Array.from(parentDoc.querySelectorAll('input')).find(i =>
                            i.getAttribute('aria-label') === 'HN_Bridge'
                        );
                        if (hnTarget && hnTarget.value !== hls) {{
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            setter.call(hnTarget, hls);
                            hnTarget.focus();
                            hnTarget.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            hnTarget.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            hnTarget.blur();
                        }}
                    }}

                    function restoreNotes() {{
                        const key = "user_notes_" + "{upload_id}";
                        let notes = JSON.parse(localStorage.getItem(key) || "{{}}");
                        if (notes['hn']) {{
                            hnData.forEach(r => {{
                                if (notes['hn'][r.idx]) r.ghi_chu = notes['hn'][r.idx];
                            }});
                        }}
                    }}

                    document.getElementById('hn-body').addEventListener('input', (e) => {{
                        if (e.target.classList.contains('editable-cell')) {{
                            saveUserNote('hn', e.target.dataset.idx, e.target.innerText.trim());
                        }}
                    }});

                    // Tab to search in Hàn nối
                    document.getElementById('hn-body').addEventListener('keydown', (e) => {{
                        if (e.key === 'Tab' && !e.shiftKey && e.target.classList.contains('editable-cell')) {{
                            e.preventDefault();
                            const s = document.getElementById('vi-tri-search');
                            if (s) {{ s.focus(); s.select(); }}
                        }}
                    }});

                    // Filter input logic
                    function setupSearchListener() {{
                        const searchInput = document.getElementById('vi-tri-search');
                        if (searchInput) {{
                            searchInput.addEventListener('input', (e) => {{
                                searchTerm = e.target.value.toLowerCase();
                                renderTable();
                            }});
                            searchInput.addEventListener('click', (e) => e.stopPropagation());
                            searchInput.addEventListener('keydown', (e) => {{
                                if (e.key === 'Enter') {{
                                    e.preventDefault();
                                    searchInput.value = "";
                                    searchTerm = "";
                                    renderTable();
                                }}
                            }});
                        }}
                    }}

                    restoreNotes();
                    restoreState();
                    setupSearchListener();
                    renderTable();
                </script>

                </body>
                </html>
                """
                st.components.v1.html(hn_html, height=620, scrolling=True)
                
                fn_hn = f"Result_HanNoi_{datetime.now().strftime('%H%M')}.xlsx"
                st.download_button("📥 Tải Excel", to_excel(res_han_noi_filtered, pre_rows=[f"Tổng đề nghị: {sum_dn}, Tổng thiết kế: {sum_tk}{diff_text}"]), fn_hn, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # --- Tab Vật tư: Interactive Sort & Sticky Header ---
        with t4:
            if res_vat_tu.empty:
                st.info("Chưa có kết quả (Thiếu dữ liệu đầu vào).")
            elif "Lỗi" in res_vat_tu.columns:
                st.error(f"⚠️ Không thể đối soát Vật tư: {res_vat_tu['Lỗi'].iloc[0]}")
            else:
                res_vat_tu.index = range(1, len(res_vat_tu) + 1)
                import json as _json_vt
                upload_id = st.session_state.get('upload_session_id', 'default_session_id')
                
                # Convert dataframe to list of dicts for JS
                vt_rows = []
                for idx, row in res_vat_tu.iterrows():
                    vt_rows.append({
                        "idx": idx,
                        "kho": str(row.get("Kho", "")),
                        "ma_vt": str(row.get("Mã vật tư", "")),
                        "ten_vt": str(row.get("Tên vật tư", "")),
                        "tinh_trang": str(row.get("Tình trạng hàng", "")),
                        "sl_tk": str(row.get("SL đối chiếu", "")),
                        "sl_nt": str(row.get("SL Nghiệm thu", "")),
                        "trang_thai": str(row.get("Trạng thái Lỗi", "")),
                        "chi_tiet": str(row.get("Chi tiết", "")),
                        "ghi_chu": str(row.get("Ghi chú", ""))
                    })
                vt_json = _json_vt.dumps(vt_rows, ensure_ascii=False)
                
                vt_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                    body {{ font-family: 'Inter', 'Segoe UI', Arial, sans-serif; font-size: 14px; }}
                    table.vt-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 5px;
                    }}
                    table.vt-table th {{
                        background-color: #f6f8fa;
                        padding: 10px;
                        text-align: center;
                        font-weight: 600;
                        color: #24292f;
                        font-size: 14px;
                        border: 1px solid #d0d7de;
                        position: sticky;
                        top: 0;
                        z-index: 10;
                        white-space: nowrap;
                    }}
                    table.vt-table th.sortable {{
                        cursor: pointer;
                        user-select: none;
                    }}
                    table.vt-table th.sortable:hover {{
                        background-color: #ebf0f5;
                    }}
                    table.vt-table td {{
                        border: 1px solid #d0d7de;
                        padding: 8px 10px;
                        text-align: center;
                        vertical-align: middle;
                        white-space: nowrap;
                    }}
                    table.vt-table td.row-num {{
                        background-color: #f6f8fa;
                        color: #656d76;
                        font-weight: 500;
                        width: 40px;
                        text-align: center;
                    }}
                    table.vt-table td.ten-vt, table.vt-table td.chi-tiet {{
                        text-align: left;
                        white-space: normal;
                        word-wrap: break-word;
                        min-width: 200px;
                    }}
                    table.vt-table tr {{ transition: background-color 0.15s; }}
                    table.vt-table tr:hover {{ background-color: #f0f4ff !important; }}
                    table.vt-table tr.err-row {{ background-color: #ffe0e0; }}
                    table.vt-table tr.ok-row {{ background-color: #e6f9e6; }}
                    .vt-hint {{ font-size: 13px; color: #555; margin-bottom: 8px; }}
                    .sort-icon {{ font-size: 11px; margin-left: 5px; opacity: 0.6; }}
                </style>
                </head>
                <body>
                <p class="vt-hint">💡 <b>SL đối chiếu</b> = Tổng SL thực tế (Cột J) file Đối tượng + Tổng SL thực tế (Cột E) file Tuyến cáp theo Mã Vật Tư.</p>
                <table class="vt-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th class="sortable" id="sort-kho">Kho <span class="sort-icon">⇅</span></th>
                            <th class="sortable" id="sort-ma_vt">Mã vật tư <span class="sort-icon">⇅</span></th>
                            <th class="sortable" id="sort-ten_vt">
                                Tên vật tư <span class="sort-icon">⇅</span>
                                <div style="margin-top: 5px;">
                                    <input type="text" id="vt-search" placeholder="Tìm..." style="width: 100%; padding: 4px; border: 1px solid #d0d7de; border-radius: 4px; font-weight: normal; font-size: 11px;">
                                </div>
                            </th>
                            <th>Tình trạng hàng</th>
                            <th>SL đối chiếu</th>
                            <th>SL Nghiệm thu</th>
                            <th>Trạng thái Lỗi</th>
                            <th>Chi tiết</th>
                            <th>Ghi chú (Nhập mới)</th>
                        </tr>
                    </thead>
                    <tbody id="vt-body"></tbody>
                </table>
                
                <script>
                    let vtData = {vt_json};
                    let currentSort = {{ column: 'kho', direction: 'asc' }};
                    let searchTerm = '';
                    
                    function getSortValue(val) {{
                        if (!val) return "";
                        // Remove markers for sorting
                        return String(val).replace(/[✅❌⚠️]\s*/g, '');
                    }}

                    function handleSort(col) {{
                        if (currentSort.column === col) {{
                            currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                        }} else {{
                            currentSort.column = col;
                            currentSort.direction = 'asc';
                        }}
                        
                        // Update UI icons
                        ['kho', 'ma_vt', 'ten_vt'].forEach(id => {{
                            const el = document.getElementById('sort-' + id);
                            const icon = el.querySelector('.sort-icon');
                            if (id === col) {{
                                icon.textContent = currentSort.direction === 'asc' ? '▲' : '▼';
                                icon.style.opacity = '1';
                            }} else {{
                                icon.textContent = '⇅';
                                icon.style.opacity = '0.6';
                            }}
                        }});

                        renderTable();
                    }}

                    document.getElementById('sort-kho').addEventListener('click', () => handleSort('kho'));
                    document.getElementById('sort-ma_vt').addEventListener('click', () => handleSort('ma_vt'));
                    document.getElementById('sort-ten_vt').addEventListener('click', () => handleSort('ten_vt'));
                    document.getElementById('vt-search').addEventListener('input', (e) => {{
                        searchTerm = e.target.value.toLowerCase();
                        renderTable();
                    }});
                    document.getElementById('vt-search').addEventListener('click', (e) => e.stopPropagation());
                    
                    function renderTable() {{
                        restoreNotes();
                        const tbody = document.getElementById('vt-body');
                        
                        let dataToRender = [...vtData];
                        if (searchTerm) {{
                            dataToRender = dataToRender.filter(r => 
                                String(r.ten_vt).toLowerCase().includes(searchTerm) || 
                                String(r.kho).toLowerCase().includes(searchTerm)
                            );
                        }}
                        if (currentSort.column) {{
                            dataToRender.sort((a, b) => {{
                                const valA = getSortValue(a[currentSort.column]);
                                const valB = getSortValue(b[currentSort.column]);
                                
                                // Try numeric sort if they can be numbers
                                const numA = parseFloat(valA);
                                const numB = parseFloat(valB);
                                if (!isNaN(numA) && !isNaN(numB)) {{
                                    return currentSort.direction === 'asc' ? numA - numB : numB - numA;
                                }}
                                
                                return currentSort.direction === 'asc' 
                                    ? String(valA).toLowerCase().localeCompare(String(valB).toLowerCase()) 
                                    : String(valB).toLowerCase().localeCompare(String(valA).toLowerCase());
                            }});
                        }}

                        tbody.innerHTML = '';
                        dataToRender.forEach(r => {{
                            const tr = document.createElement('tr');
                            
                            // Row statuses for fallback
                            const isErrRow = r.trang_thai.includes('❌') || r.trang_thai.includes('Lệch');
                            const isOkRow = r.trang_thai.includes('✅') || r.trang_thai.includes('Khớp');

                             function getCellClass(val, isStatusCol = false) {{
                                let v = String(val);
                                if (v.includes('❌')) return 'class="err-cell" style="background-color: #fee2e2; color: #991b1b"';
                                if (v.includes('⚠️')) return 'class="warn-cell" style="background-color: #fef9c3; color: #854d0e"';
                                if (v.includes('✅')) return 'class="ok-cell" style="background-color: #dcfce7; color: #166534"';
                                if (isStatusCol) {{
                                    if (isErrRow) {{
                                        if (v.includes('⚠️')) return 'class="warn-cell" style="background-color: #fef9c3; color: #854d0e"';
                                        return 'class="err-cell" style="background-color: #fee2e2; color: #991b1b"';
                                    }}
                                    if (isOkRow) return 'class="ok-cell" style="background-color: #dcfce7; color: #166534"';
                                }}
                                // Non-empty values in OK row or Non-error cells in Err row
                                if (v.trim() !== '' && v.toLowerCase() !== 'nan' && v !== '-') {{
                                    return 'class="ok-cell" style="background-color: #dcfce7; color: #166534"';
                                }}
                                return '';
                            }}

                            tr.innerHTML = `
                                <td class="row-num">${{r.idx}}</td>
                                <td>${{r.kho}}</td>
                                <td>${{r.ma_vt}}</td>
                                <td class="ten-vt">${{r.ten_vt}}</td>
                                <td>${{r.tinh_trang}}</td>
                                <td>${{r.sl_tk}}</td>
                                <td>${{r.sl_nt}}</td>
                                <td ${{getCellClass(r.trang_thai, true)}}>${{r.trang_thai}}</td>
                                <td class="chi-tiet">${{r.chi_tiet}}</td>
                                <td class="chi-tiet editable-cell" contenteditable="true" data-idx="${{r.idx}}" data-tab="vt">${{r.ghi_chu}}</td>
                            `;
                            tbody.appendChild(tr);
                        }});
                    }}
                    function saveUserNote(tab, idx, val) {{
                        const key = "user_notes_" + "{upload_id}";
                        let notes = JSON.parse(localStorage.getItem(key) || "{{}}");
                        if (!notes[tab]) notes[tab] = {{}};
                        notes[tab][idx] = val;
                        localStorage.setItem(key, JSON.stringify(notes));
                    }}

                    function syncNotesToBridge() {{
                        const key = "user_notes_" + "{upload_id}";
                        const data = localStorage.getItem(key);
                        if (!data) return;
                        
                        const parentDoc = window.parent.document;
                        const target = Array.from(parentDoc.querySelectorAll('input')).find(i =>
                            i.getAttribute('aria-label') === 'GhiChu_Bridge'
                        );
                        if (target && target.value !== data) {{
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            setter.call(target, data);
                            target.focus();
                            target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            target.blur();
                        }}
                    }}

                    function restoreNotes() {{
                        const key = "user_notes_" + "{upload_id}";
                        let notes = JSON.parse(localStorage.getItem(key) || "{{}}");
                        if (notes['vt']) {{
                            vtData.forEach(r => {{
                                if (notes['vt'][r.idx]) r.ghi_chu = notes['vt'][r.idx];
                            }});
                        }}
                    }}

                    document.getElementById('vt-body').addEventListener('input', (e) => {{
                        if (e.target.classList.contains('editable-cell')) {{
                            saveUserNote('vt', e.target.dataset.idx, e.target.innerText.trim());
                        }}
                    }});

                    restoreNotes();
                    renderTable();
                </script>
                </body>
                </html>
                """
                st.components.v1.html(vt_html, height=620, scrolling=True)
                
                fn_vt = f"Result_VatTu_{datetime.now().strftime('%H%M')}.xlsx"
                st.download_button("📥 Tải Excel", to_excel(res_vat_tu), fn_vt, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")




    # --- PAGE 3: SỐ LIỆU SAI LỆCH (NEW) ---
    if nav == "Số liệu sai lệch":
        c_title, c_btn = st.columns([3, 1])
        c_title.title("⚠️ Tổng hợp Sai lệch")
        
        if not is_any_loaded:
            st.warning("⚠️ Vui lòng upload ít nhất 1 file để xem số liệu sai lệch.")
            st.stop()
            
        _upload_id = st.session_state.get('upload_session_id', 'default_session_id')

        # --- READ HIGHLIGHTED TUYẾN CÁP ROWS ---
        st.markdown('<style>div.tc-bridge-wrapper { position: absolute; opacity: 0; height: 0; overflow: hidden; pointer-events: none; } div:has(> div > input[aria-label="TC_Bridge"]) { position: absolute; opacity: 0; height: 0; overflow: hidden; pointer-events: none; }</style>', unsafe_allow_html=True)
        tc_bridge_val = st.text_input("TC_Bridge", key="tc_bridge_input", label_visibility="collapsed")
        
        tc_highlighted_rows = []
        import json as _json
        if tc_bridge_val and len(tc_bridge_val) > 2:
            try:
                tc_highlighted_rows = _json.loads(tc_bridge_val)
            except: pass
        
        if not tc_highlighted_rows:
            st.components.v1.html(f"""
            <script>
            (function() {{
                const key = "tc_errors_{_upload_id}";
                const saved = localStorage.getItem(key);
                if (saved && saved !== "[]" && saved.length > 2) {{
                    const parentDoc = window.parent.document;
                    const target = Array.from(parentDoc.querySelectorAll('input')).find(i =>
                        i.getAttribute('aria-label') === 'TC_Bridge'
                    );
                    if (target && target.value !== saved) {{
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                        setter.call(target, saved);
                        target.focus();
                        target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        target.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }}));
                        target.blur();
                    }}
                }}
            }})();
            </script>
            """, height=0)
            
            if not st.session_state.get('_tc_sai_lech_synced', False):
                st.session_state['_tc_sai_lech_synced'] = True
                import time as _time2
                _time2.sleep(0.5)
                st.rerun()
        else:
            st.session_state['_tc_sai_lech_synced'] = False

        # --- SYNC USER NOTES BRIDGE ---
        user_notes_data = st.session_state.get('_user_notes_data', '')
        if not user_notes_data or len(user_notes_data) < 3:
            st.components.v1.html(f"""
            <script>
            (function() {{
                const key = "user_notes_{_upload_id}";
                const saved = localStorage.getItem(key);
                if (saved && saved !== "{{}}" && saved.length > 2) {{
                    const parentDoc = window.parent.document;
                    const target = Array.from(parentDoc.querySelectorAll('input')).find(i =>
                        i.getAttribute('aria-label') === 'GhiChu_Bridge'
                    );
                    if (target && target.value !== saved) {{
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                        setter.call(target, saved);
                        target.focus();
                        target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        target.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }}));
                        target.blur();
                    }}
                }}
            }})();
            </script>
            """, height=0)
            
            if not st.session_state.get('_notes_auto_synced', False):
                st.session_state['_notes_auto_synced'] = True
                import time as _t_notes
                _t_notes.sleep(0.3)
                st.rerun()
        else:
            st.session_state['_notes_auto_synced'] = False
            
        # Build tc_sai_lech_df
        if tc_highlighted_rows:
            tc_err_list = []
            for r in tc_highlighted_rows:
                if r.get('_type') == 'tc_highlight':
                    chi_tiet = r.get('chi_tiet_orig', '')
                    chi_tiet = (chi_tiet + '; Sai điểm đầu') if chi_tiet else 'Sai điểm đầu'
                    tc_err_list.append({
                        "Tuyến cáp": r.get('tuyen_cap', ''),
                        "Điểm đầu": r.get('diem_dau', ''),
                        "Điểm cuối (Key)": r.get('diem_cuoi', ''),
                        "Dung lượng (TT/TK)": r.get('dung_luong', ''),
                        "Loại (TT/TK)": r.get('loai', ''),
                        "C.dài thi công / Dự toán / Thiết kế": r.get('chieu_dai', ''),
                        "Trạng thái Lỗi": r.get('trang_thai', ''),
                        "Chi tiết": chi_tiet,
                        "Ghi chú": r.get('ghi_chu', '')
                    })
            if tc_err_list:
                tc_sai_lech_df = pd.DataFrame(tc_err_list)
                tc_sai_lech_df.insert(0, "Hạng mục", "TuyenCap")
                
                if 'TuyenCap' in errors_dict:
                    combined = errors_dict['TuyenCap']
                    for _, new_row in tc_sai_lech_df.iterrows():
                        tuyen_val = str(new_row['Tuyến cáp'])
                        mask = (combined['Tuyến cáp'].astype(str) == tuyen_val)
                        if mask.any():
                            idx = combined[mask].index[0]
                            old_ct = str(combined.at[idx, 'Chi tiết'])
                            if "Sai điểm đầu" not in old_ct:
                                combined.at[idx, 'Chi tiết'] = (old_ct + '; Sai điểm đầu') if old_ct else 'Sai điểm đầu'
                        else:
                            combined = pd.concat([combined, pd.DataFrame([new_row])], ignore_index=True)
                    combined.index = range(1, len(combined) + 1)
                    errors_dict['TuyenCap'] = combined
                    for i, e in enumerate(all_errors):
                        if not e.empty and str(e.iloc[0].get('Hạng mục', '')) == 'TuyenCap':
                            all_errors[i] = combined
                            break
                else:
                    tc_sai_lech_df.index = range(1, len(tc_sai_lech_df) + 1)
                    errors_dict['TuyenCap'] = tc_sai_lech_df
                    all_errors.append(tc_sai_lech_df)
        
        # --- PREPARE SUMMARIES FOR EXCEL ---
        def format_short_node_excel(name):
            name = str(name).strip()
            if '.' in name: name = name.split('.')[-1]
            parts = name.split('/')
            if parts[0]: parts[0] = parts[0].lstrip('0')
            return '/'.join(parts)

        # 1. Summary DoiTuong
        tong_dt_tk = 0
        tk_valid_keys_dt = []
        if not df_std_tk.empty and len(df_std_tk.columns) > 7:
            col_obj_tk_dt = df_std_tk.columns[0]
            for _, row in df_std_tk.iterrows():
                val_h = row.iloc[7] if len(row) > 7 else pd.NA
                if pd.notna(val_h) and str(val_h).strip() != "":
                    tong_dt_tk += 1
                    raw_obj = str(row[col_obj_tk_dt]).strip()
                    if raw_obj and raw_obj.lower() != 'nan':
                        key = raw_obj.split('-')[0].strip()
                        key = qa._normalize_text(key)
                        tk_valid_keys_dt.append(key)
        tong_dt_tc = len(res_doi_tuong)
        bbnt_keys_dt = res_doi_tuong['Đối tượng'].dropna().apply(lambda x: str(x).split('-')[0].strip()).apply(qa._normalize_text).tolist()
        diff_text_dt = ""
        if tong_dt_tc > tong_dt_tk:
            tk_temp = tk_valid_keys_dt.copy()
            thua = []
            for k in bbnt_keys_dt:
                if k in tk_temp: tk_temp.remove(k)
                else: thua.append(k)
            if thua:
                thua_str = ', '.join(dict.fromkeys([format_short_node_excel(k) for k in thua]))
                diff_text_dt = f", Đối tượng thừa so thiết kế: {thua_str}"
        elif tong_dt_tc < tong_dt_tk:
            bbnt_temp = bbnt_keys_dt.copy()
            thieu = []
            for k in tk_valid_keys_dt:
                if k in bbnt_temp: bbnt_temp.remove(k)
                else: thieu.append(k)
            if thieu:
                thieu_str = ', '.join(dict.fromkeys([format_short_node_excel(k) for k in thieu]))
                diff_text_dt = f", Đối tượng thiếu so thiết kế: {thieu_str}"
        dt_summ_str = f"Tổng đối tượng thiết kế: {tong_dt_tk}, Tổng đối tượng thi công: {tong_dt_tc}{diff_text_dt}"

        # 2. Summary TuyenCap
        total_design_len = qa.calculate_total_design_length(df_tk_cap)
        total_construction_count = len(res_tuyen_cap)
        col_tc = qa._find_column(df_tk_cap, ["Số lượng", "Chiều dài"])
        if not col_tc and len(df_tk_cap.columns) > 4: col_tc = df_tk_cap.columns[4]
        tk_valid_keys_tc = []
        col_obj_tk_tc = qa._find_column(df_tk_cap, ["Tên đối tượng", "Đối tượng"])
        if not col_obj_tk_tc and len(df_tk_cap.columns) > 0: col_obj_tk_tc = df_tk_cap.columns[0]
        if col_tc and col_obj_tk_tc:
            for _, row in df_tk_cap.iterrows():
                val = row[col_tc]
                if pd.isna(val): continue
                digits = "".join(filter(str.isdigit, str(val).strip()))
                if digits:
                    key = str(row[col_obj_tk_tc]).split('-')[0].strip()
                    key = qa._normalize_text(key)
                    tk_valid_keys_tc.append(key)
        bbnt_keys_tc = res_tuyen_cap['Điểm cuối (Key)'].dropna().apply(qa._normalize_text).tolist()
        diff_text_tc = ""
        if total_construction_count > total_design_len:
            tk_temp = tk_valid_keys_tc.copy()
            thua = []
            for k in bbnt_keys_tc:
                if k in tk_temp: tk_temp.remove(k)
                else: thua.append(k)
            if thua:
                thua_str = ', '.join(dict.fromkeys([format_short_node_excel(k) for k in thua]))
                diff_text_tc = f", Tuyến thừa so thiết kế: {thua_str}"
        elif total_construction_count < total_design_len:
            bbnt_temp = bbnt_keys_tc.copy()
            thieu = []
            for k in tk_valid_keys_tc:
                if k in bbnt_temp: bbnt_temp.remove(k)
                else: thieu.append(k)
            if thieu:
                thieu_str = ', '.join(dict.fromkeys([format_short_node_excel(k) for k in thieu]))
                diff_text_tc = f", Tuyến thiếu so thiết kế: {thieu_str}"
        tc_summ_str = f"Tổng tuyến thiết kế: {total_design_len}, Tổng tuyến thi công: {total_construction_count}{diff_text_tc}"

        # Summary weld for excel report (Full data)
        dn_hn = int(res_han_noi['SL đề nghị'].astype(str).str.replace(r'[✅❌\s]', '', regex=True).replace('', '0').replace('nan', '0').astype(float).fillna(0).sum()) if 'SL đề nghị' in res_han_noi.columns else 0
        tk_hn = int(res_han_noi['SL Thiết kế'].astype(str).str.replace(r'[✅❌\s]', '', regex=True).replace('', '0').replace('nan', '0').astype(float).fillna(0).sum()) if 'SL Thiết kế' in res_han_noi.columns else 0
        
        # Build diff text for Excel Summary Header
        thieu_bbnt_all = res_han_noi[res_han_noi['Trạng thái Lỗi'] == "❌ Thiếu trong biên bản"]['Vị trí'].tolist() if 'Trạng thái Lỗi' in res_han_noi.columns else []
        thieu_tk_all = res_han_noi[res_han_noi['Trạng thái Lỗi'] == "❌ Thiếu trong thiết kế"]['Vị trí'].tolist() if 'Trạng thái Lỗi' in res_han_noi.columns else []
        
        diff_text_hn_all = ""
        if thieu_bbnt_all:
            diff_text_hn_all += f", Thiếu trong Đề nghị: {', '.join([format_short_node_excel(i) for i in thieu_bbnt_all])}"
        if thieu_tk_all:
            diff_text_hn_all += f", Chưa có ở Thiết kế: {', '.join([format_short_node_excel(i) for i in thieu_tk_all])}"

        hn_summ_str = f"Tổng đề nghị: {dn_hn}, Tổng thiết kế: {tk_hn}{diff_text_hn_all}"
        
        # Filter "HanNoi" for the report list (Remove positions missing in BBNT per user request)
        res_han_noi_filtered_report = res_han_noi[res_han_noi['Trạng thái Lỗi'] != "❌ Thiếu trong biên bản"].copy() if not res_han_noi.empty else res_han_noi

        # --- PREPARE FULL REPORT DATA ---
        full_report_dict = {
            "DoiTuong": res_doi_tuong,
            "TuyenCap": res_tuyen_cap,
            "HanNoi": res_han_noi_filtered_report,
            "VatTu": res_vat_tu
        }

        pre_rows_data = {
            "DoiTuong": [dt_summ_str],
            "TuyenCap": [tc_summ_str],
            "HanNoi": [hn_summ_str]
        }

        if not df_imp.empty:
            full_report_dict["FormImport_Goc"] = df_imp
        if not df_std_tk.empty:
            full_report_dict["ThietKe_Goc"] = df_std_tk
        
        if tc_highlighted_rows:
            tc_full = res_tuyen_cap.copy()
            for r in tc_highlighted_rows:
                if r.get('_type') == 'tc_highlight':
                    t_val = str(r.get('tuyen_cap'))
                    mask = (tc_full['Tuyến cáp'].astype(str) == t_val)
                    if mask.any():
                        idx = tc_full[mask].index[0]
                        tc_full.at[idx, 'Trạng thái Lỗi'] = '❌ Lệch (Manual)'
                        ct = str(tc_full.at[idx, 'Chi tiết'])
                        if "Sai điểm đầu" not in ct:
                            tc_full.at[idx, 'Chi tiết'] = (ct + "; Sai điểm đầu") if ct else "Sai điểm đầu"
            full_report_dict["TuyenCap"] = tc_full

        with c_btn:
            st.write("") 
            st.write("")
            p_name = st.session_state.get('project_name', 'BaoCao') or "BaoCao"
            fn = f"{p_name}_Doi_soat_nghiem_thu.xlsx"
            st.download_button(
                "📥 Tải Báo cáo Sai lệch", 
                to_excel_multiple_sheets(full_report_dict, filter_errors_only=True, include_warnings=True, pre_rows=pre_rows_data), 
                fn, 
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        if not all_errors:
            st.success("🎉 Tuyệt vời! Không tìm thấy sai lệch nào trong dữ liệu.")
        else:
            st.markdown(f"Tìm thấy **{sum(len(e) for e in all_errors)}** sai lệch cần xử lý.")
            
            for edf in all_errors:
                if edf.empty: continue
                cat = str(edf.iloc[0].get('Hạng mục', 'Unknown'))
                
                with st.expander(f"🔴 {cat} ({len(edf)} lỗi)", expanded=False):
                    wrap_cols = [c for c in edf.columns if c in ["Kiểm tra Vị trí", "Chi tiết", "Tên vật tư", "Ghi chú"]]
                    nowrap_cols = [c for c in edf.columns if c not in wrap_cols]
                    
                    styled_edf = edf.style.apply(highlight_rows, axis=1) if 'Trạng thái Lỗi' in edf.columns else edf.style
                        
                    styled_edf = styled_edf.set_properties(subset=nowrap_cols, **{'white-space': 'nowrap', 'overflow': 'hidden'})
                    if wrap_cols:
                        styled_edf = styled_edf.set_properties(subset=wrap_cols, **{'white-space': 'normal', 'word-wrap': 'break-word', 'min-width': '300px', 'max-width': '500px'})

                    # Format SL columns
                    sl_fmt = {c: "{:.1f}" for c in edf.columns if "SL" in c and edf[c].dtype in ['float64', 'float32']}
                    if sl_fmt:
                        styled_edf = styled_edf.format(sl_fmt)

                    with st.container(height=450, border=True):
                        st.table(styled_edf)

