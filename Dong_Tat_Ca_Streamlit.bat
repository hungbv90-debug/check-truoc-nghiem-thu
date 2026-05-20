@echo off
echo Đang đóng triệt để các ứng dụng cũ...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM streamlit.exe /T 2>nul
timeout /t 2 >nul

set PYTHONPATH=
set PYTHONHOME=

echo.
echo Đã đóng tất cả ứng dụng thành công!
timeout /t 3 >nul
exit
