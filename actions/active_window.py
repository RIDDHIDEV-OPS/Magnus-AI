"""
Active Window Inspector for Magnus AI.
Exposes context about the user's currently focused foreground application and document.
Allows Magnus to know what the user is looking at or working on without requiring a full screenshot.
"""
import platform
import sys

_SYSTEM = platform.system()

def get_active_window_info() -> dict:
    """Returns metadata about the currently active foreground window."""
    info = {
        "title": "Unknown",
        "app_name": "Unknown",
        "process_name": "Unknown",
        "pid": 0,
        "is_focused": False,
    }

    if _SYSTEM == "Windows":
        try:
            import win32gui
            import win32process
            import psutil

            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                info["is_focused"] = True
                title = win32gui.GetWindowText(hwnd).strip()
                info["title"] = title or "(Untitled Window)"

                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                info["pid"] = pid

                try:
                    proc = psutil.Process(pid)
                    pname = proc.name()
                    info["process_name"] = pname
                    base_name = pname.lower().replace(".exe", "")

                    app_map = {
                        "code": "Visual Studio Code",
                        "chrome": "Google Chrome",
                        "msedge": "Microsoft Edge",
                        "firefox": "Mozilla Firefox",
                        "brave": "Brave Browser",
                        "explorer": "Windows Explorer / Desktop",
                        "cmd": "Command Prompt",
                        "powershell": "PowerShell",
                        "windowsterminal": "Windows Terminal",
                        "notepad": "Notepad",
                        "spotify": "Spotify",
                        "discord": "Discord",
                        "slack": "Slack",
                        "telegram": "Telegram",
                        "whatsapp": "WhatsApp",
                        "taskmgr": "Task Manager",
                    }
                    info["app_name"] = app_map.get(base_name, base_name.title())
                except Exception:
                    pass
        except Exception as e:
            info["error"] = str(e)

    elif _SYSTEM == "Darwin":
        try:
            import subprocess
            cmd = """osascript -e 'tell application "System Events" to get {name, title of front window} of first application process whose frontmost is true'"""
            out = subprocess.check_output(cmd, shell=True, text=True, timeout=2).strip()
            parts = [p.strip() for p in out.split(",")]
            if parts:
                info["app_name"] = parts[0]
                if len(parts) > 1:
                    info["title"] = parts[1]
                info["is_focused"] = True
        except Exception:
            pass

    return info


def active_window_tool(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """Action tool called by Gemini to discover what the user has open on screen."""
    info = get_active_window_info()
    if not info.get("is_focused") or info.get("title") == "Unknown":
        return "Could not determine the active foreground window."

    app = info.get("app_name", "Application")
    title = info.get("title", "")
    proc = info.get("process_name", "")

    result = f"Active foreground application: {app}\nWindow Title: '{title}'"
    if proc:
        result += f"\nProcess: {proc}"

    return result


TOOL = {
    "name": "get_active_window",
    "description": (
        "Returns the currently active foreground window, application name, and title on the user's screen. "
        "Use this whenever the user asks 'what am I doing?', 'what's on my screen?', 'check this error', "
        "or when context about the current working document or browser tab is needed without capturing a full image."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": [],
    },
    "handler": active_window_tool,
}
