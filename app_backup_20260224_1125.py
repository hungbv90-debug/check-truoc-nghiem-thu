# -*- coding: utf-8 -*-
"""
app.py — Giao diện Streamlit Đối Soát Nghiệm Thu (Refactored v5).
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
import data_processor
import streamlit.components.v1 as components
# Force reload to pick up new methods if cached
importlib.reload(data_processor)
from data_processor import QALogic
from streamlit.runtime import Runtime

import sys

def monitor_resource_usage():
    """Tự động tắt app sau 10s nếu không có tab trình duyệt nào đang kết nối (tiết kiệm tài nguyên)."""
    # KhÔNG chạy cơ chế này nếu không hỗ trợ threading (ví dụ một số môi trường đặc biệt)
    # Tuy nhiên hiện tại tập trung cho bản Streamlit server nên chạy bình thường.


    def _check():
        # Chờ app khởi động hoàn tất lần đầu
        time.sleep(20)
        inactive_count = 0
        while True:
            time.sleep(2)
            try:
                runtime = Runtime.instance()
                if runtime is None:
                    continue
                
                # Kiểm tra số lượng session đang hoạt động
                sessions = runtime.get_client_manager().list_sessions_data()
                if len(sessions) > 0:
                    inactive_count = 0
                else:
                    inactive_count += 2
                    if inactive_count >= 10: # Đã quá 10 giây không có ai dùng
                        os._exit(0)
            except Exception:
                pass
                
    # Đảm bảo chỉ khởi chạy 1 thread giám sát duy nhất
    if not any(t.name == "ResourceMonitor" for t in threading.enumerate()):
        t = threading.Thread(target=_check, name="ResourceMonitor", daemon=True)
        t.start()

# Kích hoạt giám sát
monitor_resource_usage()

# =============================================================================
# PAGE CONFIG & STYLING
# =============================================================================

if 'sidebar_state' not in st.session_state:
    st.session_state['sidebar_state'] = 'expanded'
if 'auto_collapsed' not in st.session_state:
    st.session_state['auto_collapsed'] = False

st.set_page_config(
    page_title="Hệ thống Đối soát QC Cáp Quang",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state=st.session_state['sidebar_state'],
)

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
    
    # Capture Project Name: Prioritize BBNT, then Design
    p_name = ""
    if files_bbnt:
        try:
            full_name = files_bbnt[0].name
            base_name = full_name.rsplit('.', 1)[0]
            # User Request: "Chỉ lấy mỗi mã kế hoạch, bỏ phần _BBNT_DT"
            # Assumption: Plan Code is before the first underscore
            p_name = base_name.split('_')[0]
        except: pass
    elif files_design:
        try:
            full_name = files_design[0].name
            base_name = full_name.rsplit('.', 1)[0]
            p_name = base_name.split('_')[0]
        except: pass
        
    if p_name:
        st.session_state['project_name'] = p_name
    
    # Helper to process list of files
    def _proc(flist, is_bbnt=False):
        m = {}
        l = []
        if not flist: return m, l
        for f in flist:
            try:
                f.seek(0)
                df = qa.read_excel(f)
                if df.empty:
                    l.append(f"⚠️ {f.name}: TRỐNG/LỖI")
                    continue
                ftype = qa.identify_file_type(df, filename=f.name)
                df.attrs['name'] = f.name
                
                msg = f"✅ {f.name} → {ftype}"
                
                if ftype in m:
                    # Gộp và loại bỏ các dòng bị trùng lặp hoàn toàn
                    m[ftype] = pd.concat([m[ftype], df], ignore_index=True).drop_duplicates()
                    msg += " (Gộp & Lọc trùng dòng)"
                else:
                    m[ftype] = df
                l.append(msg)
            except Exception as e:
                l.append(f"❌ {f.name}: {str(e)}")
        return m, l

    if files_design:
        map_d, logs_d = _proc(files_design)
        logs.extend(logs_d)
    
    if files_bbnt:
        map_b, logs_b = _proc(files_bbnt) 
        logs.extend(logs_b)

    # Update Session State
    st.session_state['data_bucket']['map_d'] = map_d
    st.session_state['data_bucket']['map_b'] = map_b
    st.session_state['data_bucket']['logs'] = logs
    st.session_state['data_bucket']['has_data'] = bool(map_d or map_b)
    st.session_state['upload_session_id'] = str(int(time.time()))
    st.session_state['recalculate_results'] = True

def highlight_rows(row):
    status = str(row.get('Trạng thái Lỗi', ''))
    row_str = " ".join(row.astype(str))
    
    # 1. Ưu tiên ❌ (Lỗi nghiêm trọng) -> Đỏ
    if '❌' in row_str:
        return ['background-color: #fee2e2; color: #991b1b'] * len(row)
    
    # 2. Check các từ khóa lỗi trong Trạng thái Lỗi
    if any(x in status for x in ['Thiếu', 'Thừa', 'Cảnh báo', 'Quá tải', 'Lỗi']):
        return ['background-color: #fee2e2; color: #991b1b'] * len(row)
        
    # 3. Check 'Lệch' - Bỏ qua nếu là 'Lệch nhẹ' trong Kiểm tra Vị trí
    if 'Lệch' in status:
        loc_val = str(row.get('Kiểm tra Vị trí', ''))
        if "Lệch nhẹ" in loc_val and "❌" not in row_str:
            return [''] * len(row)
        return ['background-color: #fee2e2; color: #991b1b'] * len(row)
            
    # 4. Thành công -> Xanh
    if 'Khớp' in status or '✅' in row_str:
        return ['background-color: #dcfce7; color: #166534'] * len(row)
        
    return [''] * len(row)

def to_excel(df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    df_out = df.copy()
    for c in df_out.columns:
        if "SL" in c and df_out[c].dtype in ['float64', 'float32']:
            df_out[c] = df_out[c].round(1)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_out.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    return output

# Removed CSS logic for expanding sidebar

# =============================================================================
# MAIN LAYOUT
# =============================================================================

def main():
    with st.sidebar:
        # Custom Logo Area
        st.markdown("""
        <div class="brand-logo">
            <h2 style="margin:0; color:#3b82f6;">⚡ QC ANALYTICS</h2>
            <p style="font-size:0.8rem; color:#64748b;">Hệ thống Đối soát Tự động</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        if 'nav_state' not in st.session_state:
            st.session_state['nav_state'] = "Nhật ký & File"
            
        # Đồng bộ hóa ngược từ nav_state vào radio_nav TRƯỚC khi radio widget được vẽ
        st.session_state['radio_nav'] = st.session_state['nav_state']
            
        def on_nav_change():
            st.session_state['nav_state'] = st.session_state['radio_nav']
            
        nav_opts = ["Nhật ký & File", "Kết quả phân tích", "Số liệu sai lệch"]
        try:
            cur_idx = nav_opts.index(st.session_state['nav_state'])
        except ValueError:
            cur_idx = 0
            
        st.radio(
            "Menu",
            nav_opts,
            index=cur_idx,
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
        
        # Store bridge value in session_state for use on all pages
        if sync_bridge_val and len(sync_bridge_val) > 2:
            st.session_state['_sync_bridge_data'] = sync_bridge_val

    # --- GLOBAL CONSTANTS & VALIDATION ---
    REQUIRED_TYPES = {
        'Form_import': 'Form Import',
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

    # Auto-collapse sidebar removed per user request

    # --- PAGE 1: IMPORT DỮ LIỆU ---
    if nav == "Nhật ký & File":
        st.title("📂 Import Dữ Liệu")
        st.markdown("Tải lên các file Thiết kế và Biên bản nghiệm thu để bắt đầu đối soát.")
        
        # --- TEMPLATE DOWNLOAD SECTION (COLLAPSIBLE) ---
        with st.expander("📥 Tải Template mẫu", expanded=False):
            t_col1, t_col2, t_col3 = st.columns(3)
            with t_col1:
                template_path = "Templates/02_temp_bang_thiet_ke.xlsx"
                if os.path.exists(template_path):
                    with open(template_path, "rb") as f:
                        st.download_button(
                            label="📄 Template Thiết kế",
                            data=f,
                            file_name="Template_Thiet_Ke.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else: st.error("Lỗi: Mất file Thiết kế")
            with t_col2:
                template_import = "Templates/01_temp_formimport.xlsx"
                if os.path.exists(template_import):
                    with open(template_import, "rb") as f:
                        st.download_button(
                            label="📄 Template Import (Gpon)",
                            data=f,
                            file_name="Template_Import_Gpon.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
            
            t_bbnt1, t_bbnt2, t_bbnt3, t_bbnt4 = st.columns(4)
            bbnt_templates = [
                ("03_HNI.I.U.PP.050325.13_BBNT_DT.xlsx", "📄 BBNT Đối tượng", "Template_BBNT_DoiTuong.xlsx"),
                ("05_HNI.I.U.PP.050325.13_BBNT_TuyenCap.xlsx", "📄 BBNT Tuyến cáp", "Template_BBNT_TuyenCap.xlsx"),
                ("04_HNI.I.U.PP.050325.13_BBNT_HanNoi.xlsx", "📄 BBNT Hàn nối", "Template_BBNT_HanNoi.xlsx"),
                ("06_HNI.I.U.PP.050325.13_BBNT_VatTu.xlsx", "📄 BBNT Vật tư", "Template_BBNT_VatTu.xlsx")
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
            type=['xls', 'xlsx'],
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
            for f in u_all_files:
                if f.name in unique_files:
                    has_dupes = True
                else:
                    unique_files[f.name] = f
            filtered_files = list(unique_files.values())
            
            if has_dupes:
                st.warning("⚠️ Đã phát hiện một số file trùng tên. Hệ thống tự động lọc và chỉ giữ lại 1 bản cho mỗi tên file.")

            for f in filtered_files:
                fn = f.name.lower()
                if 'thiet_ke' in fn or 'thiết kế' in fn or 'form' in fn or 'design' in fn:
                    f_d.append(f)
                else:
                    f_b.append(f)
            
            progress_bar.progress(10, text="⏳ 10% — Phân loại file...")
            time.sleep(0.05)
            
            process_files(f_d, f_b)
            
            progress_bar.progress(50, text="⏳ 50% — Đọc file xong, bắt đầu phân tích...")
            time.sleep(0.05)
            
            # --- STRICT VALIDATION BEFORE RERUN ---
            p_types = set(st.session_state['data_bucket']['map_d'].keys()) | set(st.session_state['data_bucket']['map_b'].keys())
            req_keys = ['Form_import', 'thiet_ke', 'doi_tuong', 'TUYEN_CAP', 'han_noi', 'vat_tu']
            missing = [k for k in req_keys if k not in p_types]
            
            if not missing:
                progress_bar.progress(100, text="✅ 100% — Đã đủ 6 loại file! Đang chuyển trang...")
                time.sleep(0.5)
                st.session_state['nav_state'] = "Kết quả phân tích"
                st.session_state['auto_download'] = True
                st.rerun()
            else:
                progress_bar.empty()
                st.error(f"⚠️ Chưa đủ file! Cần thêm: {', '.join([REQUIRED_TYPES.get(m, m) for m in missing])}")
            
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
    if is_fully_loaded:
        if st.session_state.get('recalculate_results', True):
            # Calculate Results only if all files are present
            res_doi_tuong = qa.check_doi_tuong(df_imp, df_bbnt_dt, df_std_tk)
            res_tuyen_cap = qa.check_tuyen_cap(df_tk_cap, df_bbnt_cap)
            res_han_noi = qa.check_han_noi(df_tk_han, df_bbnt_han)
            res_vat_tu = qa.check_vat_tu(df_bbnt_vt, df_bbnt_dt, df_bbnt_cap)
            res_design_cap = qa.check_design_capacity(df_imp, df_std_tk)
            
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
                    if cat == "DoiTuong" and c == "Kiểm tra Vị trí":
                        emoji_mask |= df[c].astype(str).str.contains("❌", na=False)
                    else:
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
        collect_err(res_han_noi, "HanNoi")
        collect_err(res_vat_tu, "VatTu")
        collect_err(res_design_cap, "DungLuong")
    else:
        # Reset results if files missing
        res_doi_tuong, res_tuyen_cap, res_han_noi, res_vat_tu, res_design_cap = [pd.DataFrame()] * 5
        st.session_state['recalculate_results'] = True

    def to_excel_multiple_sheets(dfs):
         output = BytesIO()
         with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
             workbook = writer.book
             wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'vcenter'})
             normal_format = workbook.add_format({'valign': 'vcenter'})
             
             # Prepare highlight format for manual sheet
             highlight_format = workbook.add_format({'bg_color': '#ffeeb2', 'font_color': '#995c00', 'bold': True, 'valign': 'vcenter'})
             
             for sheet_name, df in dfs.items():
                 df_out = df.copy()
                 for c in df_out.columns:
                     if "SL" in c and df_out[c].dtype in ['float64', 'float32']:
                         df_out[c] = df_out[c].round(1)
                 
                 # Drop 'Hạng mục' if it exists, since it's redundant in sheet name
                 if 'Hạng mục' in df_out.columns:
                     df_out = df_out.drop(columns=['Hạng mục'])
                 
                 df_out.to_excel(writer, sheet_name=sheet_name, index=False)
                 df = df_out
                 worksheet = writer.sheets[sheet_name]
                 
                 is_manual_sheet = str(sheet_name).strip() == "Han noi soat"
                 highlight_cols = ["Mối hàn từ hàn nối", "Đối tượng từ hàn nối"]
                 
                 for i, col in enumerate(df.columns):
                     if i == len(df.columns) - 1:
                         # Cột cuối cùng: Cố định 45 và Wrap text
                         worksheet.set_column(i, i, 45, wrap_format)
                     elif is_manual_sheet and str(col) in highlight_cols:
                         max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                         if pd.isna(max_len): max_len = 15
                         worksheet.set_column(i, i, min(max_len, 35), highlight_format)
                     else:
                         max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                         if pd.isna(max_len): max_len = 15
                         worksheet.set_column(i, i, min(max_len, 35), normal_format)
         return output.getvalue()


    # --- PAGE 2: KẾT QUẢ PHÂN TÍCH ---
    if nav == "Kết quả phân tích":
        # Match Sidebar H2 styling: color:#3b82f6 -> blueish, size 1.5rem
        # Adjust main title to match size/color roughly or exactly as requested (size of QC analytic)
        
        if not is_fully_loaded:
            st.warning("⚠️ CHƯA ĐỦ HỒ SƠ: Bạn cần upload đầy đủ 6 loại file tại tab 'Nhật ký & File' để thực hiện đối soát.")
            st.info(f"Cần thêm: **{', '.join(missing_types)}**")
            st.stop()
            
        st.title("📊 Kết quả Phân tích")
            
        t1, t2, t3, t4, t5 = st.tabs(["📦 Đối tượng", "🔗 Tuyến cáp", "⚡ Hàn nối", "🛠 Vật tư", "⚡ Hàn nối soát theo phối"])
        
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
                    
                    # Logic 3: Selective Styling for Word Wrap
                    wrap_cols = [c for c in df.columns if c in ["Kiểm tra Vị trí", "Chi tiết", "Tên vật tư"]]
                    nowrap_cols = [c for c in df.columns if c not in wrap_cols]
                    
                    if 'Trạng thái Lỗi' in df.columns:
                        styled_df = df.style.apply(highlight_rows, axis=1)
                    else:
                        styled_df = df.style
                        
                    styled_df = styled_df.set_properties(subset=nowrap_cols, **{'white-space': 'nowrap', 'width': '1%', 'overflow': 'hidden'})
                    if wrap_cols:
                        styled_df = styled_df.set_properties(subset=wrap_cols, **{'white-space': 'normal', 'word-wrap': 'break-word', 'min-width': '200px'})

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
            else:
                res_doi_tuong.index = range(1, len(res_doi_tuong) + 1)
                import json as _json_dt
                
                # Convert dataframe to list of dicts for JS
                dt_rows = []
                for idx, row in res_doi_tuong.iterrows():
                    dt_rows.append({
                        "idx": idx,
                        "doi_tuong": str(row.get("Đối tượng", "")),
                        "vi_tri": str(row.get("Kiểm tra Vị trí", "")),
                        "power": str(row.get("Check Công suất/Mở port", "")),
                        "dung_luong": str(row.get("Dung lượng (Thiết kế/Import)", "")),
                        "ma_hop": str(row.get("Mã hộp (Thiết kế/Import)", "")),
                        "chi_tiet": str(row.get("Chi tiết", ""))
                    })
                dt_json = _json_dt.dumps(dt_rows, ensure_ascii=False)
                
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
                        white-space: nowrap;
                    }}
                    table.dt-table td.row-num {{
                        background-color: #f6f8fa;
                        color: #656d76;
                        font-weight: 500;
                        width: 40px;
                        text-align: center;
                    }}
                    table.dt-table td.chi-tiet {{
                        text-align: left;
                        white-space: normal;
                        word-wrap: break-word;
                        min-width: 250px;
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
                <p class="dt-hint">💡 Click vào <b>Tiêu đề cột (Đối tượng)</b> để sắp xếp. Tiêu đề được cố định khi cuộn.</p>
                <table class="dt-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th class="sortable" id="sort-doi_tuong">Đối tượng <span class="sort-icon">⇅</span></th>
                            <th>Kiểm tra Vị trí</th>
                            <th>Check Công suất/Mở port</th>
                            <th>Dung lượng (Thiết kế/Import)</th>
                            <th>Mã hộp (Thiết kế/Import)</th>
                            <th>Chi tiết</th>
                        </tr>
                    </thead>
                    <tbody id="dt-body"></tbody>
                </table>
                
                <script>
                    let dtData = {dt_json};
                    let currentSort = {{ column: null, direction: 'asc' }};
                    
                    function getSortValue(val) {{
                        if (!val) return "";
                        const str = String(val);
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
                    
                    function renderTable() {{
                        const tbody = document.getElementById('dt-body');
                        
                        let dataToRender = [...dtData];
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
                            
                            // Highlight logic: Skip red for "Lệch nhẹ" if no other critical errors
                            const allContent = r.doi_tuong + r.vi_tri + r.power + r.dung_luong + r.ma_hop + r.chi_tiet;
                            const hasCrit = allContent.includes('❌') || 
                                          ((allContent.includes('⚠️') || allContent.includes('Lệch')) && !r.vi_tri.includes('Lệch nhẹ'));
                            
                            if (hasCrit) {{
                                tr.classList.add('err-row');
                            }} else if (allContent.includes('✅') || allContent.includes('Khớp') || r.vi_tri.includes('Lệch nhẹ')) {{
                                tr.classList.add('ok-row');
                            }}
                            
                            tr.innerHTML = `
                                <td class="row-num">${{r.idx}}</td>
                                <td>${{r.doi_tuong}}</td>
                                <td>${{r.vi_tri}}</td>
                                <td>${{r.power}}</td>
                                <td>${{r.dung_luong}}</td>
                                <td>${{r.ma_hop}}</td>
                                <td class="chi-tiet">${{r.chi_tiet}}</td>
                            `;
                            tbody.appendChild(tr);
                        }});
                    }}
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
            else:
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
                        "diem_cuoi": str(row.get("Điểm cuối (Key)", "")),
                        "dung_luong": str(row.get("Dung lượng (TT/TK)", "")),
                        "loai": str(row.get("Loại (TT/TK)", "")),
                        "chieu_dai": str(row.get("Chiều dài (TT/TK)", "")),
                        "trang_thai": str(row.get("Trạng thái Lỗi", "")),
                        "chi_tiet": str(row.get("Chi tiết", ""))
                    })
                tc_json = _json_tc.dumps(tc_rows, ensure_ascii=False)
                
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
                        white-space: normal;
                        word-wrap: break-word;
                        min-width: 200px;
                    }}
                    table.tc-table tr {{ cursor: pointer; transition: background-color 0.15s; }}
                    table.tc-table tr:hover {{ background-color: #f0f4ff !important; }}
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
                <p class="tc-hint">💡 <b>Click vào hàng</b> để bôi vàng các tuyến sai điểm đầu thiết kế. Click vào <b>Tiêu đề cột</b> (Tuyến cáp, Điểm đầu, Điểm cuối) để sắp xếp.</p>
                <table class="tc-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th class="sortable" id="sort-tuyen_cap">Tuyến cáp <span class="sort-icon">⇅</span></th>
                            <th class="sortable" id="sort-diem_dau">Điểm đầu <span class="sort-icon">⇅</span></th>
                            <th class="sortable" id="sort-diem_cuoi">Điểm cuối (Key) <span class="sort-icon">⇅</span></th>
                            <th>Dung lượng (TT/TK)</th>
                            <th>Loại (TT/TK)</th>
                            <th>Chiều dài (TT/TK)</th>
                            <th>Trạng thái Lỗi</th>
                            <th>Chi tiết</th>
                        </tr>
                    </thead>
                    <tbody id="tc-body"></tbody>
                </table>
                
                <script>
                    let tcData = {tc_json};
                    const storageKey = "tc_highlighted_{_upload_id_tc}";
                    let currentSort = {{ column: null, direction: 'asc' }};
                    
                    // Load highlighted rows from localStorage
                    let highlightedSet = new Set();
                    try {{
                        const saved = localStorage.getItem(storageKey);
                        if (saved) highlightedSet = new Set(JSON.parse(saved));
                    }} catch(e) {{}}
                    
                    function saveHighlighted() {{
                        localStorage.setItem(storageKey, JSON.stringify([...highlightedSet]));
                        syncToBridge();
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
                                            chieu_dai: r.chieu_dai,
                                            trang_thai: r.trang_thai,
                                            chi_tiet_orig: r.chi_tiet
                                        }});
                                    }}
                                }});
                                localStorage.setItem("tc_errors_{_upload_id_tc}", JSON.stringify(tcPayload));
                            }}
                        }} catch(e) {{}}
                    }}

                    function getSortValue(val) {{
                        if (!val) return "";
                        const str = String(val);
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
                        const tbody = document.getElementById('tc-body');
                        
                        let dataToRender = [...tcData];
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

                        tbody.innerHTML = '';
                        dataToRender.forEach(r => {{
                            const tr = document.createElement('tr');
                            const isHL = highlightedSet.has(r.idx);
                            
                            if (isHL) tr.classList.add('highlighted');
                            else if (r.trang_thai.includes('❌') || r.trang_thai.includes('Sai') || r.trang_thai.includes('Lệch')) tr.classList.add('err-row');
                            else if (r.trang_thai.includes('✅') || r.trang_thai.includes('Khớp')) tr.classList.add('ok-row');
                            
                            let chiTiet = r.chi_tiet || '';
                            if (isHL) {{
                                chiTiet = chiTiet ? chiTiet + '; Sai điểm đầu' : 'Sai điểm đầu';
                            }}
                            
                            tr.innerHTML = `
                                <td class="row-num">${{r.idx}}</td>
                                <td>${{r.tuyen_cap}}</td>
                                <td>${{r.diem_dau}}</td>
                                <td>${{r.diem_cuoi}}</td>
                                <td>${{r.dung_luong}}</td>
                                <td>${{r.loai}}</td>
                                <td>${{r.chieu_dai}}</td>
                                <td>${{r.trang_thai}}</td>
                                <td class="chi-tiet">${{chiTiet}}</td>
                            `;
                            
                            tr.addEventListener('click', (e) => {{
                                // Prevent toggle if clicking on a button or something (though there aren't any)
                                if (highlightedSet.has(r.idx)) {{
                                    highlightedSet.delete(r.idx);
                                }} else {{
                                    highlightedSet.add(r.idx);
                                }}
                                saveHighlighted();
                                renderTable();
                            }});
                            
                            tbody.appendChild(tr);
                        }});
                    }}
                    
                    renderTable();
                    syncToBridge();
                </script>
                </body>
                </html>
                """
                st.components.v1.html(tc_html, height=620, scrolling=True)
                
                fn_tc = f"Result_TuyenCap_{datetime.now().strftime('%H%M')}.xlsx"
                st.download_button("📥 Tải Excel", to_excel(res_tuyen_cap), fn_tc, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        # --- Tab Hàn nối: Interactive Sort & Sticky Header ---
        with t3:
            if res_han_noi.empty:
                st.info("Chưa có kết quả (Thiếu dữ liệu đầu vào).")
            else:
                res_han_noi.index = range(1, len(res_han_noi) + 1)
                import json as _json_hn
                
                # Convert dataframe to list of dicts for JS
                hn_rows = []
                for idx, row in res_han_noi.iterrows():
                    # Format as int string per request
                    sl_tk = row.get("SL Thiết kế", 0)
                    sl_tt = row.get("SL Thực tế", 0)
                    sl_tk_str = str(int(sl_tk)) if sl_tk == int(sl_tk) else f"{sl_tk:g}"
                    sl_tt_str = str(int(sl_tt)) if sl_tt == int(sl_tt) else f"{sl_tt:g}"
                    
                    hn_rows.append({
                        "idx": idx,
                        "vi_tri": str(row.get("Vị trí", "")),
                        "sl_tk": sl_tk_str,
                        "sl_tt": sl_tt_str,
                        "trang_thai": str(row.get("Trạng thái Lỗi", "")),
                        "chi_tiet": str(row.get("Chi tiết", ""))
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
                    table.hn-table th.sortable {{
                        cursor: pointer;
                        user-select: none;
                    }}
                    table.hn-table th.sortable:hover {{
                        background-color: #ebf0f5;
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
                        white-space: normal;
                        word-wrap: break-word;
                        min-width: 250px;
                    }}
                    table.hn-table tr {{ transition: background-color 0.15s; }}
                    table.hn-table tr:hover {{ background-color: #f0f4ff !important; }}
                    table.hn-table tr.err-row {{ background-color: #ffe0e0; }}
                    table.hn-table tr.ok-row {{ background-color: #e6f9e6; }}
                    .hn-hint {{ font-size: 13px; color: #555; margin-bottom: 8px; }}
                    .sort-icon {{ font-size: 11px; margin-left: 5px; opacity: 0.6; }}
                </style>
                </head>
                <body>
                <p class="hn-hint">💡 Click vào <b>Tiêu đề cột (Vị trí)</b> để sắp xếp. Tiêu đề được cố định khi cuộn.</p>
                <table class="hn-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th class="sortable" id="sort-vi_tri">Vị trí <span class="sort-icon">⇅</span></th>
                            <th>SL Thiết kế</th>
                            <th>SL Thực tế</th>
                            <th>Trạng thái Lỗi</th>
                            <th>Chi tiết</th>
                        </tr>
                    </thead>
                    <tbody id="hn-body"></tbody>
                </table>
                
                <script>
                    let hnData = {hn_json};
                    let currentSort = {{ column: null, direction: 'asc' }};
                    
                    function getSortValue(val) {{
                        if (!val) return "";
                        const str = String(val);
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

                    document.getElementById('sort-vi_tri').addEventListener('click', () => handleSort('vi_tri'));
                    
                    function renderTable() {{
                        const tbody = document.getElementById('hn-body');
                        
                        let dataToRender = [...hnData];
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
                            
                            // Highlight logic
                            if (r.trang_thai.includes('❌') || r.trang_thai.includes('Lệch')) {{
                                tr.classList.add('err-row');
                            }} else if (r.trang_thai.includes('✅') || r.trang_thai.includes('Khớp')) {{
                                tr.classList.add('ok-row');
                            }}
                            
                            tr.innerHTML = `
                                <td class="row-num">${{r.idx}}</td>
                                <td>${{r.vi_tri}}</td>
                                <td>${{r.sl_tk}}</td>
                                <td>${{r.sl_tt}}</td>
                                <td>${{r.trang_thai}}</td>
                                <td class="chi-tiet">${{r.chi_tiet}}</td>
                            `;
                            tbody.appendChild(tr);
                        }});
                    }}
                    renderTable();
                </script>
                </body>
                </html>
                """
                st.components.v1.html(hn_html, height=620, scrolling=True)
                
                fn_hn = f"Result_HanNoi_{datetime.now().strftime('%H%M')}.xlsx"
                st.download_button("📥 Tải Excel", to_excel(res_han_noi), fn_hn, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # --- Tab Vật tư: Interactive Sort & Sticky Header ---
        with t4:
            if res_vat_tu.empty:
                st.info("Chưa có kết quả (Thiếu dữ liệu đầu vào).")
            else:
                res_vat_tu.index = range(1, len(res_vat_tu) + 1)
                import json as _json_vt
                
                # Convert dataframe to list of dicts for JS
                vt_rows = []
                for idx, row in res_vat_tu.iterrows():
                    # Format quantities as integers if possible
                    sl_tk = row.get("SL Thiết kế", 0)
                    sl_nt = row.get("SL Nghiệm thu", 0)
                    sl_tk_str = str(int(sl_tk)) if sl_tk == int(sl_tk) else f"{sl_tk:g}"
                    sl_nt_str = str(int(sl_nt)) if sl_nt == int(sl_nt) else f"{sl_nt:g}"
                    
                    vt_rows.append({
                        "idx": idx,
                        "ma_vt": str(row.get("Mã vật tư", "")),
                        "ten_vt": str(row.get("Tên vật tư", "")),
                        "tinh_trang": str(row.get("Tình trạng hàng", "")),
                        "sl_tk": sl_tk_str,
                        "sl_nt": sl_nt_str,
                        "trang_thai": str(row.get("Trạng thái Lỗi", "")),
                        "chi_tiet": str(row.get("Chi tiết", ""))
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
                <p class="vt-hint">💡 Click vào <b>Tiêu đề cột (Mã vật tư, Tên vật tư)</b> để sắp xếp. Tiêu đề được cố định khi cuộn.</p>
                <table class="vt-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th class="sortable" id="sort-ma_vt">Mã vật tư <span class="sort-icon">⇅</span></th>
                            <th class="sortable" id="sort-ten_vt">Tên vật tư <span class="sort-icon">⇅</span></th>
                            <th>Tình trạng hàng</th>
                            <th>SL Thiết kế</th>
                            <th>SL Nghiệm thu</th>
                            <th>Trạng thái Lỗi</th>
                            <th>Chi tiết</th>
                        </tr>
                    </thead>
                    <tbody id="vt-body"></tbody>
                </table>
                
                <script>
                    let vtData = {vt_json};
                    let currentSort = {{ column: null, direction: 'asc' }};
                    
                    function handleSort(col) {{
                        if (currentSort.column === col) {{
                            currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                        }} else {{
                            currentSort.column = col;
                            currentSort.direction = 'asc';
                        }}
                        
                        // Update UI icons
                        ['ma_vt', 'ten_vt'].forEach(id => {{
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

                    document.getElementById('sort-ma_vt').addEventListener('click', () => handleSort('ma_vt'));
                    document.getElementById('sort-ten_vt').addEventListener('click', () => handleSort('ten_vt'));
                    
                    function renderTable() {{
                        const tbody = document.getElementById('vt-body');
                        
                        let dataToRender = [...vtData];
                        if (currentSort.column) {{
                            dataToRender.sort((a, b) => {{
                                const valA = String(a[currentSort.column]).toLowerCase();
                                const valB = String(b[currentSort.column]).toLowerCase();
                                
                                // Try numeric sort for Mã vật tư if they are digits
                                if (currentSort.column === 'ma_vt') {{
                                    const numA = parseInt(valA);
                                    const numB = parseInt(valB);
                                    if (!isNaN(numA) && !isNaN(numB)) {{
                                        return currentSort.direction === 'asc' ? numA - numB : numB - numA;
                                    }}
                                }}
                                
                                return currentSort.direction === 'asc' 
                                    ? valA.localeCompare(valB) 
                                    : valB.localeCompare(valA);
                            }});
                        }}

                        tbody.innerHTML = '';
                        dataToRender.forEach(r => {{
                            const tr = document.createElement('tr');
                            
                            // Highlight logic
                            if (r.trang_thai.includes('❌') || r.trang_thai.includes('Lệch')) {{
                                tr.classList.add('err-row');
                            }} else if (r.trang_thai.includes('✅') || r.trang_thai.includes('Khớp')) {{
                                tr.classList.add('ok-row');
                            }}
                            
                            tr.innerHTML = `
                                <td class="row-num">${{r.idx}}</td>
                                <td>${{r.ma_vt}}</td>
                                <td class="ten-vt">${{r.ten_vt}}</td>
                                <td>${{r.tinh_trang}}</td>
                                <td>${{r.sl_tk}}</td>
                                <td>${{r.sl_nt}}</td>
                                <td>${{r.trang_thai}}</td>
                                <td class="chi-tiet">${{r.chi_tiet}}</td>
                            `;
                            tbody.appendChild(tr);
                        }});
                    }}
                    renderTable();
                </script>
                </body>
                </html>
                """
                st.components.v1.html(vt_html, height=620, scrolling=True)
                
                fn_vt = f"Result_VatTu_{datetime.now().strftime('%H%M')}.xlsx"
                st.download_button("📥 Tải Excel", to_excel(res_vat_tu), fn_vt, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


        with t5:
            # Lấy Session ID để reset bảng nếu up file mới
            upload_session_id = st.session_state.get('upload_session_id', 'default_session_id')
            
            # 1. Trích xuất dữ liệu mảng để JS có thể tra cứu
            qa_logic_instance = get_qa_logic()
            lookup_list = []
            if not res_han_noi.empty:
                for _, hn_row in res_han_noi.iterrows():
                    vitri = str(hn_row.get("Vị trí", ""))
                    if not vitri or vitri.lower() == 'nan': continue
                    sl_tt = qa_logic_instance._safe_num(hn_row.get("SL Thực tế", 0))
                    val_tt = str(int(sl_tt)) if sl_tt == int(sl_tt) else str(sl_tt)
                    lookup_list.append({
                        "vitri_lower": vitri.lower(),
                        "vitri": vitri.upper(),
                        "sl": val_tt
                    })
            
            import json
            lookup_json = json.dumps(lookup_list)
            
            # 2. Tạo Table HTML & JS (Hoạt động offline siêu mượt như Excel thực thụ)
            html_code = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <style>
                .excel-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
                    margin-top: 10px;
                }}
                .excel-table th, .excel-table td {{
                    border: 1px solid #d0d7de;
                    padding: 0;
                    margin: 0;
                }}
                .excel-table th {{
                    background-color: #f6f8fa;
                    padding: 10px;
                    text-align: center;
                    font-weight: 600;
                    color: #24292f;
                    font-size: 14px;
                    position: sticky;
                    top: 0;
                    z-index: 10;
                }}
                .excel-table td.row-num {{
                    background-color: #f6f8fa;
                    text-align: center;
                    width: 40px;
                    color: #57606a;
                    font-size: 14px;
                }}
                .cell-input {{
                    width: 100%;
                    box-sizing: border-box;
                    border: none;
                    padding: 10px;
                    font-size: 14px;
                    text-align: center;
                    outline: none;
                    background-color: #ffffff;
                }}
                .cell-input:focus {{
                    box-shadow: inset 0 0 0 2px #0969da;
                    background-color: #f0f7ff;
                }}
                .readonly-cell {{
                    padding: 10px;
                    font-size: 14px;
                    color: #24292f;
                    min-height: 20px;
                    background-color: #fbfbfb;
                    white-space: nowrap;
                    overflow: hidden;
                    text-align: center;
                    text-overflow: ellipsis;
                    cursor: pointer;
                    user-select: none;
                }}
                .not-found {{
                    color: #cf222e;
                    font-style: italic;
                }}
                .suspicious .readonly-cell{{
                    background-color: #ffeeb2 !important;
                    font-weight: bold;
                    color: #995c00;
                }}
            </style>
            </head>
            <body style="margin: 0; background: white; padding: 10px;">
            <p style="font-size: 14px; color: #57606a; margin-top: 0; margin-bottom: 10px;">💡 <b>Hướng dẫn:</b> Nhập mã đối tượng (1, 2, 3 ký tự hộp) vào cột <b>Nhập đối tượng</b> (nhấn Enter để xuống dòng tự động).<br/>Nếu thấy kết quả đáng ngờ, hãy <b>Click 1 lần vào cột Kết quả</b> (Đối tượng từ hàn nối) để bôi vàng. Dữ liệu bôi vàng sẽ được xuất ra ở <b>Tab Số liệu sai lệch</b>.</p>
            <table class="excel-table" id="manual-table">
                <thead>
                    <tr>
                        <th style="width: 40px; text-align: center;">#</th>
                        <th style="width: 1%; white-space: nowrap; padding: 10px 20px; text-align: center;">Nhập đối tượng</th>
                        <th style="width: 1%; white-space: nowrap; padding: 10px 20px; text-align: center;">Mối hàn từ hàn nối</th>
                        <th style="width: 1%; white-space: nowrap; padding: 10px 20px; text-align: center;">Đối tượng từ hàn nối</th>
                        <th style="width: auto; text-align: center;">Ghi chú</th>
                    </tr>
                </thead>
                <tbody id="table-body">
                </tbody>
            </table>
            
            <script>
                const lookupData = {lookup_json};
                const uploadSessionId = "{upload_session_id}";
                const tbody = document.getElementById('table-body');
                let rowCount = 0;
                
                function saveData() {{
                    let rowsData = [];
                    document.querySelectorAll('#manual-table tbody tr').forEach((tr) => {{
                        let inputs = tr.querySelectorAll('input.cell-input');
                        if (inputs.length === 2 && (inputs[0].value || inputs[1].value || tr.classList.contains('suspicious'))) {{
                            let hanoi = tr.querySelector('td:nth-child(3) div').innerText;
                            let obj = tr.querySelector('td:nth-child(4) div').innerText;
                            rowsData.push({{
                                idx: parseInt(inputs[0].dataset.row),
                                input_val: inputs[0].value,
                                hanoi_val: hanoi,
                                obj_val: obj,
                                note_val: inputs[1].value,
                                suspicious: tr.classList.contains('suspicious')
                            }});
                        }}
                    }});
                    localStorage.setItem("manual_splicing_" + uploadSessionId, JSON.stringify(rowsData));
                }}
                
                function processInputLogic(inputEl, val, checkDuplicate) {{
                    const row = parseInt(inputEl.dataset.row);
                    const hanoiEl = document.getElementById('hanoi-' + row);
                    const objEl = document.getElementById('obj-' + row);
                    
                    if (!val) {{
                        hanoiEl.innerText = '';
                        objEl.innerText = '';
                        objEl.classList.remove('not-found');
                        return;
                    }}
                    
                    let searchStr = val.toLowerCase();
                    if (/^\\d+$/.test(val) && val.length <= 4) {{
                        searchStr = val.padStart(4, '0');
                    }}
                    
                    // Check duplicate
                    if (checkDuplicate) {{
                        let isDuplicate = false;
                        document.querySelectorAll('input.cell-input[data-obj="true"]').forEach(other => {{
                            if (other !== inputEl && other.value.trim() !== '') {{
                                let otherVal = other.value.trim().toLowerCase();
                                let otherSearchStr = otherVal;
                                if (/^\\d+$/.test(otherVal) && otherVal.length <= 4) {{
                                    otherSearchStr = otherVal.padStart(4, '0');
                                }}
                                if (searchStr === otherSearchStr) {{
                                    isDuplicate = true;
                                }}
                            }}
                        }});
                        
                        if (isDuplicate) {{
                            alert("Bị trùng! Giá trị '" + val + "' đã được nhập ở vị trí khác.");
                            inputEl.value = '';
                            hanoiEl.innerText = '';
                            objEl.innerText = '';
                            objEl.classList.remove('not-found');
                            setTimeout(() => inputEl.focus(), 10);
                            return;
                        }}
                    }}
                    
                    let foundItem = lookupData.find(item => item.vitri_lower.includes(searchStr));
                    
                    if (foundItem) {{
                        hanoiEl.innerText = foundItem.sl;
                        objEl.innerText = foundItem.vitri;
                        objEl.classList.remove('not-found');
                    }} else {{
                        hanoiEl.innerText = '0';
                        objEl.innerText = 'Không tìm thấy';
                        objEl.classList.add('not-found');
                    }}
                    
                    if (row === rowCount && val) {{
                        addRow();
                    }}
                }}
                
                function addRow() {{
                    rowCount++;
                    const tr = document.createElement('tr');
                    
                    const tdNum = document.createElement('td');
                    tdNum.className = 'row-num';
                    tdNum.innerText = rowCount;
                    
                    const tdInput = document.createElement('td');
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.className = 'cell-input';
                    input.dataset.row = rowCount;
                    input.dataset.obj = "true";
                    tdInput.appendChild(input);
                    
                    const tdHanoi = document.createElement('td');
                    const divHanoi = document.createElement('div');
                    divHanoi.className = 'readonly-cell';
                    divHanoi.id = 'hanoi-' + rowCount;
                    tdHanoi.appendChild(divHanoi);
                    
                    const tdObj = document.createElement('td');
                    const divObj = document.createElement('div');
                    divObj.className = 'readonly-cell';
                    divObj.id = 'obj-' + rowCount;
                    divObj.title = "Click để đánh dấu nghi ngờ sai lệch";
                    tdObj.appendChild(divObj);
                    
                    // Click to mark suspicious
                    divObj.addEventListener('click', function() {{
                        const trParent = this.closest('tr');
                        // Chỉ cho phép đánh dấu nếu đã có kết quả (khác trống)
                        if (this.innerText.trim() !== '') {{
                            trParent.classList.toggle('suspicious');
                            saveData();
                        }}
                    }});
                    
                    const tdNote = document.createElement('td');
                    const inputNote = document.createElement('input');
                    inputNote.type = 'text';
                    inputNote.className = 'cell-input';
                    inputNote.placeholder = "Nhập ghi chú...";
                    inputNote.addEventListener('input', saveData);
                    tdNote.appendChild(inputNote);
                    
                    tr.appendChild(tdNum);
                    tr.appendChild(tdInput);
                    tr.appendChild(tdHanoi);
                    tr.appendChild(tdObj);
                    tr.appendChild(tdNote);
                    
                    tbody.appendChild(tr);
                    
                    input.addEventListener('input', function(e) {{
                        processInputLogic(this, e.target.value.trim(), false);
                        saveData();
                    }});
                    
                    input.addEventListener('change', function(e) {{
                        processInputLogic(this, e.target.value.trim(), true);
                        saveData();
                    }});
                    
                    input.addEventListener('keydown', handleArrowKeys);
                    inputNote.addEventListener('keydown', handleArrowKeys);
                }}
                
                function handleArrowKeys(e) {{
                    const row = parseInt(this.dataset.row || this.closest('tr').rowIndex);
                    const isNote = !this.dataset.row;
                    
                    if (e.key === 'Enter') {{
                        e.preventDefault();
                        // Tìm ô "Nhập đối tượng" trống đầu tiên trong toàn bộ bảng
                        const allRows = document.querySelectorAll('table.excel-table tbody tr');
                        let found = false;
                        for (let i = 0; i < allRows.length; i++) {{
                            const inp = allRows[i].querySelector('input.cell-input[data-row]');
                            if (inp && inp.value.trim() === '') {{
                                inp.focus();
                                found = true;
                                break;
                            }}
                        }}
                        if (!found) {{
                            // Nếu tất cả đã nhập, nhảy đến dòng tiếp theo
                            const nextTr = document.querySelector('tr:nth-child(' + (row + 1) + ')');
                            if (nextTr) {{
                                const inputs = nextTr.querySelectorAll('input.cell-input');
                                if (inputs[0]) inputs[0].focus();
                            }}
                        }}
                    }} else if (e.key === 'ArrowDown') {{
                        e.preventDefault();
                        const nextTr = document.querySelector('tr:nth-child(' + (row + 1) + ')');
                        if (nextTr) {{
                            const inputs = nextTr.querySelectorAll('input.cell-input');
                            if(isNote && inputs[1]) inputs[1].focus();
                            else if(!isNote && inputs[0]) inputs[0].focus();
                        }}
                    }} else if (e.key === 'ArrowUp') {{
                        e.preventDefault();
                        if (row > 1) {{
                            const prevTr = document.querySelector('tr:nth-child(' + (row - 1) + ')');
                            if (prevTr) {{
                                const inputs = prevTr.querySelectorAll('input.cell-input');
                                if(isNote && inputs[1]) inputs[1].focus();
                                else if(!isNote && inputs[0]) inputs[0].focus();
                            }}
                        }}
                    }}
                }}
                
                function restoreData() {{
                    let saved = localStorage.getItem("manual_splicing_" + uploadSessionId);
                    if(saved) {{
                        try {{
                            let rowsData = JSON.parse(saved);
                            if (rowsData.length === 0) {{
                                if (rowCount === 0) addRow();
                                return;
                            }}
                            
                            let maxRow = 1;
                            rowsData.forEach(r => {{ if (r.idx > maxRow) maxRow = r.idx; }});
                            
                            while(rowCount < maxRow) {{ addRow(); }}
                            
                            rowsData.forEach(rData => {{
                                let tr = tbody.rows[rData.idx - 1];
                                if(tr) {{
                                    let inputs = tr.querySelectorAll('input.cell-input');
                                    if(inputs.length === 2) {{
                                        inputs[0].value = rData.input_val || "";
                                        inputs[1].value = rData.note_val || "";
                                        if (rData.suspicious) {{
                                            tr.classList.add('suspicious');
                                        }} else {{
                                            tr.classList.remove('suspicious');
                                        }}
                                        processInputLogic(inputs[0], rData.input_val || "", false);
                                    }}
                                }}
                            }});
                            // Add one empty row at the bottom if the last row has data
                            let lastTr = document.querySelector('tr:nth-child(' + maxRow + ')');
                            if (lastTr) {{
                                let inputs = lastTr.querySelectorAll('input.cell-input');
                                if (inputs[0] && inputs[0].value) addRow();
                            }}
                        }} catch(e) {{}}
                    }} else {{
                        if (rowCount === 0) addRow();
                    }}
                }}
                
                restoreData();
            </script>
            </body>
            </html>
            """
            # Tăng height lên để người dùng không phải cuộn nhiều bên ngoài cửa sổ con
            st.components.v1.html(html_code, height=800, scrolling=True)

    # --- PAGE 3: SỐ LIỆU SAI LỆCH (NEW) ---
    if nav == "Số liệu sai lệch":
        c_title, c_btn = st.columns([3, 1])
        c_title.title("⚠️ Tổng hợp Sai lệch")
        
        if not is_fully_loaded:
            st.warning("⚠️ Vui lòng upload đầy đủ 6 loại file trước.")
            st.stop()
            
        # --- READ SUSPICIOUS DATA ---
        import json as _json
        suspicious_df = None
        saved_rows = []
        _upload_id = st.session_state.get('upload_session_id', 'default_session_id')
        
        # Đọc dữ liệu từ sidebar bridge (vốn đã được đồng bộ từ Tab 5 qua JS)
        bridge_data = st.session_state.get('_sync_bridge_data', '')
        if bridge_data and len(bridge_data) > 2:
            try:
                saved_rows = _json.loads(bridge_data)
            except Exception:
                pass
        
        # Priority 3: Server fallback — JS component that reads localStorage and pushes to bridge
        if not saved_rows:
            st.components.v1.html(f"""
            <script>
            (function() {{
                const key = "manual_splicing_{_upload_id}";
                const saved = localStorage.getItem(key);
                if (saved && saved !== "[]" && saved.length > 2) {{
                    const parentDoc = window.parent.document;
                    const target = Array.from(parentDoc.querySelectorAll('input')).find(i =>
                        i.getAttribute('aria-label') === 'DataSync_Bridge'
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
            
            # Auto-rerun once to pick up the value after JS pushes it
            if not st.session_state.get('_sai_lech_auto_synced', False):
                st.session_state['_sai_lech_auto_synced'] = True
                import time as _time
                _time.sleep(0.8)  # Wait for JS to execute
                st.rerun()
        else:
            # Reset auto-sync flag when data is present (for next navigation cycle)
            st.session_state['_sai_lech_auto_synced'] = False
        
        # Build suspicious_df from rows marked as suspicious
        suspicious_list = []
        for rData in saved_rows:
            if rData.get('suspicious'):
                suspicious_list.append({
                    "Nhập đối tượng": rData.get('input_val', ''),
                    "Mối hàn từ hàn nối": rData.get('hanoi_val', ''),
                    "Đối tượng từ hàn nối": rData.get('obj_val', ''),
                    "Ghi chú": rData.get('note_val', '')
                })
        
        if suspicious_list:
            suspicious_df = pd.DataFrame(suspicious_list)
            suspicious_df.index = range(1, len(suspicious_df) + 1)
            suspicious_df.insert(0, "Hạng mục", "Han noi soat")
        
        if suspicious_df is not None and not suspicious_df.empty:
            errors_dict['Han noi soat'] = suspicious_df
            all_errors.append(suspicious_df)
        
        # --- READ HIGHLIGHTED TUYẾN CÁP ROWS ---
        # Use a second hidden bridge to sync tc_errors from localStorage
        st.markdown('<style>div.tc-bridge-wrapper { position: absolute; opacity: 0; height: 0; overflow: hidden; pointer-events: none; } div:has(> div > input[aria-label="TC_Bridge"]) { position: absolute; opacity: 0; height: 0; overflow: hidden; pointer-events: none; }</style>', unsafe_allow_html=True)
        tc_bridge_val = st.text_input("TC_Bridge", key="tc_bridge_input", label_visibility="collapsed")
        
        tc_highlighted_rows = []
        if tc_bridge_val and len(tc_bridge_val) > 2:
            try:
                tc_highlighted_rows = _json.loads(tc_bridge_val)
            except: pass
        
        if not tc_highlighted_rows:
            # JS fallback: read from localStorage directly
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
                        "Chiều dài (TT/TK)": r.get('chieu_dai', ''),
                        "Trạng thái Lỗi": r.get('trang_thai', ''),
                        "Chi tiết": chi_tiet
                    })
            if tc_err_list:
                tc_sai_lech_df = pd.DataFrame(tc_err_list)
                tc_sai_lech_df.insert(0, "Hạng mục", "TuyenCap")
                
                # Gộp vào TuyenCap đã có (nếu có)
                if 'TuyenCap' in errors_dict:
                    combined = errors_dict['TuyenCap']
                    # Cập nhật nội dung cho các dòng đã tồn tại hoặc thêm mới từ danh sách highlight
                    for _, new_row in tc_sai_lech_df.iterrows():
                        tuyen_val = str(new_row['Tuyến cáp'])
                        mask = (combined['Tuyến cáp'].astype(str) == tuyen_val)
                        if mask.any():
                            # Nếu đã tồn tại, cập nhật Chi tiết (đảm bảo thêm "Sai điểm đầu" nếu chưa có)
                            idx = combined[mask].index[0]
                            old_ct = str(combined.at[idx, 'Chi tiết'])
                            if "Sai điểm đầu" not in old_ct:
                                combined.at[idx, 'Chi tiết'] = (old_ct + '; Sai điểm đầu') if old_ct else 'Sai điểm đầu'
                        else:
                            # Nếu chưa tồn tại, thêm mới
                            combined = pd.concat([combined, pd.DataFrame([new_row])], ignore_index=True)
                    
                    combined.index = range(1, len(combined) + 1)
                    errors_dict['TuyenCap'] = combined
                    # Cập nhật trong all_errors
                    for i, e in enumerate(all_errors):
                        if not e.empty and str(e.iloc[0].get('Hạng mục', '')) == 'TuyenCap':
                            all_errors[i] = combined
                            break
                else:
                    tc_sai_lech_df.index = range(1, len(tc_sai_lech_df) + 1)
                    errors_dict['TuyenCap'] = tc_sai_lech_df
                    all_errors.append(tc_sai_lech_df)
        
        if errors_dict:
            with c_btn:
                st.write("") # Spacer
                st.write("")
                p_name = st.session_state.get('project_name', 'BaoCao')
                if not p_name: p_name = "BaoCao"
                fn = f"{p_name}_Check_truoc_NThu.xlsx"
                st.download_button("📥 Tải Báo cáo Tổng hợp", to_excel_multiple_sheets(errors_dict), fn, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        if not all_errors:
            st.success("🎉 Tuyệt vời! Không tìm thấy sai lệch nào trong dữ liệu.")
        else:
            st.markdown(f"Tìm thấy **{sum(len(e) for e in all_errors)}** sai lệch cần xử lý.")
            
            for edf in all_errors:
                if edf.empty: continue
                cat = str(edf.iloc[0].get('Hạng mục', 'Unknown'))
                
                # Special display for manual "Han noi soat" category
                is_manual = (cat == "Han noi soat" or ("Nhập đối tượng" in edf.columns and "Mối hàn từ hàn nối" in edf.columns))
                
                with st.expander(f"🔴 {cat} ({len(edf)} lỗi)", expanded=False):
                    if is_manual:
                        disp_df = edf.drop(columns=['Hạng mục'], errors='ignore').copy()
                        disp_df.index.name = "#"
                        
                        def highlight_han_noi(row):
                            return ['background-color: #ffeeb2 !important; font-weight: bold; color: #995c00 !important' if c in ["Mối hàn từ hàn nối", "Đối tượng từ hàn nối"] else '' for c in disp_df.columns]
                        
                        styled_edf = disp_df.style.apply(highlight_han_noi, axis=1)
                        styled_edf = styled_edf.set_properties(**{
                            'border': '1px solid #d0d7de', 
                            'padding': '10px'
                        })
                    else:
                        wrap_cols = [c for c in edf.columns if c in ["Kiểm tra Vị trí", "Chi tiết", "Tên vật tư"]]
                        nowrap_cols = [c for c in edf.columns if c not in wrap_cols]
                        
                        if 'Trạng thái Lỗi' in edf.columns:
                            styled_edf = edf.style.apply(highlight_rows, axis=1)
                        else:
                            styled_edf = edf.style
                            
                        styled_edf = styled_edf.set_properties(subset=nowrap_cols, **{'white-space': 'nowrap', 'overflow': 'hidden'})
                        if wrap_cols:
                            styled_edf = styled_edf.set_properties(subset=wrap_cols, **{'white-space': 'normal', 'word-wrap': 'break-word', 'min-width': '300px', 'max-width': '500px'})

                        # Format SL columns to 1 decimal place
                        sl_fmt = {c: "{:.1f}" for c in edf.columns if "SL" in c and edf[c].dtype in ['float64', 'float32']}
                        if sl_fmt:
                            styled_edf = styled_edf.format(sl_fmt)

                    with st.container(height=450, border=True):
                        st.table(styled_edf)


if __name__ == "__main__":
    main()
