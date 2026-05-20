# ⚡ PHÂN TÍCH ĐỐI SOÁT NGHIỆM THU

> **Phiên bản:** 2.5 | **Cập nhật:** 24/02/2026
> **Đơn vị:** Ban Đảm bảo Chất lượng — FPT Telecom
> **Framework:** QA Vertical Edition (KWSR Mapping)

---

## 🎯 Mục tiêu

Hệ thống được thiết kế nhằm **hỗ trợ đối soát nghiệm thu hạ tầng ngoại vi ()**, tự động so khớp dữ liệu giữa hồ sơ **Thiết kế** và **Biên bản Nghiệm thu (BBNT)** để phát hiện các sai lệch về cấu hình, vị trí và khối lượng vật tư.

### Các hạng mục kiểm tra chính:

| Hạng mục                | Nội dung kiểm tra                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------------- |
| 📦**Đối tượng** | Tọa độ ↔ Địa chỉ (Hybrid GIS), Công suất/Mở port, Dung lượng bộ chia, Mã hộp |
| 🔗**Tuyến cáp**   | Dung lượng cáp, Loại cáp (Treo/Ngầm), Chiều dài, Điểm đầu/Điểm cuối          |
| ⚡**Hàn nối**     | Số lượng mối hàn Thiết kế ↔ Thực tế |
| 🛠**Vật tư**      | Số lượng Thiết kế ↔ Nghiệm thu theo mã vật tư, Tình trạng hàng                 |

---

## ✨ Tính năng sản phẩm (v2.5)

1. **🚀 Hybrid GIS Technology**: Kiểm tra ranh giới hành chính của 63 tỉnh thành Việt Nam **Offline** (không cần mạng) bằng GeoPandas. Tự động fallback sang API BigDataCloud khi cần chi tiết cấp Phường/Xã.
2. **📥 Quản lý Template**: Tích hợp khu vực tải Template mẫu (6 loại file) ngay trong ứng dụng, có khả năng thu gọn (Expander) để tối ưu diện tích.
3. **🎨 Giao diện Tối ưu**:
   * Bố cục Split-view: Trạng thái hồ sơ bên trái ↔ Nhật ký xử lý bên phải.
   * Compact UI: Giảm khoảng trắng thừa, tập trung vào dữ liệu.
   * Interactive Sort: Sắp xếp thông minh dữ liệu Tuyến cáp/Hàn nối theo mã số tuyến.

---

## 📖 Hướng dẫn sử dụng

Để đạt hiệu quả đối soát cao nhất, người dùng nên tuân thủ các bước sau:

1. **Chuẩn bị dữ liệu**: Đảm bảo các file dữ liệu tuân thủ Template mẫu (có thể tải trực tiếp trong ứng dụng). Cần đủ 6 loại file: *Form Import, Thiết kế, BBNT Đối tượng, BBNT Tuyến cáp, BBNT Hàn nối, BBNT Vật tư*.
2. **Tải lên (Import)**: Truy cập menu **"Nhật ký & File"**, kéo thả đồng thời tất cả các file vào vùng upload.
3. **Kiểm tra trạng thái**: Theo dõi bảng **"Trạng thái Hồ sơ"**. Chỉ khi đủ 6/6 file được tích xanh ✅, hệ thống mới tự động chuyển sang bước phân tích.
4. **Xem chi tiết**: Tại tab **"Kết quả phân tích"**, kiểm tra các hạng mục sai lệch được tô màu (🔴 Lỗi, 🟡 Cảnh báo).
5. **Xuất báo cáo**: Chuyển sang tab **"Số liệu sai lệch"** để tải file Excel tổng hợp lỗi, phục vụ việc hiệu chỉnh hồ sơ.

---

## 🚀 Hướng dẫn cài đặt & Khởi vận

Hệ thống được tối ưu hóa để triển khai nhanh trên môi trường Windows:

1. **Cài đặt Python**: Tải bản [Python 3.10+](https://www.python.org/downloads/) và đảm bảo chọn **"Add Python to PATH"**.
2. **Khởi tạo môi trường**: Tại thư mục gốc, mở Terminal và chạy:
   ```bash
   pip install -r requirements.txt
   ```
3. **Khởi chạy**:
   * **Nhanh**: Nhấp đúp file `Khoi_dong_ung_dung.bat`.
   * **Thủ công**: Chạy lệnh `streamlit run app.py`.
   * Hệ thống tự động mở tại: `http://localhost:8501`

---

## 🛡️ Nguyên tắc Bảo mật (QA Rules)

Dự án tuân thủ nghiêm ngặt quy trình **FPT Telecom QA Specialist**:

* **Security First**: Mọi dữ liệu Level 3 (PII) phải được xử lý tại thư mục `02_Process/` và ẩn danh hóa (Masking).
* **Evidence Based**: Kết quả kiểm định dựa trên dữ liệu thực chứng 100%.
* **Read-Only Input**: Tuyệt đối không sửa đổi file gốc trong thư mục `01_Inputs/`.

---

## ❓ Giải quyết lỗi thường gặp

* **Lỗi GeoPandas/Rtree**: Đảm bảo đã chạy đúng lệnh pip cài đặt ở Bước 2.
* **Lỗi "Ngoài vùng VN"**: Kiểm tra lại tọa độ (Lat/Lon) trong file Excel có bị nhầm lẫn vị trí không.
* **Giao diện bị chậm**: Streamlit tự động quản lý tài nguyên, nếu không sử dụng trong 10s hệ thống sẽ tự động tạm dừng để tiết kiệm CPU.

---

*© 2026 Ban Đảm bảo Chất lượng — FPT Telecom*
