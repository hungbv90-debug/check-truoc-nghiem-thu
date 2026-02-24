@echo off
setlocal
title Khoi chay QC Analytics - Ftels

:: =============================================================================
:: DIEU KHIEN AN/HIEN CUA SO
:: =============================================================================
:: Neu dang chay o che do background (-silent), nhay den thuc thi app
if "%~1"=="-silent" goto :RUN_APP

:: Neu chua dung che do background, khoi chay lai chinh no o che do AN
echo [INFO] Dang khoi dong QC Analytics trong nen background...
mshta vbscript:CreateObject("Wscript.Shell").Run("""%~f0"" -silent",0)(window.close)&exit

:RUN_APP
cd /d "%~dp0"

:: --- Tự động giải 'Enable Editing' (Unblock) cho các file Excel trong thư mục ---
echo [INFO] Dang tu dong giai phong (Unblock) cac file Excel...
powershell -Command "Get-ChildItem -Recurse -Include *.xlsx,*.xls | Unblock-File" 2>nul

:: --- Giai phong cong 8501 neu dang bi chiem dung ---
echo [INFO] Dang kiem tra va giai phong cong 8501...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do (
    echo [INFO] Phat hien tien trinh %%a dang chiem cong 8501. Dang giai phong...
    taskkill /F /PID %%a >nul 2>&1
)
:: Cho mot chut de he thong giai phong hoan toan port
timeout /t 2 /nobreak >nul

:: --- Mo trinh duyet (Chi mo 1 lan duy nhat) ---
start "" "http://localhost:8501"

:: --- Thu cac cach chay Streamlit ---
echo [INFO] Dang khoi chay may chu...

:: Thu voi tung lenh, neu thanh cong thi exit luon
set ARGS=run app.py --server.port 8501 --server.headless=true --server.baseUrlPath="" --browser.gatherUsageStats=false

:: Cach 1: py -m streamlit (Thuong dung nhat tren Windows)
py -m streamlit %ARGS% >nul 2>&1
call :CHECK_SUCCESS

:: Cach 2: python -m streamlit
python -m streamlit %ARGS% >nul 2>&1
call :CHECK_SUCCESS

:: Cach 3: streamlit truc tiep
streamlit %ARGS% >nul 2>&1
call :CHECK_SUCCESS

:: =============================================================================
:: XU LY KHI CO LOI THUC SU
:: =============================================================================
:: Kiem tra lan cuoi truoc khi bao loi
netstat -aon | findstr :8501 | findstr LISTENING >nul
if %errorlevel% equ 0 exit /b

powershell -Command "Start-Process cmd -ArgumentList '/c color 0C & title LOI HE THONG & echo =================================================== & echo [LOI] KHONG THE KHOI DONG STREAMLIT & echo =================================================== & echo. & echo Nguyen nhan: Khong tim thay Python hoac Streamlit trong he thong. & echo. & echo Giai phap: & echo 1. Hay chac chan da cai Python (https://www.python.org/) & echo 2. Da chay lenh: pip install streamlit & echo. & pause' -WindowStyle Normal"
exit /b 1

:CHECK_SUCCESS
:: Ham kiem tra xem port 8501 da len chua
timeout /t 3 /nobreak >nul
netstat -aon | findstr :8501 | findstr LISTENING >nul
if %errorlevel% equ 0 (
    exit /b 0
)
goto :EOF

exit /b 1
