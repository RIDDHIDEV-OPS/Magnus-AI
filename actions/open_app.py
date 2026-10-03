import os
import sys
from pathlib import Path
import time
import subprocess
import platform
import shutil

for _stream in ("stdout", "stderr"):
    try:
        _s = getattr(sys, _stream, None)
        if _s is not None and hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_SYSTEM = platform.system()

_APP_ALIASES: dict[str, dict[str, str]] = {
    # Browsers
    "chrome":             {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "google chrome":      {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "firefox":            {"Windows": "firefox",                 "Darwin": "Firefox",              "Linux": "firefox"},
    "edge":               {"Windows": "msedge",                  "Darwin": "Microsoft Edge",       "Linux": "microsoft-edge"},
    "brave":              {"Windows": "brave",                   "Darwin": "Brave Browser",        "Linux": "brave-browser"},
    "safari":             {"Windows": "msedge",                  "Darwin": "Safari",               "Linux": "firefox"},
    "opera":              {"Windows": "opera",                   "Darwin": "Opera",                "Linux": "opera"},

    # File Manager / Explorer
    "file manager":       {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "filemanager":        {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "file-manager":       {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "files":              {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "my files":           {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "my filemanager":     {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "my file manager":    {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "this pc":            {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "my computer":        {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "downloads":          {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "documents":          {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "explorer":           {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "file explorer":      {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "finder":             {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},

    # Messaging & Social
    "whatsapp":           {"Windows": "whatsapp:",               "Darwin": "WhatsApp",             "Linux": "whatsapp"},
    "telegram":           {"Windows": "Telegram",                "Darwin": "Telegram",             "Linux": "telegram"},
    "discord":            {"Windows": "Discord",                 "Darwin": "Discord",              "Linux": "discord"},
    "slack":              {"Windows": "Slack",                   "Darwin": "Slack",                "Linux": "slack"},
    "zoom":               {"Windows": "Zoom",                    "Darwin": "zoom.us",              "Linux": "zoom"},
    "teams":              {"Windows": "msteams",                 "Darwin": "Microsoft Teams",      "Linux": "teams"},
    "skype":              {"Windows": "skype",                   "Darwin": "Skype",                "Linux": "skype"},
    "signal":             {"Windows": "signal",                  "Darwin": "Signal",               "Linux": "signal"},
    "instagram":          {"Windows": "Instagram",               "Darwin": "Instagram",            "Linux": "firefox"},
    "tiktok":             {"Windows": "TikTok",                  "Darwin": "TikTok",               "Linux": "firefox"},
    "linkedin":           {"Windows": "LinkedIn",                "Darwin": "LinkedIn",             "Linux": "linkedin"},
    "linked in":          {"Windows": "LinkedIn",                "Darwin": "LinkedIn",             "Linux": "linkedin"},

    # Media & Entertainment
    "spotify":            {"Windows": "spotify:",                "Darwin": "Spotify",              "Linux": "spotify"},
    "vlc":                {"Windows": "vlc",                     "Darwin": "VLC",                  "Linux": "vlc"},
    "netflix":            {"Windows": "Netflix",                 "Darwin": "Netflix",              "Linux": "firefox"},
    "youtube":            {"Windows": "https://www.youtube.com", "Darwin": "https://www.youtube.com", "Linux": "https://www.youtube.com"},

    # Development & Office
    "vscode":             {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "visual studio code": {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "code":               {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "terminal":           {"Windows": "wt",                      "Darwin": "Terminal",             "Linux": "x-terminal-emulator"},
    "cmd":                {"Windows": "cmd.exe",                 "Darwin": "Terminal",             "Linux": "bash"},
    "powershell":         {"Windows": "powershell.exe",          "Darwin": "Terminal",             "Linux": "bash"},
    "postman":            {"Windows": "Postman",                 "Darwin": "Postman",              "Linux": "postman"},
    "git":                {"Windows": "git-bash",                "Darwin": "Terminal",             "Linux": "bash"},
    "figma":              {"Windows": "Figma",                   "Darwin": "Figma",                "Linux": "figma"},
    "blender":            {"Windows": "blender",                 "Darwin": "Blender",              "Linux": "blender"},
    "word":               {"Windows": "winword",                 "Darwin": "Microsoft Word",       "Linux": "libreoffice --writer"},
    "excel":              {"Windows": "excel",                   "Darwin": "Microsoft Excel",      "Linux": "libreoffice --calc"},
    "powerpoint":         {"Windows": "powerpnt",                "Darwin": "Microsoft PowerPoint", "Linux": "libreoffice --impress"},
    "libreoffice":        {"Windows": "soffice",                 "Darwin": "LibreOffice",          "Linux": "libreoffice"},
    "notepad":            {"Windows": "notepad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},
    "textedit":           {"Windows": "notepad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},

    # Windows Store & System Tools
    "store":              {"Windows": "ms-windows-store:",       "Darwin": "App Store",            "Linux": "snap-store"},
    "microsoft store":    {"Windows": "ms-windows-store:",       "Darwin": "App Store",            "Linux": "snap-store"},
    "app store":          {"Windows": "ms-windows-store:",       "Darwin": "App Store",            "Linux": "snap-store"},
    "windows store":      {"Windows": "ms-windows-store:",       "Darwin": "App Store",            "Linux": "snap-store"},
    "task manager":       {"Windows": "taskmgr.exe",             "Darwin": "Activity Monitor",     "Linux": "gnome-system-monitor"},
    "taskmgr":            {"Windows": "taskmgr.exe",             "Darwin": "Activity Monitor",     "Linux": "gnome-system-monitor"},
    "settings":           {"Windows": "ms-settings:",            "Darwin": "System Preferences",   "Linux": "gnome-control-center"},
    "calculator":         {"Windows": "calc.exe",                "Darwin": "Calculator",           "Linux": "gnome-calculator"},
    "calc":               {"Windows": "calc.exe",                "Darwin": "Calculator",           "Linux": "gnome-calculator"},
    "paint":              {"Windows": "mspaint.exe",             "Darwin": "Preview",              "Linux": "gimp"},
    "photos":             {"Windows": "ms-photos:",              "Darwin": "Photos",               "Linux": "shotwell"},
    "camera":             {"Windows": "microsoft.windows.camera:","Darwin": "Photo Booth",         "Linux": "cheese"},
    "clock":              {"Windows": "ms-clock:",               "Darwin": "Clock",                "Linux": "gnome-clocks"},

    # Productivity & Gaming
    "notion":             {"Windows": "Notion",                  "Darwin": "Notion",               "Linux": "notion"},
    "obsidian":           {"Windows": "Obsidian",                "Darwin": "Obsidian",             "Linux": "obsidian"},
    "capcut":             {"Windows": "CapCut",                  "Darwin": "CapCut",               "Linux": "capcut"},
    "steam":              {"Windows": "steam",                   "Darwin": "Steam",                "Linux": "steam"},
    "epic":               {"Windows": "EpicGamesLauncher",       "Darwin": "Epic Games Launcher",  "Linux": "legendary"},
    "epic games":         {"Windows": "EpicGamesLauncher",       "Darwin": "Epic Games Launcher",  "Linux": "legendary"},

    # Common Web & Utilities
    "browser":            {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "web browser":        {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "internet":           {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "google":             {"Windows": "https://www.google.com",  "Darwin": "https://www.google.com", "Linux": "https://www.google.com"},
    "gmail":              {"Windows": "https://mail.google.com", "Darwin": "https://mail.google.com", "Linux": "https://mail.google.com"},
    "mail":               {"Windows": "https://mail.google.com", "Darwin": "https://mail.google.com", "Linux": "https://mail.google.com"},
    "email":              {"Windows": "https://mail.google.com", "Darwin": "https://mail.google.com", "Linux": "https://mail.google.com"},
    "maps":               {"Windows": "https://maps.google.com", "Darwin": "https://maps.google.com", "Linux": "https://maps.google.com"},
    "google maps":        {"Windows": "https://maps.google.com", "Darwin": "https://maps.google.com", "Linux": "https://maps.google.com"},
    "github":             {"Windows": "https://github.com",      "Darwin": "https://github.com",      "Linux": "https://github.com"},
    "chatgpt":            {"Windows": "https://chatgpt.com",     "Darwin": "https://chatgpt.com",     "Linux": "https://chatgpt.com"},
    "command prompt":     {"Windows": "cmd.exe",                 "Darwin": "Terminal",             "Linux": "bash"},
    "cmd prompt":         {"Windows": "cmd.exe",                 "Darwin": "Terminal",             "Linux": "bash"},
    "control panel":      {"Windows": "control.exe",             "Darwin": "System Preferences",   "Linux": "gnome-control-center"},
    "snipping tool":      {"Windows": "snippingtool.exe",        "Darwin": "Screenshot",           "Linux": "gnome-screenshot"},
    "snip":               {"Windows": "snippingtool.exe",        "Darwin": "Screenshot",           "Linux": "gnome-screenshot"},
    "screenshot":         {"Windows": "snippingtool.exe",        "Darwin": "Screenshot",           "Linux": "gnome-screenshot"},
    "media player":       {"Windows": "wmplayer.exe",            "Darwin": "QuickTime Player",     "Linux": "vlc"},
    "windows media player": {"Windows": "wmplayer.exe",          "Darwin": "QuickTime Player",     "Linux": "vlc"},
    "wordpad":            {"Windows": "wordpad.exe",             "Darwin": "TextEdit",             "Linux": "libreoffice --writer"},
    "recycle bin":        {"Windows": "explorer.exe shell:RecycleBinFolder", "Darwin": "Finder",   "Linux": "nautilus"},
    "trash":              {"Windows": "explorer.exe shell:RecycleBinFolder", "Darwin": "Trash",    "Linux": "nautilus"},
    "cursor":             {"Windows": "cursor",                  "Darwin": "Cursor",               "Linux": "cursor"},
}


def _normalize(raw: str) -> str:
    key = raw.lower().strip()

    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(_SYSTEM, raw)

    for alias_key, os_map in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(_SYSTEM, raw)

    return raw


# ── Windows Window Focus & Foreground Management ─────────────────────────────

def _ensure_desktop():
    if _SYSTEM == "Windows":
        try:
            import ctypes
            hdesk = ctypes.windll.user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if hdesk:
                ctypes.windll.user32.SetThreadDesktop(hdesk)
        except Exception:
            pass


def _force_focus_hwnd(hwnd: int) -> bool:
    """Forces the target HWND to the foreground in front of all other windows.
    Bypasses Windows LockSetForegroundWindow restrictions using AttachThreadInput
    and keyboard state manipulation."""
    if not hwnd or _SYSTEM != "Windows":
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        if not user32.IsWindow(hwnd):
            return False

        try:
            user32.AllowSetForegroundWindow(-1)
            user32.LockSetForegroundWindow(2)  # LSFW_UNLOCK
        except Exception:
            pass

        # 1. Restore window if minimized
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        else:
            user32.ShowWindow(hwnd, 5)  # SW_SHOW

        # 2. Attach thread input to borrow foreground rights
        fore_hwnd = user32.GetForegroundWindow()
        fore_pid = ctypes.c_ulong()
        fore_tid = user32.GetWindowThreadProcessId(fore_hwnd, ctypes.byref(fore_pid))
        cur_tid = kernel32.GetCurrentThreadId()

        if fore_tid and fore_tid != cur_tid:
            user32.AttachThreadInput(fore_tid, cur_tid, True)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(fore_tid, cur_tid, False)
        else:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)

        # 3. Simulate Alt key tap if still not foreground (breaks stubborn Windows 10/11 lock)
        if user32.GetForegroundWindow() != hwnd:
            user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU down
            user32.SetForegroundWindow(hwnd)
            user32.keybd_event(0x12, 0, 2, 0)  # VK_MENU up

        # 4. Z-order bump: Topmost then Notopmost to force Windows DWM to surface window above all else
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_FLAGS = 0x0001 | 0x0002 | 0x0040  # SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_FLAGS)

        # 5. SwitchToThisWindow ensures the OS brings this window to front
        user32.SwitchToThisWindow(hwnd, True)
        return True
    except Exception as e:
        print(f"[open_app] _force_focus_hwnd error: {e}")
        return False


def _find_window_hwnds(search_terms: list[str], process_names: list[str] = None) -> list[int]:
    """Finds all visible window HWNDs matching search terms or process names."""
    if _SYSTEM != "Windows":
        return []
    _ensure_desktop()
    hwnds = []
    lower_terms = [t.lower().strip() for t in search_terms if t.strip()]
    target_pids = set()

    if process_names and _PSUTIL:
        lower_procs = [p.lower().strip() for p in process_names if p.strip()]
        for p in psutil.process_iter(['pid', 'name']):
            try:
                pname = p.info['name'].lower()
                if any(proc in pname for proc in lower_procs):
                    target_pids.add(p.info['pid'])
            except Exception:
                pass

    try:
        import win32gui
        import win32process

        def _enum_cb(hwnd, _):
            if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd).strip()
            cls_name = win32gui.GetClassName(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            try:
                rect = win32gui.GetWindowRect(hwnd)
                # Ignore 0x0 or off-screen hidden tool windows
                if (rect[2] - rect[0]) < 80 or (rect[3] - rect[1]) < 80:
                    return True
            except Exception:
                return True

            if pid in target_pids:
                hwnds.append(hwnd)
                return True

            if any(term in title.lower() for term in lower_terms):
                hwnds.append(hwnd)
                return True

            # Match Windows File Explorer class specifically
            if any(t in ("explorer", "file explorer", "file manager", "filemanager", "cabinetwclass") for t in lower_terms):
                if cls_name == "CabinetWClass":
                    hwnds.append(hwnd)
                    return True

            return True

        win32gui.EnumWindows(_enum_cb, None)
    except Exception:
        pass

    # Fallback to pygetwindow if win32gui missed or wasn't loaded
    if not hwnds:
        try:
            import pygetwindow as gw
            for w in gw.getAllWindows():
                if w.visible and w.title:
                    t_lower = w.title.lower()
                    if any(term in t_lower for term in lower_terms):
                        hwnds.append(w._hWnd)
        except Exception:
            pass

    return hwnds


def _bring_app_to_front(app_name: str, raw_name: str = "") -> bool:
    """Finds existing open window(s) and forces them to the foreground."""
    terms = [app_name, raw_name]
    procs = [app_name, raw_name]

    clean = (raw_name or app_name).lower().replace("-", " ").replace("_", " ").strip()
    if any(k in clean for k in ("explorer", "file manager", "filemanager", "files", "this pc", "my computer")):
        terms.extend(["file explorer", "this pc", "quick access", "downloads", "documents", "cabinetwclass"])
        procs.extend(["explorer.exe", "explorer"])
    elif "chrome" in clean:
        terms.extend(["chrome", "google chrome"])
        procs.append("chrome.exe")
    elif "edge" in clean:
        terms.extend(["edge", "microsoft edge"])
        procs.append("msedge.exe")
    elif "spotify" in clean:
        terms.append("spotify")
        procs.append("spotify.exe")
    elif "whatsapp" in clean:
        terms.append("whatsapp")
        procs.append("whatsapp.exe")
    elif "calc" in clean:
        terms.append("calculator")
        procs.append("calculatorapp.exe")
    elif "store" in clean:
        terms.append("microsoft store")
        procs.append("winstore.app.exe")
    elif "linkedin" in clean:
        terms.extend(["linkedin", "linked in"])
        procs.extend(["linkedin.exe", "applicationframehost.exe"])
    elif any(k in clean for k in ("code", "vscode", "visual studio code")):
        terms.extend(["visual studio code", "visual studio", "code"])
        procs.extend(["code.exe"])
    elif any(k in clean for k in ("terminal", "cmd", "powershell")):
        terms.extend(["terminal", "command prompt", "powershell", "windowsterminal"])
        procs.extend(["windowsterminal.exe", "cmd.exe", "powershell.exe"])
    elif "notepad" in clean:
        terms.append("notepad")
        procs.append("notepad.exe")
    elif "vlc" in clean:
        terms.append("vlc")
        procs.append("vlc.exe")
    elif "media player" in clean:
        terms.extend(["windows media player", "media player"])
        procs.append("wmplayer.exe")

    hwnds = _find_window_hwnds(terms, procs)
    for hwnd in hwnds:
        if _force_focus_hwnd(hwnd):
            time.sleep(0.1)
            return True
    return False


# ── Windows StartApps Cache (Microsoft Store + Win32 apps) ───────────────────

_START_APPS_CACHE: dict[str, str] = {}
_START_APPS_LOADED = False

def _get_start_apps() -> dict[str, str]:
    global _START_APPS_CACHE, _START_APPS_LOADED
    if _START_APPS_LOADED:
        return _START_APPS_CACHE
    if _SYSTEM != "Windows":
        _START_APPS_LOADED = True
        return {}
    try:
        import json
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-StartApps | ConvertTo-Json"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                n = str(item.get("Name") or "").strip().lower()
                a = str(item.get("AppID") or "").strip()
                if n and a:
                    _START_APPS_CACHE[n] = a
    except Exception as e:
        print(f"[open_app] Failed to load StartApps: {e}")
    _START_APPS_LOADED = True
    return _START_APPS_CACHE

def _find_start_app_id(query: str) -> str | None:
    apps = _get_start_apps()
    q = query.lower().strip()
    if q in apps:
        return apps[q]
    for name, appid in apps.items():
        if q == name or q in name or name in q:
            return appid
    return None


# ── Process Running Check ─────────────────────────────────────────────────────

_PROCESS_EXE_MAP: dict[str, list[str]] = {
    "chrome":        ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "firefox":       ["firefox.exe"],
    "edge":          ["msedge.exe"],
    "msedge":        ["msedge.exe"],
    "brave":         ["brave.exe"],
    "spotify":       ["spotify.exe"],
    "discord":       ["discord.exe"],
    "telegram":      ["telegram.exe"],
    "whatsapp":      ["whatsapp.exe"],
    "slack":         ["slack.exe"],
    "zoom":          ["zoom.exe"],
    "code":          ["code.exe"],
    "explorer":      ["explorer.exe"],
    "notepad":       ["notepad.exe"],
    "calc":          ["calculatorapp.exe", "calc.exe"],
    "vlc":           ["vlc.exe"],
    "steam":         ["steam.exe"],
    "notion":        ["notion.exe"],
    "obsidian":      ["obsidian.exe"],
    "figma":         ["figma.exe"],
    "blender":       ["blender.exe"],
    "postman":       ["postman.exe"],
}


def _is_process_running(app_name: str, raw_name: str = "") -> bool:
    """Returns True if any process matching the given app name is currently running."""
    if not _PSUTIL:
        return False
    clean = (raw_name or app_name).lower().replace("-", " ").replace("_", " ").strip()

    targets: list[str] = []
    for key, exes in _PROCESS_EXE_MAP.items():
        if key in clean or clean in key:
            targets.extend(exes)

    # Fallback: try the raw app_name itself as an exe
    raw_exe = app_name.lower().strip()
    if not raw_exe.endswith(".exe"):
        raw_exe += ".exe"
    targets.append(raw_exe)

    targets_lower = [t.lower() for t in targets]
    try:
        for p in psutil.process_iter(['name']):
            try:
                pname = (p.info['name'] or "").lower()
                if pname in targets_lower:
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def _fast_wait_visible(app_name: str, raw_name: str = "", max_wait: float = 0.25) -> bool:
    """Briefly poll (max 250ms) for the window to appear without blocking the assistant."""
    t_end = time.time() + max_wait
    while time.time() < t_end:
        if _bring_app_to_front(app_name, raw_name):
            return True
        time.sleep(0.04)
    return True


# ── Windows Launcher ─────────────────────────────────────────────────────────

def _launch_windows(app_name: str, raw_name: str = "") -> bool:
    clean = (raw_name or app_name).lower().replace("-", " ").replace("_", " ").strip()

    # 1. Check if a visible window is already open — bring it to front immediately.
    if _bring_app_to_front(app_name, raw_name):
        print(f"[open_app] Existing window found and brought to front for: {raw_name or app_name}")
        return True

    # 2. Process is running but has NO visible window (e.g. Chrome closed all tabs but
    #    still lives in system tray). In this case we must open a NEW window rather than
    #    trying to focus a non-existent one.
    proc_running = _is_process_running(app_name, raw_name)
    if proc_running:
        print(f"[open_app] Process running but no visible window detected for '{raw_name or app_name}'. Opening new window...")
        # For Chrome / browsers, pass --new-window flag so a fresh window appears
        if "chrome" in clean:
            try:
                exe = shutil.which("chrome") or shutil.which("google-chrome")
                if not exe:
                    try:
                        from actions.browser_control import _find_exe_windows
                        exe = _find_exe_windows("chrome")
                    except Exception:
                        pass
                if exe:
                    subprocess.Popen([exe, "--new-window"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    # Fallback: start via shell which lets Windows pick the right chrome.exe
                    subprocess.Popen(["cmd", "/c", "start", "chrome", "--new-window"],
                                     shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return _fast_wait_visible(app_name, raw_name)
            except Exception as e:
                print(f"[open_app] chrome --new-window failed: {e}")
        elif "edge" in clean or "msedge" in clean:
            try:
                subprocess.Popen(["cmd", "/c", "start", "msedge", "--new-window"],
                                 shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return _fast_wait_visible(app_name, raw_name)
            except Exception as e:
                print(f"[open_app] msedge --new-window failed: {e}")
        elif "firefox" in clean:
            try:
                subprocess.Popen(["cmd", "/c", "start", "firefox", "--new-window"],
                                 shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return _fast_wait_visible(app_name, raw_name)
            except Exception as e:
                print(f"[open_app] firefox --new-window failed: {e}")
        # For other apps where the process is alive but windowless, fall through to normal launch

    # 2. File Explorer / File Manager special handling:
    # Use Win+E keyboard shortcut which Windows shell handles natively in the foreground
    if any(k in clean for k in ("explorer", "file manager", "filemanager", "files", "this pc", "my computer")):
        try:
            import pyautogui
            pyautogui.hotkey("win", "e")
            return _fast_wait_visible("explorer", "file explorer", max_wait=0.3)
        except Exception as e:
            print(f"[open_app] Win+E failed: {e}")

    # 3. Check if app is an installed Microsoft Store or Desktop App via StartApps
    start_app_id = _find_start_app_id(clean)
    if start_app_id:
        try:
            print(f"[open_app] Launching via StartApp ID: {start_app_id}")
            os.startfile(f"shell:AppsFolder\\{start_app_id}")
            return _fast_wait_visible(app_name, raw_name)
        except Exception as e:
            print(f"[open_app] StartApp launch failed: {e}")

    # 4. Check if it's a URI protocol (e.g. ms-settings:, whatsapp:, spotify:, ms-windows-store:)
    if ":" in app_name and not app_name.startswith("http"):
        try:
            os.startfile(app_name)
            return _fast_wait_visible(app_name, raw_name)
        except Exception:
            pass

    # 5. Web URLs & Domains
    target_url = None
    if app_name.startswith("http://") or app_name.startswith("https://"):
        target_url = app_name
    elif any(app_name.lower().endswith(ext) for ext in (".com", ".org", ".net", ".io", ".ai", ".co", ".in", ".edu", ".gov")) or app_name.lower().startswith("www."):
        target_url = f"https://{app_name}" if not app_name.startswith("http") else app_name

    if target_url:
        try:
            from actions.browser_control import _open_native
            res = _open_native(target_url, None)
            if res and res.startswith("Opened"):
                return True
        except Exception:
            pass
        try:
            os.startfile(target_url)
            time.sleep(0.1)
            _bring_app_to_front("chrome", "browser")
            return True
        except Exception:
            pass

    # 6. Check if executable exists in PATH or known locations
    exe = shutil.which(app_name) or shutil.which(app_name.split(".")[0])
    if not exe:
        try:
            from actions.browser_control import _find_exe_windows
            exe = _find_exe_windows(app_name)
        except Exception:
            pass

    if exe:
        try:
            # os.startfile uses ShellExecute which grants higher foreground priority
            os.startfile(exe)
        except Exception:
            subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return _fast_wait_visible(app_name, raw_name)

    # 7. Fallback: Windows Start Menu search
    try:
        import pyautogui
        pyautogui.PAUSE = 0.02
        pyautogui.press("win")
        time.sleep(0.15)
        pyautogui.write(raw_name or app_name, interval=0.01)
        time.sleep(0.2)
        pyautogui.press("enter")
        return _fast_wait_visible(app_name, raw_name, max_wait=0.4)
    except Exception as e:
        print(f"[open_app] Start Menu search failed: {e}")

    return False


def _launch_macos(app_name: str, *args, **kwargs) -> bool:
    try:
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True, timeout=8
        )
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["open", "-a", f"{app_name}.app"],
            capture_output=True, timeout=8
        )
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen(
                [binary],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        import pyautogui
        pyautogui.hotkey("command", "space")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[open_app] Spotlight failed: {e}")

    return False


_LINUX_TERMINAL_FALLBACKS = [
    "x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal",
    "xterm", "lxterminal", "mate-terminal", "tilix", "alacritty", "kitty",
]

def _launch_linux(app_name: str, *args, **kwargs) -> bool:
    if app_name in ("x-terminal-emulator", "gnome-terminal", "terminal"):
        for term in _LINUX_TERMINAL_FALLBACKS:
            if shutil.which(term):
                try:
                    subprocess.Popen([term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1.0)
                    return True
                except Exception:
                    continue

    binary = (
        shutil.which(app_name) or
        shutil.which(app_name.lower()) or
        shutil.which(app_name.lower().replace(" ", "-")) or
        shutil.which(app_name.lower().replace(" ", "_"))
    )
    if binary:
        try:
            subprocess.Popen(
                [binary],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        subprocess.run(
            ["xdg-open", app_name],
            capture_output=True, timeout=5
        )
        return True
    except Exception:
        pass

    for desktop_name in [
        app_name.lower(),
        app_name.lower().replace(" ", "-"),
        app_name.lower().replace(" ", ""),
    ]:
        try:
            result = subprocess.run(
                ["gtk-launch", desktop_name],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass

    return False


_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin":  _launch_macos,
    "Linux":   _launch_linux,
}

def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()

    if not app_name:
        return "No application name provided."

    launcher = _OS_LAUNCHERS.get(_SYSTEM)
    if launcher is None:
        return f"Unsupported operating system: {_SYSTEM}"

    normalized = _normalize(app_name)
    print(f"[open_app] Launching/Focusing: '{app_name}' -> '{normalized}' ({_SYSTEM})")

    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        success = launcher(normalized, raw_name=app_name)
        if not success and normalized.lower() != app_name.lower():
            success = launcher(app_name, raw_name=app_name)

        if success:
            return f"Opened {app_name} successfully."
        return (
            f"Could not open {app_name}. "
            f"It may not be installed, or something went wrong."
        )
    except Exception as e:
        print(f"[open_app] Error: {e}")
        return f"Failed to open {app_name}: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "open_app",
    "description": "Opens, launches, or brings to the front any application on the computer, including LinkedIn, WhatsApp, Spotify, Chrome, Edge, File Manager / Explorer, Microsoft Store apps, settings, and tools. Always call this tool whenever the user asks to open, launch, or switch to any app or service.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app_name": {
                "type": "STRING",
                "description": "Exact or common name of the application (e.g. 'chrome', 'file manager', 'whatsapp', 'spotify', 'calculator', 'notepad')"
            }
        },
        "required": [
            "app_name"
        ]
    },
    "handler": open_app,
}
