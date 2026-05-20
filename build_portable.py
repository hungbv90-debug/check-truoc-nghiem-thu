# -*- coding: utf-8 -*-
"""
build_portable.py — Tu dong tai va cau hinh moi truong Python Portable.
Giup ung dung co the chay tren moi may tinh Windows ma khong can cai dat truoc.
"""

import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess

def main():
    print("=======================================================================")
    print("        CONG CU TU DONG DONG GOI PYTHON PORTABLE CHO GOI GPON")
    print("=======================================================================")
    print()
    
    # 1. Thiet lap thu muc
    base_dir = os.path.dirname(os.path.abspath(__file__))
    python_root = os.path.join(base_dir, "python")
    target_dir = os.path.join(python_root, "python")
    
    if os.path.exists(python_root):
        print("[INFO] Phat hien thu muc python cu. Dang don dep...")
        shutil.rmtree(python_root)
        
    os.makedirs(target_dir, exist_ok=True)
    
    # Thong so phien ban Python
    py_version = "3.10.11"
    zip_name = f"python-{py_version}-embed-amd64.zip"
    url = f"https://www.python.org/ftp/python/{py_version}/{zip_name}"
    zip_path = os.path.join(python_root, zip_name)
    
    # 2. Tai Python Embeddable
    print(f"[1/5] Dang tai phien ban Python {py_version} Embeddable tu python.org...")
    try:
        # Request voi User-Agent hop le
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("[INFO] Tai xuong thanh cong.")
    except Exception as e:
        print(f"[LOI] Khong the tai Python: {e}")
        return
        
    # 3. Giai nen Python
    print("[2/5] Dang giai nen Python vao thu muc ung dung...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        os.remove(zip_path)
        print("[INFO] Giai nen hoan tat.")
    except Exception as e:
        print(f"[LOI] Giai nen that bai: {e}")
        return
        
    # 4. Kich hoat site-packages trong file .pth
    print("[3/5] Dang cau hinh quy tac tim kiem thu vien (site-packages)...")
    pth_file = os.path.join(target_dir, "python310._pth")
    if os.path.exists(pth_file):
        try:
            with open(pth_file, "r") as f:
                lines = f.readlines()
            
            # Mo khoa dong 'import site' bang cach bo dau comment
            new_lines = []
            for line in lines:
                if "import site" in line or "#import site" in line:
                    new_lines.append("import site\n")
                else:
                    new_lines.append(line)
                    
            with open(pth_file, "w") as f:
                f.writelines(new_lines)
            print("[INFO] Cau hinh file .pth thanh cong.")
        except Exception as e:
            print(f"[LOI] Khong the cau hinh file .pth: {e}")
            return
    else:
        print("[CANH BAO] Khong tim thay file python310._pth!")
        
    # 5. Tai va cai dat pip
    print("[4/5] Dang tai va tich hop trinh quan ly pip...")
    get_pip_path = os.path.join(python_root, "get-pip.py")
    try:
        req = urllib.request.Request("https://bootstrap.pypa.io/get-pip.py", headers=headers)
        with urllib.request.urlopen(req) as response, open(get_pip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        # Chay python portable de tu cai pip cho chinh no
        py_exe = os.path.join(target_dir, "python.exe")
        subprocess.run([py_exe, get_pip_path], check=True)
        os.remove(get_pip_path)
        print("[INFO] Tich hop pip thanh cong.")
    except Exception as e:
        print(f"[LOI] Khong the tich hop pip: {e}")
        return
        
    # 6. Cai dat cac thu vien phu thuoc tu requirements.txt
    print("[5/5] Dang tai va cai dat cac thu vien (requirements.txt)... Vui long doi...")
    req_file = os.path.join(base_dir, "requirements.txt")
    if not os.path.exists(req_file):
        print(f"[LOI] Khong tim thay file requirements.txt tai {req_file}")
        return
        
    try:
        # Chay pip install bang python di dong
        py_exe = os.path.join(target_dir, "python.exe")
        subprocess.run([py_exe, "-m", "pip", "install", "-r", req_file, "--no-warn-script-location"], check=True)
        print("[INFO] Da cai dat day du cac thu vien.")
    except Exception as e:
        print(f"[LOI] Cai dat thu vien phu thuoc that bai: {e}")
        return
        
    print()
    print("=======================================================================")
    print("       QUA TRINH DONG GOI MOI TRUONG PORTABLE DA HOAN TAT!")
    print("=======================================================================")
    print(" Gio day, ban co the nen (ZIP) toan bo thu muc 'Doi_soat_GPON' nay lai.")
    print(" Va gui cho bat ky may tinh Windows 64-bit nao khac.")
    print(" May do chi can giai nen va bam double-click 'Khoi_dong_ung_dung.bat' la chay.")
    print("=======================================================================")

if __name__ == "__main__":
    main()
