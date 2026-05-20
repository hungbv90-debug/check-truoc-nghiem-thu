@echo off
setlocal
title He Thong Doi Soat GPON - Khoi Dong

cls
echo =======================================================================
echo               HE THONG DOI SOAT GPON - BAN DAM BAO CHAT LUONG
echo =======================================================================
echo.
echo [1/5] Dang kiem tra moi truong Python...

set PY_PROG=

:: 1. Kiem tra va uu tien Python Portable trong thu muc ung dung truoc
if exist "%~dp0python\python\python.exe" (
    set PY_PROG="%~dp0python\python\python.exe"
    echo [INFO] Phat hien va su dung Python Portable trong thu muc ung dung.
    goto START_STEPS
)

:: 2. Neu khong co, kiem tra python trong PATH he thong
python --version >nul 2>&1
if errorlevel 1 goto CHECK_DEFAULT

python -m streamlit --version >nul 2>&1
if errorlevel 1 goto CHECK_DEFAULT

set PY_PROG=python
echo [INFO] Phat hien va su dung Python va Streamlit tu he thong PATH.
goto START_STEPS

:CHECK_DEFAULT
:: 3. Kiem tra duong dan python mac dinh cua o dia
if exist "C:\Users\hungb\AppData\Local\Programs\Python\Python313\python.exe" (
    set PY_PROG="C:\Users\hungb\AppData\Local\Programs\Python\Python313\python.exe"
    echo [INFO] Phat hien va su dung Python 3.13 tai thu muc mac dinh cua he thong.
    goto START_STEPS
)

:: Neu khong tim thay python nao, thong bao loi va dung lai
color 0C
echo.
echo =======================================================================
echo [LOI] KHONG TIM THAY PYTHON HOAC STREAMLIT TRONG HE THONG!
echo =======================================================================
echo.
echo Huong dan khac phuc:
echo   1. Hay chac chan da tai va cai Python 3.10+ (https://www.python.org/)
echo   2. Hay chac chan da cai thu vien Streamlit bang cach mo CMD va chay:
echo      pip install streamlit
echo.
echo Nhan phim bat ky de thoat...
pause >nul
exit /b 1

:START_STEPS
:: 2. Tu dong mo khoa Excel trong thu muc du an
echo [2/5] Dang mo khoa (Unblock) cac tep Excel trong thu muc du an...
powershell -Command "Get-ChildItem -Path '%~dp0' -Recurse -Include *.xlsx,*.xls | Unblock-File" >nul 2>&1

:: 3. Giai phong cong 8501 neu dang bi trung
echo [3/5] Dang kiem tra va giai phong cong ket noi 8501...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do (
    echo [INFO] Phat hien tien trinh %%a dang chiem dung cong 8501. Dang giai phong...
    taskkill /F /PID %%a >nul 2>&1
)
:: Tri hoan 1 giay bang ping de cho he thong giai phong cong hoan toan
ping 127.0.0.1 -n 2 >nul

:: 4. Mo trinh duyet
echo [4/5] Dang tu dong mo trinh duyet web...
start "" "http://localhost:8501"

:: 5. Khoi chay Streamlit
echo [5/5] Dang ket noi may chu va khoi dong giao dien ung dung...
echo.
echo =======================================================================
echo   HE THONG DA KHOI CHAY THANH CONG!
echo   VUI LONG GIU CUA SO NAY TRONG SUOT QUA TRINH SU DUNG.
echo   De dong ung dung, chi can dong cua so CMD nay.
echo =======================================================================
echo.

%PY_PROG% -m streamlit run app.py --server.port 8501 --server.headless=true --server.baseUrlPath="" --browser.gatherUsageStats=false

if not errorlevel 1 goto END

color 0C
echo.
echo [LOI] Ung dung Streamlit bi dung dot ngot.
echo Vui long kiem tra log loi phia tren va bao lai cho admin.
echo.
pause

:END
exit /b 0
