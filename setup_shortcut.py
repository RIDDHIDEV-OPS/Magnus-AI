import os
import subprocess
from pathlib import Path

import winreg
key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
desktop_raw, _ = winreg.QueryValueEx(key, "Desktop")
desktop = Path(os.path.expandvars(desktop_raw))
target_bat = Path(r"d:\Mark-LV-main\run_magnus.bat")
icon_path = Path(r"d:\Mark-LV-main\config\jarvis.ico")
shortcut_vbs = Path(r"d:\Mark-LV-main\make_shortcut.vbs")

vbs_code = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{desktop / 'Magnus AI.lnk'}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_bat}"
oLink.WorkingDirectory = "d:\\Mark-LV-main"
oLink.IconLocation = "{icon_path}, 0"
oLink.Description = "Magnus AI Desktop Voice Assistant"
oLink.Save
"""
shortcut_vbs.write_text(vbs_code, encoding="utf-8")
try:
    subprocess.run(["cscript", "//nologo", str(shortcut_vbs)], check=True)
    print("SUCCESS: Created 'Magnus AI' desktop shortcut!")
finally:
    if shortcut_vbs.exists():
        shortcut_vbs.unlink()
