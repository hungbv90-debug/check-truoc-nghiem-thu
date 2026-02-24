# -*- coding: utf-8 -*-
"""
reconcile_engine.py — Module xử lý đối soát dữ liệu nghiệm thu viễn thông.
Sử dụng Pandas thuần túy. Không import Streamlit.

FPT Telecom — Ban Đảm bảo Chất lượng
"""

import pandas as pd
import numpy as np
from io import BytesIO
from typing import Optional, Tuple, Dict, List, Any, Union


# =============================================================================
# HÀM HỖ TRỢ (UTILITY FUNCTIONS)
# =============================================================================

def read_bbnt_excel(
    file: Any,
    keywords: Optional[List[str]] = None,
    sheet_name: int = 0
) -> pd.DataFrame:
    """
    Đọc file Excel BBNT có dòng metadata rác phía trên header thực tế.

    Logic:
        1. Đọc toàn bộ file không header (header=None, dtype=str).
        2. Duyệt từng dòng, tìm dòng chứa 1 trong các keyword.
        3. Lấy dòng đó làm header, bỏ dòng rác phía trên.

    Args:
        file: Đường dẫn file hoặc BytesIO object (từ Streamlit uploader).
        keywords: Danh sách keyword để nhận diện header row.
        sheet_name: Index sheet cần đọc (mặc định 0).

    Returns:
        pd.DataFrame đã cleaned với header đúng.

    Raises:
        ValueError: Nếu không tìm thấy header row nào phù hợp.
    """
    if keywords is None:
        keywords = ["STT", "Đối tượng", "Mã vật tư", "Tuyến cáp", "Mã đối tượng"]

    try:
        # Bước 1: Đọc raw — không header, tất cả là string
        raw = pd.read_excel(file, header=None, dtype=str, sheet_name=sheet_name)

        # Bước 2: Duyệt tìm header row
        header_row = None
        for idx, row in raw.iterrows():
            row_values = [str(v).strip() for v in row.values if pd.notna(v)]
            for kw in keywords:
                if any(kw in val for val in row_values):
                    header_row = idx
                    break
            if header_row is not None:
                break

        if header_row is None:
            raise ValueError(
                f"Không tìm thấy header row với keywords: {keywords}. "
                f"File có thể không đúng định dạng BBNT."
            )

        # Bước 3: Tái đọc — seekable check cho BytesIO
        if hasattr(file, 'seek'):
            file.seek(0)

        df = pd.read_excel(
            file,
            skiprows=int(header_row),
            dtype=str,
            sheet_name=sheet_name
        )

        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]

        # Loại bỏ dòng hoàn toàn rỗng
        df = df.dropna(how='all').reset_index(drop=True)

        # Loại bỏ dòng mà STT là NaN (nếu có cột STT) — thường là dòng tổng/footer
        if 'STT' in df.columns:
            df = df[df['STT'].notna()].reset_index(drop=True)

        return df

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Lỗi đọc file Excel: {str(e)}")


def read_design_excel(
    file: Any,
    sheet_name: int = 0
) -> pd.DataFrame:
    """
    Đọc file Thiết kế (thường có header ở dòng 1, không có metadata rác).
    Fallback: nếu header dòng 1 không hợp lệ, dùng read_bbnt_excel.

    Args:
        file: Đường dẫn file hoặc BytesIO object.
        sheet_name: Index sheet cần đọc.

    Returns:
        pd.DataFrame đã cleaned.
    """
    try:
        if hasattr(file, 'seek'):
            file.seek(0)

        df = pd.read_excel(file, dtype=str, sheet_name=sheet_name)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how='all').reset_index(drop=True)

        # Kiểm tra header có hợp lệ không (chứa ít nhất 1 keyword)
        valid_keywords = ["STT", "Đối tượng", "Mã", "Tuyến", "Tên"]
        header_valid = any(
            any(kw in str(col) for kw in valid_keywords)
            for col in df.columns
        )

        if not header_valid:
            # Fallback: thử smart detect
            if hasattr(file, 'seek'):
                file.seek(0)
            return read_bbnt_excel(file, sheet_name=sheet_name)

        return df

    except Exception as e:
        raise ValueError(f"Lỗi đọc file Thiết kế: {str(e)}")


def safe_num(val: Any) -> float:
    """Chuyển đổi giá trị sang float an toàn. Trả về 0.0 nếu lỗi."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return 0.0
    try:
        # Xử lý chuỗi có dấu phẩy (1,234.56 hoặc 1.234,56)
        s = str(val).strip().replace(',', '.')
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def normalize_text(val: Any) -> str:
    """Chuẩn hóa text: strip + lowercase để so sánh."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    return str(val).strip().lower()


def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """
    Tìm tên cột thực tế trong DataFrame khớp với danh sách tên ứng viên.
    So sánh case-insensitive, cho phép partial match.

    Args:
        df: DataFrame cần tìm.
        candidates: Danh sách tên cột ứng viên (ưu tiên exact match).

    Returns:
        Tên cột thực tế nếu tìm thấy, None nếu không.
    """
    df_cols_lower = {col.lower().strip(): col for col in df.columns}

    # Exact match (case-insensitive)
    for c in candidates:
        if c.lower().strip() in df_cols_lower:
            return df_cols_lower[c.lower().strip()]

    # Partial match (tên ứng viên chứa trong tên cột)
    for c in candidates:
        for col_lower, col_orig in df_cols_lower.items():
            if c.lower() in col_lower:
                return col_orig

    return None


def _build_summary(result_df: pd.DataFrame, status_col: str = "Kết quả") -> Dict[str, Any]:
    """
    Tạo dict tóm tắt từ DataFrame kết quả.

    Returns:
        {"total": int, "match": int, "mismatch": int, "missing": int, "rate": str}
    """
    total = len(result_df)
    match = len(result_df[result_df[status_col].str.contains("Khớp", na=False)])
    mismatch = len(result_df[result_df[status_col].str.contains("Lệch", na=False)])
    missing = len(result_df[result_df[status_col].str.contains("Thiếu", na=False)])

    rate = f"{(match / total * 100):.1f}%" if total > 0 else "0.0%"

    return {
        "total": total,
        "match": match,
        "mismatch": mismatch,
        "missing": missing,
        "rate": rate,
    }


# =============================================================================
# HÀM ĐỐI SOÁT CHÍNH (RECONCILIATION FUNCTIONS)
# =============================================================================

def reconcile_doi_tuong(
    df_tk: pd.DataFrame,
    df_bbnt: pd.DataFrame
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Đối soát Đối tượng: Thiết kế vs BBNT Đối tượng.

    Merge theo 'Mã đối tượng', so sánh:
    - Tên đối tượng
    - Loại đối tượng
    - Trạng thái

    Args:
        df_tk: DataFrame thiết kế.
        df_bbnt: DataFrame BBNT đối tượng.

    Returns:
        (result_df, summary_dict)
    """
    try:
        # Tìm cột merge key
        key_tk = _find_column(df_tk, ["Mã đối tượng", "Mã ĐT", "Ma doi tuong"])
        key_bbnt = _find_column(df_bbnt, ["Mã đối tượng", "Mã ĐT", "Ma doi tuong"])

        if not key_tk:
            raise ValueError("Không tìm thấy cột 'Mã đối tượng' trong file Thiết kế")
        if not key_bbnt:
            raise ValueError("Không tìm thấy cột 'Mã đối tượng' trong file BBNT Đối tượng")

        # Chuẩn hóa key
        df_tk = df_tk.copy()
        df_bbnt = df_bbnt.copy()
        df_tk['_key'] = df_tk[key_tk].apply(normalize_text)
        df_bbnt['_key'] = df_bbnt[key_bbnt].apply(normalize_text)

        # Merge
        merged = df_tk.merge(
            df_bbnt,
            on='_key',
            how='outer',
            suffixes=('_TK', '_BBNT'),
            indicator=True
        )

        # Xây dựng kết quả
        results = []
        for _, row in merged.iterrows():
            ma_dt = row.get(key_tk, row.get(f'{key_tk}_TK', row.get(f'{key_tk}_BBNT', '')))
            if pd.isna(ma_dt) or str(ma_dt).strip() == '':
                # Thử lấy từ cột có suffix
                for col in merged.columns:
                    if 'mã đối tượng' in col.lower() or 'mã đt' in col.lower():
                        if pd.notna(row[col]) and str(row[col]).strip():
                            ma_dt = row[col]
                            break

            errors = []
            merge_status = row['_merge']

            if merge_status == 'left_only':
                status = "⚠️ Thiếu (BBNT)"
                errors.append("Có trong Thiết kế nhưng thiếu trong BBNT")
            elif merge_status == 'right_only':
                status = "⚠️ Thiếu (TK)"
                errors.append("Có trong BBNT nhưng thiếu trong Thiết kế")
            else:
                # So sánh các trường
                # Tìm cột tên đối tượng
                ten_tk_col = _find_column(df_tk, ["Tên đối tượng", "Tên ĐT"])
                ten_bbnt_col = _find_column(df_bbnt, ["Tên đối tượng", "Tên ĐT"])

                if ten_tk_col and ten_bbnt_col:
                    tk_name_col = f'{ten_tk_col}_TK' if f'{ten_tk_col}_TK' in merged.columns else ten_tk_col
                    bbnt_name_col = f'{ten_bbnt_col}_BBNT' if f'{ten_bbnt_col}_BBNT' in merged.columns else ten_bbnt_col
                    if normalize_text(row.get(tk_name_col)) != normalize_text(row.get(bbnt_name_col)):
                        errors.append(f"Tên: TK='{row.get(tk_name_col)}' ≠ BBNT='{row.get(bbnt_name_col)}'")

                status = "❌ Lệch" if errors else "✅ Khớp"

            results.append({
                "Mã đối tượng": str(ma_dt).strip() if pd.notna(ma_dt) else "",
                "Kết quả": status,
                "Chi tiết lỗi": " | ".join(errors) if errors else ""
            })

        result_df = pd.DataFrame(results)
        summary = _build_summary(result_df)
        return result_df, summary

    except Exception as e:
        error_df = pd.DataFrame([{"Lỗi": str(e)}])
        return error_df, {"total": 0, "match": 0, "mismatch": 0, "missing": 0, "rate": "N/A", "error": str(e)}


def reconcile_cap(
    df_tk: pd.DataFrame,
    df_bbnt: pd.DataFrame
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Đối soát Cáp: Thiết kế vs BBNT Cáp.

    Merge theo 'Tuyến cáp', so sánh:
    - Loại cáp
    - Chiều dài

    Args:
        df_tk: DataFrame thiết kế.
        df_bbnt: DataFrame BBNT cáp.

    Returns:
        (result_df, summary_dict)
    """
    try:
        key_tk = _find_column(df_tk, ["Tuyến cáp", "Tên tuyến cáp", "Tuyến"])
        key_bbnt = _find_column(df_bbnt, ["Tuyến cáp", "Tên tuyến cáp", "Tuyến"])

        if not key_tk:
            raise ValueError("Không tìm thấy cột 'Tuyến cáp' trong file Thiết kế")
        if not key_bbnt:
            raise ValueError("Không tìm thấy cột 'Tuyến cáp' trong file BBNT Cáp")

        df_tk = df_tk.copy()
        df_bbnt = df_bbnt.copy()
        df_tk['_key'] = df_tk[key_tk].apply(normalize_text)
        df_bbnt['_key'] = df_bbnt[key_bbnt].apply(normalize_text)

        merged = df_tk.merge(
            df_bbnt,
            on='_key',
            how='outer',
            suffixes=('_TK', '_BBNT'),
            indicator=True
        )

        # Tìm cột loại cáp & chiều dài
        loai_tk = _find_column(df_tk, ["Loại cáp", "Loại"])
        loai_bbnt = _find_column(df_bbnt, ["Loại cáp", "Loại"])
        dai_tk = _find_column(df_tk, ["Chiều dài", "Chiều dài (m)", "Dài"])
        dai_bbnt = _find_column(df_bbnt, ["Chiều dài", "Chiều dài (m)", "Dài", "Chiều dài TT"])

        results = []
        for _, row in merged.iterrows():
            tuyen_cap = row.get(key_tk, row.get(f'{key_tk}_TK', row.get(f'{key_tk}_BBNT', '')))
            if pd.isna(tuyen_cap):
                for col in merged.columns:
                    if 'tuyến' in col.lower() or 'tuyen' in col.lower():
                        if pd.notna(row[col]):
                            tuyen_cap = row[col]
                            break

            errors = []
            merge_status = row['_merge']

            if merge_status == 'left_only':
                status = "⚠️ Thiếu (BBNT)"
                errors.append("Có trong Thiết kế nhưng thiếu trong BBNT")
            elif merge_status == 'right_only':
                status = "⚠️ Thiếu (TK)"
                errors.append("Có trong BBNT nhưng thiếu trong Thiết kế")
            else:
                # So sánh loại cáp
                if loai_tk and loai_bbnt:
                    col_tk = f'{loai_tk}_TK' if f'{loai_tk}_TK' in merged.columns else loai_tk
                    col_bbnt = f'{loai_bbnt}_BBNT' if f'{loai_bbnt}_BBNT' in merged.columns else loai_bbnt
                    if normalize_text(row.get(col_tk)) != normalize_text(row.get(col_bbnt)):
                        errors.append(
                            f"Loại cáp: TK='{row.get(col_tk)}' ≠ BBNT='{row.get(col_bbnt)}'"
                        )

                # So sánh chiều dài
                if dai_tk and dai_bbnt:
                    col_tk = f'{dai_tk}_TK' if f'{dai_tk}_TK' in merged.columns else dai_tk
                    col_bbnt = f'{dai_bbnt}_BBNT' if f'{dai_bbnt}_BBNT' in merged.columns else dai_bbnt
                    val_tk = safe_num(row.get(col_tk))
                    val_bbnt = safe_num(row.get(col_bbnt))
                    if val_tk != val_bbnt:
                        errors.append(
                            f"Chiều dài: TK={val_tk} ≠ BBNT={val_bbnt}"
                        )

                status = "❌ Lệch" if errors else "✅ Khớp"

            results.append({
                "Tuyến cáp": str(tuyen_cap).strip() if pd.notna(tuyen_cap) else "",
                "Kết quả": status,
                "Chi tiết lỗi": " | ".join(errors) if errors else ""
            })

        result_df = pd.DataFrame(results)
        summary = _build_summary(result_df)
        return result_df, summary

    except Exception as e:
        error_df = pd.DataFrame([{"Lỗi": str(e)}])
        return error_df, {"total": 0, "match": 0, "mismatch": 0, "missing": 0, "rate": "N/A", "error": str(e)}


def reconcile_vat_tu(
    df_bbnt: pd.DataFrame
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Đối soát Vật tư: So sánh SL thực tế vs SL thiết kế trong BBNT Vật tư.

    Group by 'Mã vật tư', sum 'SL thực tế' vs 'SL thiết kế'.

    Args:
        df_bbnt: DataFrame BBNT vật tư.

    Returns:
        (result_df, summary_dict)
    """
    try:
        col_ma = _find_column(df_bbnt, ["Mã vật tư", "Mã VT", "Ma vat tu"])
        col_sl_tt = _find_column(df_bbnt, ["SL thực tế", "SL TT", "Số lượng thực tế", "SL thực tế sử dụng"])
        col_sl_tk = _find_column(df_bbnt, ["SL thiết kế", "SL TK", "Số lượng thiết kế", "SL theo thiết kế"])
        col_ten = _find_column(df_bbnt, ["Tên vật tư", "Tên VT", "Diễn giải"])
        col_dvt = _find_column(df_bbnt, ["ĐVT", "Đơn vị tính", "Đơn vị"])

        if not col_ma:
            raise ValueError("Không tìm thấy cột 'Mã vật tư' trong file BBNT Vật tư")
        if not col_sl_tt:
            raise ValueError("Không tìm thấy cột 'SL thực tế' trong file BBNT Vật tư")
        if not col_sl_tk:
            raise ValueError("Không tìm thấy cột 'SL thiết kế' trong file BBNT Vật tư")

        df = df_bbnt.copy()
        df['_sl_tt'] = df[col_sl_tt].apply(safe_num)
        df['_sl_tk'] = df[col_sl_tk].apply(safe_num)

        # Group by mã vật tư
        agg_dict = {
            '_sl_tt': 'sum',
            '_sl_tk': 'first',  # SL thiết kế thường giống nhau cho cùng mã
        }
        if col_ten:
            agg_dict[col_ten] = 'first'
        if col_dvt:
            agg_dict[col_dvt] = 'first'

        grouped = df.groupby(col_ma).agg(agg_dict).reset_index()

        results = []
        for _, row in grouped.iterrows():
            sl_tt = row['_sl_tt']
            sl_tk = row['_sl_tk']
            chenh_lech = sl_tt - sl_tk
            errors = []

            if sl_tt != sl_tk:
                status = "❌ Lệch"
                direction = "thừa" if chenh_lech > 0 else "thiếu"
                errors.append(f"SL TT={sl_tt}, SL TK={sl_tk}, Chênh lệch={abs(chenh_lech)} ({direction})")
            else:
                status = "✅ Khớp"

            record = {
                "Mã vật tư": row[col_ma],
                "SL Thiết kế": sl_tk,
                "SL Thực tế": sl_tt,
                "Chênh lệch": chenh_lech,
                "Kết quả": status,
                "Chi tiết lỗi": " | ".join(errors) if errors else ""
            }
            if col_ten:
                record["Tên vật tư"] = row.get(col_ten, "")
            if col_dvt:
                record["ĐVT"] = row.get(col_dvt, "")

            results.append(record)

        result_df = pd.DataFrame(results)

        # Sắp xếp: Lệch lên trước
        result_df = result_df.sort_values(
            by='Kết quả',
            key=lambda x: x.map({"❌ Lệch": 0, "⚠️ Thiếu": 1, "✅ Khớp": 2}),
            na_position='last'
        ).reset_index(drop=True)

        summary = _build_summary(result_df)
        return result_df, summary

    except Exception as e:
        error_df = pd.DataFrame([{"Lỗi": str(e)}])
        return error_df, {"total": 0, "match": 0, "mismatch": 0, "missing": 0, "rate": "N/A", "error": str(e)}


def reconcile_han_noi(
    df_tk: pd.DataFrame,
    df_bbnt: pd.DataFrame
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Đối soát Hàn nối: Thiết kế vs BBNT Hàn nối.

    Merge theo 'Tên đối tượng' (TK) ↔ 'Vị trí' (BBNT), so sánh SL mối hàn.

    Args:
        df_tk: DataFrame thiết kế.
        df_bbnt: DataFrame BBNT hàn nối.

    Returns:
        (result_df, summary_dict)
    """
    try:
        key_tk = _find_column(df_tk, ["Tên đối tượng", "Tên ĐT", "Đối tượng", "Vị trí hàn"])
        key_bbnt = _find_column(df_bbnt, ["Vị trí", "Vị trí hàn", "Tên đối tượng", "Đối tượng"])

        if not key_tk:
            raise ValueError("Không tìm thấy cột 'Tên đối tượng' trong file Thiết kế")
        if not key_bbnt:
            raise ValueError("Không tìm thấy cột 'Vị trí' trong file BBNT Hàn nối")

        col_sl_tk = _find_column(df_tk, ["SL mối hàn", "Số mối hàn", "SL hàn"])
        col_sl_bbnt = _find_column(df_bbnt, ["SL Thực tế", "SL thực tế", "SL TT", "Số mối hàn TT"])

        df_tk = df_tk.copy()
        df_bbnt = df_bbnt.copy()
        df_tk['_key'] = df_tk[key_tk].apply(normalize_text)
        df_bbnt['_key'] = df_bbnt[key_bbnt].apply(normalize_text)

        merged = df_tk.merge(
            df_bbnt,
            on='_key',
            how='outer',
            suffixes=('_TK', '_BBNT'),
            indicator=True
        )

        results = []
        for _, row in merged.iterrows():
            vi_tri = row.get(key_tk, row.get(f'{key_tk}_TK', row.get(f'{key_bbnt}_BBNT', '')))
            if pd.isna(vi_tri):
                for col in merged.columns:
                    if 'vị trí' in col.lower() or 'đối tượng' in col.lower():
                        if pd.notna(row[col]):
                            vi_tri = row[col]
                            break

            errors = []
            merge_status = row['_merge']

            if merge_status == 'left_only':
                status = "⚠️ Thiếu (BBNT)"
                errors.append("Có trong Thiết kế nhưng thiếu trong BBNT")
            elif merge_status == 'right_only':
                status = "⚠️ Thiếu (TK)"
                errors.append("Có trong BBNT nhưng thiếu trong Thiết kế")
            else:
                if col_sl_tk and col_sl_bbnt:
                    c_tk = f'{col_sl_tk}_TK' if f'{col_sl_tk}_TK' in merged.columns else col_sl_tk
                    c_bbnt = f'{col_sl_bbnt}_BBNT' if f'{col_sl_bbnt}_BBNT' in merged.columns else col_sl_bbnt
                    val_tk = safe_num(row.get(c_tk))
                    val_bbnt = safe_num(row.get(c_bbnt))
                    if val_tk != val_bbnt:
                        errors.append(f"SL mối hàn: TK={val_tk} ≠ BBNT={val_bbnt}")

                status = "❌ Lệch" if errors else "✅ Khớp"

            results.append({
                "Vị trí": str(vi_tri).strip() if pd.notna(vi_tri) else "",
                "Kết quả": status,
                "Chi tiết lỗi": " | ".join(errors) if errors else ""
            })

        result_df = pd.DataFrame(results)
        summary = _build_summary(result_df)
        return result_df, summary

    except Exception as e:
        error_df = pd.DataFrame([{"Lỗi": str(e)}])
        return error_df, {"total": 0, "match": 0, "mismatch": 0, "missing": 0, "rate": "N/A", "error": str(e)}


def reconcile_formimport(
    df_import: pd.DataFrame,
    df_bbnt_dt: pd.DataFrame
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Đối soát FormImport vs BBNT Đối tượng.

    Merge theo 'Mã đối tượng', đối chiếu:
    - Thông tin port
    - Trạng thái
    - Công suất

    Args:
        df_import: DataFrame FormImport.
        df_bbnt_dt: DataFrame BBNT đối tượng.

    Returns:
        (result_df, summary_dict)
    """
    try:
        key_import = _find_column(df_import, ["Mã đối tượng", "Mã ĐT", "Ma doi tuong", "Mã"])
        key_bbnt = _find_column(df_bbnt_dt, ["Mã đối tượng", "Mã ĐT", "Ma doi tuong"])

        if not key_import:
            raise ValueError("Không tìm thấy cột 'Mã đối tượng' trong file FormImport")
        if not key_bbnt:
            raise ValueError("Không tìm thấy cột 'Mã đối tượng' trong file BBNT Đối tượng")

        df_import = df_import.copy()
        df_bbnt_dt = df_bbnt_dt.copy()
        df_import['_key'] = df_import[key_import].apply(normalize_text)
        df_bbnt_dt['_key'] = df_bbnt_dt[key_bbnt].apply(normalize_text)

        merged = df_import.merge(
            df_bbnt_dt,
            on='_key',
            how='outer',
            suffixes=('_IMP', '_BBNT'),
            indicator=True
        )

        # Tìm cột so sánh
        port_imp = _find_column(df_import, ["Port", "Số port", "Port gpon"])
        port_bbnt = _find_column(df_bbnt_dt, ["Port", "Số port", "Port gpon"])
        tt_imp = _find_column(df_import, ["Trạng thái", "Status", "TT"])
        tt_bbnt = _find_column(df_bbnt_dt, ["Trạng thái", "Status", "TT"])
        cs_imp = _find_column(df_import, ["Công suất", "Power", "Rx Power", "Công suất thu"])
        cs_bbnt = _find_column(df_bbnt_dt, ["Công suất", "Power", "Rx Power", "Công suất thu"])

        results = []
        for _, row in merged.iterrows():
            ma_dt = row.get(key_import, row.get(f'{key_import}_IMP', row.get(f'{key_bbnt}_BBNT', '')))
            if pd.isna(ma_dt):
                for col in merged.columns:
                    if 'mã đối tượng' in col.lower() or 'mã đt' in col.lower() or 'mã' == col.lower():
                        if pd.notna(row[col]):
                            ma_dt = row[col]
                            break

            errors = []
            merge_status = row['_merge']

            if merge_status == 'left_only':
                status = "⚠️ Thiếu (BBNT)"
                errors.append("Có trong FormImport nhưng thiếu trong BBNT")
            elif merge_status == 'right_only':
                status = "⚠️ Thiếu (Import)"
                errors.append("Có trong BBNT nhưng thiếu trong FormImport")
            else:
                # So sánh Port
                if port_imp and port_bbnt:
                    c_imp = f'{port_imp}_IMP' if f'{port_imp}_IMP' in merged.columns else port_imp
                    c_bbnt = f'{port_bbnt}_BBNT' if f'{port_bbnt}_BBNT' in merged.columns else port_bbnt
                    if normalize_text(row.get(c_imp)) != normalize_text(row.get(c_bbnt)):
                        errors.append(f"Port: Import='{row.get(c_imp)}' ≠ BBNT='{row.get(c_bbnt)}'")

                # So sánh Trạng thái
                if tt_imp and tt_bbnt:
                    c_imp = f'{tt_imp}_IMP' if f'{tt_imp}_IMP' in merged.columns else tt_imp
                    c_bbnt = f'{tt_bbnt}_BBNT' if f'{tt_bbnt}_BBNT' in merged.columns else tt_bbnt
                    if normalize_text(row.get(c_imp)) != normalize_text(row.get(c_bbnt)):
                        errors.append(f"Trạng thái: Import='{row.get(c_imp)}' ≠ BBNT='{row.get(c_bbnt)}'")

                # So sánh Công suất
                if cs_imp and cs_bbnt:
                    c_imp = f'{cs_imp}_IMP' if f'{cs_imp}_IMP' in merged.columns else cs_imp
                    c_bbnt = f'{cs_bbnt}_BBNT' if f'{cs_bbnt}_BBNT' in merged.columns else cs_bbnt
                    val_imp = safe_num(row.get(c_imp))
                    val_bbnt = safe_num(row.get(c_bbnt))
                    if val_imp != val_bbnt:
                        errors.append(f"Công suất: Import={val_imp} ≠ BBNT={val_bbnt}")

                status = "❌ Lệch" if errors else "✅ Khớp"

            results.append({
                "Mã đối tượng": str(ma_dt).strip() if pd.notna(ma_dt) else "",
                "Kết quả": status,
                "Chi tiết lỗi": " | ".join(errors) if errors else ""
            })

        result_df = pd.DataFrame(results)
        summary = _build_summary(result_df)
        return result_df, summary

    except Exception as e:
        error_df = pd.DataFrame([{"Lỗi": str(e)}])
        return error_df, {"total": 0, "match": 0, "mismatch": 0, "missing": 0, "rate": "N/A", "error": str(e)}


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================

def export_to_excel(
    results: Dict[str, Tuple[pd.DataFrame, Dict[str, Any]]],
    output_path: Optional[str] = None
) -> BytesIO:
    """
    Xuất toàn bộ kết quả đối soát ra file Excel multi-sheet.

    Args:
        results: Dict với key = tên tab, value = (result_df, summary_dict).
        output_path: Nếu cung cấp, lưu ra file. Nếu không, trả về BytesIO.

    Returns:
        BytesIO buffer chứa file Excel.
    """
    buffer = BytesIO()

    try:
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Sheet tổng hợp
            summary_rows = []
            for tab_name, (_, summary) in results.items():
                summary_rows.append({
                    "Hạng mục": tab_name,
                    "Tổng số": summary.get("total", 0),
                    "Khớp": summary.get("match", 0),
                    "Lệch": summary.get("mismatch", 0),
                    "Thiếu": summary.get("missing", 0),
                    "Tỷ lệ khớp": summary.get("rate", "N/A"),
                })
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Tổng hợp", index=False)

            # Sheet chi tiết từng hạng mục
            for tab_name, (df, _) in results.items():
                # Truncate sheet name to 31 chars (Excel limit)
                sheet_name = tab_name[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        buffer.seek(0)

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())
            buffer.seek(0)

        return buffer

    except Exception as e:
        raise ValueError(f"Lỗi xuất Excel: {str(e)}")
