# ⚡ QC Analytics — Hệ thống Đối soát Nghiệm thu Cáp quang

> **Phiên bản:** 2.5 | **Cập nhật:** 24/02/2026  
> **Đơn vị:** 
> **Framework:** QA Vertical Edition (KWSR Mapping)

---

## 📋 Mô tả

Công cụ tự động **đối soát số liệu nghiệm thu** hạ tầng cáp quang, so khớp giữa file **Thiết kế** và **Biên bản Nghiệm thu (BBNT)** để phát hiện sai lệch. Hệ thống sử dụng công nghệ **Hybrid GIS** để xác thực vị trí ngoại tuyến và trực tuyến.

### Các hạng mục kiểm tra chính:
| Hạng mục | Nội dung kiểm tra |
|---|---|
| 📦 **Đối tượng** | Tọa độ ↔ Địa chỉ (Hybrid GIS), Công suất/Mở port, Dung lượng bộ chia, Mã hộp |
| 🔗 **Tuyến cáp** | Dung lượng cáp, Loại cáp (Treo/Ngầm), Chiều dài, Điểm đầu/Điểm cuối |
| ⚡ **Hàn nối** | Số lượng mối hàn Thiết kế ↔ Thực tế, Đối soát hàn nối soát theo phối |
| 🛠 **Vật tư** | Số lượng Thiết kế ↔ Nghiệm thu theo mã vật tư, Tình trạng hàng |

---

## ✨ Tính năng nổi bật (v2.5)

1.  **🚀 Hybrid GIS Technology**: Kiểm tra ranh giới hành chính của 63 tỉnh thành Việt Nam **Offline** (không cần mạng) bằng GeoPandas. Tự động fallback sang API BigDataCloud khi cần chi tiết cấp Phường/Xã.
2.  **📥 Quản lý Template**: Tích hợp khu vực tải Template mẫu (6 loại file) ngay trong ứng dụng, có khả năng thu gọn (Expander) để tối ưu diện tích.
3.  **🎨 Giao diện Tối ưu**:
    *   Bố cục Split-view: Trạng thái hồ sơ bên trái ↔ Nhật ký xử lý bên phải.
    *   Compact UI: Giảm khoảng trắng thừa, tập trung vào dữ liệu.
    *   Interactive Sort: Sắp xếp thông minh dữ liệu Tuyến cáp/Hàn nối theo mã số tuyến.

---

## 🚀 Hướng dẫn cài đặt

### Bước 1: Cài đặt Python
- Tải và cài đặt Python (phiên bản ≥ 3.9) từ [python.org](https://www.python.org/).
- **Lưu ý:** Phải chọn ☑ **"Add Python to PATH"** trong quá trình cài đặt.

### Bước 2: Cài đặt thư viện (Chỉ làm lần đầu)
Mở **Command Prompt** tại thư mục dự án và chạy:
```cmd
pip install -r requirements.txt
```

### Bước 3: Khởi chạy ứng dụng
- **Cách 1**: Nhấp đúp vào file `Khoi_dong_QC_Analytics.bat`.
- **Cách 2**: Chạy lệnh `streamlit run app.py` trong Command Prompt.

Ứng dụng sẽ mở tại địa chỉ: **http://localhost:8501**

---

## 📂 Cấu trúc dự án

```text
Check_truoc_nghiem_thu/
│
├── 📄 app.py                       ← Giao diện chính (Streamlit UI)
├── 📄 data_processor.py            ← Engine xử lý logic & GIS
├── 📂 Templates/                   ← Kho chứa 6 file mẫu (Design & BBNT)
├── 📂 gis_data/                    ← Dữ liệu ranh giới Việt Nam (.geojson)
├── 📂 01_Inputs/                   ← Thư mục lưu minh chứng gốc
├── 📂 02_Process/                  ← Thư mục xử lý & Masking
├── 📂 03_Outputs/                  ← Thư mục xuất báo cáo sạch
└── 📄 requirements.txt             ← Danh sách thư viện (Pandas, GeoPandas, etc.)
```

---

## 🛡️ Nguyên tắc Bảo mật (QA Rules)

Dự án tuân thủ nghiêm ngặt quy trình **FPT Telecom QA Specialist**:
*   **Security First**: Mọi dữ liệu Level 3 (PII) phải được xử lý tại thư mục `02_Process/` và ẩn danh hóa (Masking).
*   **Evidence Based**: Kết quả kiểm định dựa trên dữ liệu thực chứng 100%.
*   **Read-Only Input**: Tuyệt đối không sửa đổi file gốc trong thư mục `01_Inputs/`.

---

## ❓ Giải quyết lỗi thường gặp

*   **Lỗi GeoPandas/Rtree**: Đảm bảo đã chạy đúng lệnh pip cài đặt ở Bước 2.
*   **Lỗi "Ngoài vùng VN"**: Kiểm tra lại tọa độ (Lat/Lon) trong file Excel có bị nhầm lẫn vị trí không.
*   **Giao diện bị chậm**: Streamlit tự động quản lý tài nguyên, nếu không sử dụng trong 10s hệ thống sẽ tự động tạm dừng để tiết kiệm CPU.


