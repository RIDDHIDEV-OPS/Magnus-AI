#youtube_video.py
import json
import re
import sys
import time
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

for _stream in ("stdout", "stderr"):
    try:
        _s = getattr(sys, _stream, None)
        if _s is not None and hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP_OK = True
except ImportError:
    _PYPERCLIP_OK = False

try:
    import numpy as np
    _NUMPY = True
except ImportError:
    _NUMPY = False

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _TRANSCRIPT_OK = True
except ImportError:
    _TRANSCRIPT_OK = False

from config import get_os, is_windows, is_mac, is_linux

_LAST_YOUTUBE_HWND: int | None = None
_LAST_SEARCH_QUERY: str = ""
_PLAYED_VIDEO_IDS: set[str] = set()


def _ensure_desktop():
    if is_windows():
        try:
            import ctypes
            hdesk = ctypes.windll.user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if hdesk:
                ctypes.windll.user32.SetThreadDesktop(hdesk)
        except Exception:
            pass


def _force_focus_hwnd(hwnd: int) -> bool:
    """Forces the target HWND to the foreground in front of all other windows."""
    if not hwnd or not is_windows():
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

        # 3. Simulate Alt key tap if still not foreground
        if user32.GetForegroundWindow() != hwnd:
            user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU down
            user32.SetForegroundWindow(hwnd)
            user32.keybd_event(0x12, 0, 2, 0)  # VK_MENU up

        # 4. Z-order bump: Topmost then Notopmost to force Windows DWM to surface window
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_FLAGS = 0x0001 | 0x0002 | 0x0040  # SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_FLAGS)

        # 5. SwitchToThisWindow ensures the OS brings this window to front
        user32.SwitchToThisWindow(hwnd, True)
        return True
    except Exception as e:
        print(f"[YouTube] _force_focus_hwnd error: {e}")
        return False


def _find_youtube_or_browser_window(browser: str | None = None) -> int | None:
    """Finds an existing YouTube tab window HWND or active browser window HWND."""
    if not is_windows():
        return None
    try:
        import ctypes
        import win32gui
        import win32process
        import psutil

        _ensure_desktop()

        browser_procs = ["chrome.exe", "msedge.exe", "brave.exe", "firefox.exe", "opera.exe"]
        if browser:
            b_clean = browser.lower().strip()
            if "chrome" in b_clean:
                browser_procs = ["chrome.exe"]
            elif "edge" in b_clean:
                browser_procs = ["msedge.exe"]
            elif "brave" in b_clean:
                browser_procs = ["brave.exe"]
            elif "firefox" in b_clean:
                browser_procs = ["firefox.exe"]
            elif "opera" in b_clean:
                browser_procs = ["opera.exe"]

        youtube_hwnds = []
        last_match_hwnd = None
        new_tab_hwnds = []
        browser_hwnds = []

        def _enum_cb(hwnd, _):
            if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return True

            try:
                rect = win32gui.GetWindowRect(hwnd)
                if (rect[2] - rect[0]) < 100 or (rect[3] - rect[1]) < 100:
                    return True
            except Exception:
                return True

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                pname = psutil.Process(pid).name().lower()
            except Exception:
                pname = ""

            is_browser_proc = any(bp in pname for bp in browser_procs)
            t_lower = title.lower()

            # Priority 1: Window specifically has "youtube" in its active tab title
            if "youtube" in t_lower:
                youtube_hwnds.append(hwnd)
                return True

            # If it matches our last known YouTube window and is still valid
            global _LAST_YOUTUBE_HWND
            if _LAST_YOUTUBE_HWND and hwnd == _LAST_YOUTUBE_HWND:
                last_match_hwnd = hwnd
                return True

            # Priority 2: Browser window is currently on a blank / new tab
            if is_browser_proc and ("new tab" in t_lower or t_lower in ("google chrome", "microsoft edge", "brave")):
                new_tab_hwnds.append(hwnd)
                return True

            # Priority 3: Any existing browser window
            if is_browser_proc:
                browser_hwnds.append(hwnd)
                return True

            return True

        win32gui.EnumWindows(_enum_cb, None)

        if youtube_hwnds:
            return youtube_hwnds[0]
        if last_match_hwnd:
            return last_match_hwnd
        if new_tab_hwnds:
            return new_tab_hwnds[0]
        if browser_hwnds:
            return browser_hwnds[0]

        return None
    except Exception as e:
        print(f"[YouTube] _find_youtube_or_browser_window error: {e}")
        return None


def _navigate_existing_tab(hwnd: int, url: str) -> bool:
    """Navigates an existing browser/YouTube tab in-place, stopping any previous song."""
    try:
        import pyautogui
        import time

        print(f"[YouTube] Navigating existing tab in-place (HWND {hwnd})...")
        if not _force_focus_hwnd(hwnd):
            return False

        time.sleep(0.15)

        # 1. Immediately pause any currently playing video so previous music halts instantly
        try:
            pyautogui.press("k")
        except Exception:
            pass
        time.sleep(0.08)

        # 2. Select address bar: Ctrl + L
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.1)

        # 3. Paste target URL and press Enter
        _set_clipboard(url)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.08)
        pyautogui.press("enter")
        time.sleep(0.1)

        global _LAST_YOUTUBE_HWND
        _LAST_YOUTUBE_HWND = hwnd
        print(f"[YouTube] In-place navigation succeeded for: {url}")
        return True
    except Exception as e:
        print(f"[YouTube] In-place navigation failed: {e}")
        return False


def _set_clipboard(text: str) -> None:
    try:
        import pyperclip
        pyperclip.copy(text)
        return
    except Exception:
        pass
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text)
        win32clipboard.CloseClipboard()
        return
    except Exception:
        pass


def _store_new_browser_hwnd(browser: str | None = None):
    def _worker():
        import time
        for _ in range(5):
            time.sleep(1.0)
            hwnd = _find_youtube_or_browser_window(browser)
            if hwnd:
                global _LAST_YOUTUBE_HWND
                _LAST_YOUTUBE_HWND = hwnd
                break
    import threading
    threading.Thread(target=_worker, daemon=True).start()


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_YT_VIDEO_FILTER = "EgIQAQ%3D%3D"


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _open_url(url: str, browser: str | None = None) -> None:
    # 1. If an existing YouTube or browser tab is open, navigate it in-place
    yt_hwnd = _find_youtube_or_browser_window(browser)
    if yt_hwnd:
        if _navigate_existing_tab(yt_hwnd, url):
            return

    # 2. If no existing YouTube tab, launch via browser_control or OS
    try:
        from actions.browser_control import _open_native
        res = _open_native(url, browser)
        if res and res.startswith("Opened"):
            _store_new_browser_hwnd(browser)
            return
    except Exception as e:
        print(f"[YouTube] Native open failed ({e}), using fallback")

    try:
        if is_windows():
            import os
            try:
                os.startfile(url)
                _store_new_browser_hwnd(browser)
                return
            except Exception:
                pass
        import webbrowser
        try:
            if webbrowser.open(url):
                _store_new_browser_hwnd(browser)
                return
        except Exception:
            pass
        if is_mac():
            subprocess.Popen(["open", url])
        elif is_linux():
            subprocess.Popen(["xdg-open", url])
        else:
            subprocess.Popen(f'start "" "{url}"', shell=True)
        _store_new_browser_hwnd(browser)
    except Exception as e:
        print(f"[YouTube] ⚠️ open_url failed: {e}")


def _scrape_first_video_url(query: str, skip_ids: set[str] | None = None) -> str | None:

    if not _REQUESTS_OK:
        return None

    if skip_ids is None:
        skip_ids = set()

    search_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )

    try:
        r    = requests.get(search_url, headers=HEADERS, timeout=10)
        html = r.text

        video_ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)

        seen = set()
        for vid in video_ids:
            if vid in seen or vid in skip_ids:
                continue
            seen.add(vid)

            if f'/shorts/{vid}' in html:
                continue
            return f"https://www.youtube.com/watch?v={vid}"

        # If all candidates were in skip_ids, fall back to any valid video ID
        for vid in video_ids:
            if vid in seen:
                continue
            seen.add(vid)
            if f'/shorts/{vid}' not in html:
                return f"https://www.youtube.com/watch?v={vid}"

    except Exception as e:
        print(f"[YouTube] ⚠️ scrape_first_video_url failed: {e}")

    return None

def _extract_video_id(url: str) -> str | None:
    match = re.search(
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})", url
    )
    return match.group(1) if match else None


def _scrape_video_urls(query: str, max_results: int = 10) -> list[str]:
    if not _REQUESTS_OK:
        return []
    search_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )
    try:
        r = requests.get(search_url, headers=HEADERS, timeout=10)
        html = r.text
        video_ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
        seen = set()
        urls = []
        for vid in video_ids:
            if vid in seen:
                continue
            seen.add(vid)
            if f'/shorts/{vid}' in html:
                continue
            urls.append(f"https://www.youtube.com/watch?v={vid}")
            if len(urls) >= max_results:
                break
        return urls
    except Exception as e:
        print(f"[YouTube] ⚠️ _scrape_video_urls failed: {e}")
        return []


def _extract_ordinal(text: str) -> int | None:
    t = text.lower().strip()
    if t.isdigit() and 1 <= int(t) <= 50:
        return int(t)

    digit_m = re.search(r"\b(?:video|song|track|result|item|number|no\.?)\s*#?\s*(\d+)\b|\b(\d+)(?:st|nd|rd|th)?\s+(?:video|song|track|result|item|one)\b", t)
    if digit_m:
        val = digit_m.group(1) or digit_m.group(2)
        if val and val.isdigit():
            return int(val)

    ordinals = {
        "first": 1, "1st": 1, "one": 1,
        "second": 2, "2nd": 2, "two": 2,
        "third": 3, "3rd": 3, "three": 3,
        "fourth": 4, "4th": 4, "four": 4,
        "fifth": 5, "5th": 5, "five": 5,
        "sixth": 6, "6th": 6, "six": 6,
        "seventh": 7, "7th": 7, "seven": 7,
        "eighth": 8, "8th": 8, "eight": 8,
        "ninth": 9, "9th": 9, "nine": 9,
        "tenth": 10, "10th": 10, "ten": 10,
    }
    for word, num in ordinals.items():
        pattern = rf"\b{word}\s+(?:video|song|track|result|item|one)\b|\b(?:video|song|track|result|item|number|no\.?)\s+{word}\b"
        if re.search(pattern, t):
            return num
        if re.search(rf"\b(?:the\s+)?{word}\b", t) and any(w in t for w in ("play", "open", "select", "choose", "watch")):
            return num
    return None


def _is_youtube_homepage_title(title: str) -> bool:
    """Checks if a browser window title represents the YouTube homepage."""
    clean = re.sub(r"^\s*\(\d+[\d,]*\)\s*", "", title.strip(), flags=re.I)
    clean = re.sub(r"\s*-\s*(?:Google Chrome|Microsoft Edge|Brave|Firefox|Opera|Vivaldi).*$", "", clean, flags=re.I).strip()
    return clean.lower() in ("youtube", "")


def _get_active_youtube_query() -> str:
    """Extracts search query from active YouTube window title or session memory."""
    hwnd = _find_youtube_or_browser_window()
    if hwnd:
        try:
            import win32gui
            title = win32gui.GetWindowText(hwnd).strip()
            if _is_youtube_homepage_title(title):
                return ""
            # Strip leading notification badge (e.g. '(2127) Song Name - YouTube')
            cleaned = re.sub(r"^\s*\(\d+[\d,]*\)\s*", "", title, flags=re.I).strip()
            cleaned = re.sub(
                r"\s*-\s*(?:YouTube)?\s*-\s*(?:Google Chrome|Microsoft Edge|Brave|Firefox|Opera|Vivaldi).*$",
                "", cleaned, flags=re.I
            ).strip()
            cleaned = re.sub(r"\s*-\s*YouTube$", "", cleaned, flags=re.I).strip()
            if cleaned and cleaned.lower() not in ("youtube", "new tab"):
                return cleaned
        except Exception:
            pass
    return _LAST_SEARCH_QUERY


def _is_valid_youtube_url(url: str) -> bool:
    return bool(re.search(r"(youtube\.com|youtu\.be)", url or ""))


def _ask_for_url(prompt_text: str = "YouTube video URL:") -> str | None:
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk._default_root
        if root is None:
            root = tk.Tk()
            root.withdraw()

        url = simpledialog.askstring("J.A.R.V.I.S", prompt_text, parent=root)
        return url.strip() if url else None
    except Exception as e:
        print(f"[YouTube] ⚠️ URL dialog failed: {e}")
        return None


def _get_transcript(video_id: str) -> str | None:
    if not _TRANSCRIPT_OK:
        return None
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript      = None

        lang_priority = ["en", "tr", "de", "fr", "es", "it", "pt", "ru", "ja", "ko", "ar", "zh"]

        try:
            transcript = transcript_list.find_manually_created_transcript(lang_priority)
        except Exception:
            pass

        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(lang_priority)
            except Exception:
                for t in transcript_list:
                    transcript = t
                    break

        if transcript is None:
            return None

        fetched = transcript.fetch()
        return " ".join(entry["text"] for entry in fetched)

    except Exception as e:
        print(f"[YouTube] ⚠️ Transcript fetch failed: {e}")
        return None


def _summarize_with_gemini(transcript: str, video_url: str) -> str:
    from google.genai import types
    from core import gemini

    max_chars = 80000
    truncated = transcript[:max_chars] + ("..." if len(transcript) > max_chars else "")
    # A whole transcript can be 80k characters, hence the long deadline — but a
    # deadline there is, and the ladder in core/gemini.py picks the model.
    response = gemini.call(
        f"Please summarize this YouTube video transcript:\n\n{truncated}",
        tier=gemini.SMART,
        timeout_ms=60_000,
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are JARVIS, an AI assistant. "
                "Summarize YouTube video transcripts clearly and concisely. "
                "Structure: 1-sentence overview, then 3-5 key points. "
                "Be direct. Address the user as 'sir'. "
                "Match the language of the transcript."
            )
        )
    )
    if response is None:
        return "I couldn't reach Gemini to summarise that transcript, sir."
    return (response.text or "").strip()


def _save_summary(content: str, video_url: str) -> str:
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"youtube_summary_{ts}.txt"
    desktop  = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    filepath = desktop / filename

    header = (
        f"JARVIS — YouTube Summary\n"
        f"{'─' * 50}\n"
        f"URL    : {video_url}\n"
        f"Date   : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"{'─' * 50}\n\n"
    )
    filepath.write_text(header + content, encoding="utf-8")

    try:
        if is_windows():
            subprocess.Popen(["notepad.exe", str(filepath)])
        elif is_mac():
            subprocess.Popen(["open", "-t", str(filepath)])
        else:
            subprocess.Popen(["xdg-open", str(filepath)])
    except Exception as e:
        print(f"[YouTube] ⚠️ Could not open text editor: {e}")

    return str(filepath)


def _scrape_video_info(video_id: str) -> dict:
    if not _REQUESTS_OK:
        return {}
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=12)
        html = r.text
        info = {}

        for key, pattern in [
            ("title",    r'"title":\{"runs":\[\{"text":"([^"]+)"'),
            ("channel",  r'"ownerChannelName":"([^"]+)"'),
            ("views",    r'"viewCount":"(\d+)"'),
            ("duration", r'"lengthSeconds":"(\d+)"'),
            ("likes",    r'"label":"([0-9,]+ likes)"'),
        ]:
            match = re.search(pattern, html)
            if match:
                raw = match.group(1)
                if key == "views":
                    info[key] = f"{int(raw):,}"
                elif key == "duration":
                    secs = int(raw)
                    info[key] = f"{secs // 60}:{secs % 60:02d}"
                else:
                    info[key] = raw

        return info
    except Exception as e:
        print(f"[YouTube] ⚠️ Info scrape failed: {e}")
        return {}


def _scrape_trending(region: str = "TR", max_results: int = 8) -> list[dict]:
    if not _REQUESTS_OK:
        return []
    url = f"https://www.youtube.com/feed/trending?gl={region.upper()}"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=12)
        html = r.text

        titles   = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}\]', html)
        channels = re.findall(r'"ownerText":\{"runs":\[\{"text":"([^"]+)"', html)

        results, seen = [], set()
        for i, title in enumerate(titles):
            if title in seen or len(title) < 5:
                continue
            seen.add(title)
            channel = channels[i] if i < len(channels) else "Unknown"
            results.append({"rank": len(results) + 1, "title": title, "channel": channel})
            if len(results) >= max_results:
                break

        return results
    except Exception as e:
        print(f"[YouTube] ⚠️ Trending scrape failed: {e}")
        return []

def _handle_pause(parameters: dict = None, player=None, speak=None) -> str:
    """Pauses playback in the existing YouTube tab."""
    hwnd = _find_youtube_or_browser_window()
    if hwnd:
        _force_focus_hwnd(hwnd)
        time.sleep(0.08)
        try:
            import pyautogui
            pyautogui.press("k")
        except Exception:
            pass
        if player:
            player.write_log("[YouTube] Paused playback")
        return "Music playback paused, sir."

    if is_windows():
        try:
            import ctypes
            # VK_MEDIA_PLAY_PAUSE = 0xB3
            ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
            return "Music playback paused, sir."
        except Exception:
            pass

    return "No active music playing to pause, sir."


def _handle_resume(parameters: dict = None, player=None, speak=None) -> str:
    """Resumes playback in the existing YouTube tab."""
    hwnd = _find_youtube_or_browser_window()
    if hwnd:
        _force_focus_hwnd(hwnd)
        time.sleep(0.08)
        try:
            import pyautogui
            pyautogui.press("k")
        except Exception:
            pass
        if player:
            player.write_log("[YouTube] Resumed playback")
        return "Music playback resumed, sir."

    if is_windows():
        try:
            import ctypes
            ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
            return "Music playback resumed, sir."
        except Exception:
            pass

    return "No active music playing to resume, sir."


def _handle_next(parameters: dict = None, player=None, speak=None) -> str:
    """Plays the next song in the existing tab."""
    params = {"query": "next song"}
    return _handle_play(params, player)


def _handle_home(parameters: dict = None, player=None, speak=None) -> str:
    """Navigates the existing browser tab to YouTube home page."""
    _open_url("https://www.youtube.com")
    if player:
        player.write_log("[YouTube] Navigated to YouTube home page")
    return "Opened YouTube home page in existing tab, sir."


def _handle_back(parameters: dict = None, player=None, speak=None) -> str:
    """Navigates back to the previous page/video in the existing browser tab."""
    hwnd = _find_youtube_or_browser_window()
    if hwnd:
        _force_focus_hwnd(hwnd)
        time.sleep(0.08)
        try:
            import pyautogui
            pyautogui.hotkey("alt", "left")
            if player:
                player.write_log("[YouTube] Navigated back/reverse")
            return "Went back to previous page, sir."
        except Exception as e:
            print(f"[YouTube] Back failed: {e}")
    return "No active browser window to go back, sir."


def _handle_skip_ad(parameters: dict = None, player=None, speak=None) -> str:
    """Skips advertisement in YouTube video player safely without typing, opening ad links, or toggling miniplayer."""
    hwnd = _find_youtube_or_browser_window()
    if not hwnd:
        return "No active YouTube window found to skip ads, sir."

    _force_focus_hwnd(hwnd)
    time.sleep(0.15)

    if _PYAUTOGUI:
        import pyautogui
        sw, sh = pyautogui.size()

        # If an advertiser tab was previously opened (e.g. Google Cloud), return to YouTube tab
        try:
            import win32gui
            t = win32gui.GetWindowText(hwnd).lower()
            if "youtube" not in t:
                if any(k in t for k in ("cloud", "advertiser", "sponsor", "google store", "webstore")):
                    pyautogui.hotkey("ctrl", "w")
                    time.sleep(0.2)
                else:
                    pyautogui.hotkey("ctrl", "shift", "tab")
                    time.sleep(0.2)
        except Exception:
            pass

        # The YouTube Skip Ads button is located in the bottom-right corner of the video frame.
        # NEVER click the video center as that opens the advertiser's website (e.g. Google Cloud).
        # We test candidate coordinates for Standard player, Theater mode, and Fullscreen:
        skip_targets = [
            (int(sw * 0.672), int(sh * 0.787)),  # Standard player (e.g. 1290, 850 on 1080p)
            (int(sw * 0.660), int(sh * 0.770)),  # Standard player slightly inset
            (int(sw * 0.680), int(sh * 0.800)),  # Standard player slightly lower
            (int(sw * 0.958), int(sh * 0.861)),  # Theater mode (e.g. 1840, 930 on 1080p)
            (int(sw * 0.958), int(sh * 0.949)),  # Fullscreen mode (e.g. 1840, 1025 on 1080p)
        ]

        # In YouTube, Tab navigates to Skip button and Enter activates it
        try:
            pyautogui.press("tab")
            time.sleep(0.04)
            pyautogui.press("enter")
            time.sleep(0.05)
        except Exception:
            pass

        # Click the exact Skip button coordinates across short intervals in case countdown is ending
        for attempt in range(3):
            for sx, sy in skip_targets:
                pyautogui.click(sx, sy)
                time.sleep(0.03)
            time.sleep(0.5)

        if player:
            player.write_log("[YouTube] Skipped advertisement")
        return "Skipped the advertisement, sir."

    return "PyAutoGUI not available to skip ads, sir."


def _ensure_audible_volume():
    """Auto-unmutes and sets volume to a comfortable 35% if the system is muted or at 0."""
    try:
        from actions.computer_settings import volume_get, computer_settings
        cur_vol = volume_get()
        if cur_vol is not None and cur_vol <= 5:
            computer_settings(parameters={"action": "volume_set", "value": "35"})
            print(f"[YouTube] 🔊 Volume was {cur_vol}%, automatically raised to 35% for music playback.")
    except Exception as e:
        print(f"[YouTube] Volume guard check: {e}")


def _handle_play(parameters: dict, player) -> str:
    global _LAST_SEARCH_QUERY, _PLAYED_VIDEO_IDS
    _ensure_audible_volume()
    query = (parameters.get("query") or "").strip()
    browser = parameters.get("browser", None)
    if not query:
        return "Please tell me what you'd like to watch, sir."

    if not browser:
        q_lower = query.lower()
        for b_name in ("chrome", "edge", "firefox", "brave", "opera"):
            if b_name in q_lower:
                browser = b_name
                break

    # Clean query from conversational boilerplate
    clean = re.sub(
        r"^(?:please\s+)?(?:can\s+you\s+)?(?:open\s+youtube\s+(?:in\s+(?:my\s+)?\w+\s+)?(?:and\s+)?)?(?:play|search|put\s+on|find)\s+(?:me\s+)?(?:a\s+|any\s+|the\s+)?(?:song|video|music|track)?(?:\s+(?:by|of|from|called|named))?\s*",
        "",
        query,
        flags=re.IGNORECASE,
    ).strip()
    clean = re.sub(
        r"\s+(?:on\s+youtube|in\s+(?:my\s+)?(?:chrome|edge|firefox|browser))(?:\s+please)?$",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()

    clean_lower = clean.lower()

    # Intercept pause / stop commands mistakenly routed to 'play'
    if clean_lower in (
        "pause", "stop", "halt", "pause music", "stop music",
        "pause the music", "stop the music", "pause video", "stop video"
    ):
        return _handle_pause(parameters, player)

    # Intercept resume commands mistakenly routed to 'play'
    if clean_lower in ("resume", "continue", "unpause", "play music", "resume music", "resume video"):
        return _handle_resume(parameters, player)

    # Intercept skip ad commands mistakenly routed to 'play'
    if clean_lower in ("skip ad", "skip the ad", "skip ads", "skip", "skip advertisement", "skip this ad"):
        return _handle_skip_ad(parameters, player)

    # Intercept home page requests
    if clean_lower in (
        "home", "homepage", "main page", "youtube home", "youtube main page",
        "youtube homepage", "go to home", "go to main page", "go to homepage"
    ):
        return _handle_home(parameters, player)

    # Intercept reverse / back requests
    if clean_lower in (
        "back", "reverse", "go back", "go to reverse", "previous", "previous page", "rewind"
    ):
        return _handle_back(parameters, player)

    # Check for ordinal / video number selection (e.g. "play second video", "play 2nd video", "third video")
    ordinal = _extract_ordinal(clean_lower) or _extract_ordinal(query.lower())
    if ordinal is not None:
        # Check if currently on the YouTube homepage or user explicitly asked for homepage video
        is_homepage = False
        hwnd = _find_youtube_or_browser_window(browser)
        if hwnd:
            try:
                import win32gui
                wt = win32gui.GetWindowText(hwnd).strip()
                if _is_youtube_homepage_title(wt):
                    is_homepage = True
            except Exception:
                pass
        if any(k in query.lower() for k in ("homepage", "home page", "home video", "from home", "on home")):
            is_homepage = True

        if is_homepage:
            print(f"[YouTube] Selecting homepage video #{ordinal} directly on screen...")
            if hwnd:
                _force_focus_hwnd(hwnd)
                time.sleep(0.2)
            else:
                _open_url("https://www.youtube.com", browser)
                time.sleep(1.5)
                hwnd = _find_youtube_or_browser_window(browser)
                if hwnd:
                    _force_focus_hwnd(hwnd)
                    time.sleep(0.2)

            if _PYAUTOGUI:
                import pyautogui
                sw, sh = pyautogui.size()
                # Video card centers on YouTube homepage grid (supports 3-card and 4-card rows)
                col_map = {
                    1: (int(sw * 0.30), int(sh * 0.36)),
                    2: (int(sw * 0.57), int(sh * 0.36)),
                    3: (int(sw * 0.84), int(sh * 0.36)),
                    4: (int(sw * 0.30), int(sh * 0.72)),
                    5: (int(sw * 0.57), int(sh * 0.72)),
                    6: (int(sw * 0.84), int(sh * 0.72)),
                }
                cx, cy = col_map.get(ordinal, (int(sw * 0.57), int(sh * 0.36)))
                pyautogui.click(cx, cy)
                if player:
                    player.write_log(f"[YouTube] Clicked homepage video #{ordinal} at ({cx}, {cy})")
                return f"Playing video {ordinal} from YouTube homepage, sir."

        active_query = _get_active_youtube_query() or _LAST_SEARCH_QUERY or "top trending hit songs"
        print(f"[YouTube] Selecting video #{ordinal} for query: '{active_query}'")
        urls = _scrape_video_urls(active_query, max_results=max(10, ordinal + 2))
        if len(urls) >= ordinal:
            target_url = urls[ordinal - 1]
            vid = _extract_video_id(target_url)
            if vid:
                _PLAYED_VIDEO_IDS.add(vid)
            print(f"[YouTube] ▶️ Opening video #{ordinal}: {target_url}")
            _open_url(target_url, browser)
            return f"Playing video {ordinal} for: {active_query}"
        elif urls:
            target_url = urls[0]
            _open_url(target_url, browser)
            return f"Playing: {active_query}"

    # Detect relative requests and generic play requests like "play another music", "play something", "next song"
    generic_music_phrases = {
        "something", "anything", "play something", "play anything",
        "play music", "play a song", "play some music", "play a video",
        "play any music", "play any song", "play any video", "play",
        "another music", "another song", "next song", "next music",
        "something else", "different music", "different song",
        "other music", "other song", "another track", "next track",
        "another one", "next one", "another video", "next video",
        "another", "next", "change song", "change music"
    }

    if clean_lower in generic_music_phrases:
        active_query = _get_active_youtube_query() or _LAST_SEARCH_QUERY
        if active_query:
            search_query = active_query
        else:
            search_query = "top trending hit songs"
    else:
        search_query = clean if clean else query
        _LAST_SEARCH_QUERY = search_query

    if player:
        player.write_log(f"[YouTube] Searching: {search_query}")

    print(f"[YouTube] 🔍 Scraping video for: '{search_query}' (previously played: {len(_PLAYED_VIDEO_IDS)})")

    video_url = _scrape_first_video_url(search_query, skip_ids=_PLAYED_VIDEO_IDS)

    if video_url:
        vid = _extract_video_id(video_url)
        if vid:
            _PLAYED_VIDEO_IDS.add(vid)
        print(f"[YouTube] ▶️ Opening/Navigating: {video_url}")
        _open_url(video_url, browser)
        return f"Playing: {search_query}"

    print(f"[YouTube] ⚠️ Scrape failed, opening filtered search page")
    fallback_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(search_query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )
    _open_url(fallback_url, browser)
    return f"Opened YouTube search for: {search_query} (manual selection required)"


def _handle_summarize(parameters: dict, player, speak) -> str:
    if not _TRANSCRIPT_OK:
        return "youtube-transcript-api is not installed. Run: pip install youtube-transcript-api"

    url = _ask_for_url("Please paste the YouTube video URL:")
    if not url:
        return "No URL provided, sir. Summary cancelled."
    if not _is_valid_youtube_url(url):
        return "That doesn't appear to be a valid YouTube URL, sir."

    video_id = _extract_video_id(url)
    if not video_id:
        return "Could not extract video ID from that URL, sir."

    if player:
        player.write_log(f"[YouTube] Summarizing: {url}")
    if speak:
        speak("Fetching the transcript now, sir. One moment.")

    transcript = _get_transcript(video_id)
    if not transcript:
        return "I couldn't retrieve a transcript for that video, sir."

    if speak:
        speak("Transcript retrieved. Generating summary now.")

    try:
        summary = _summarize_with_gemini(transcript, url)
    except Exception as e:
        return f"Summary generation failed, sir: {e}"

    if speak:
        speak(summary)

    if parameters.get("save", False):
        saved_path = _save_summary(summary, url)
        return f"Summary complete and saved to Desktop: {saved_path}"

    return summary


def _handle_get_info(parameters: dict, player, speak) -> str:
    url = parameters.get("url", "").strip()
    if not url:
        url = _ask_for_url("Please paste the YouTube video URL:")
    if not url or not _is_valid_youtube_url(url):
        return "Please provide a valid YouTube URL, sir."

    video_id = _extract_video_id(url)
    if not video_id:
        return "Could not extract video ID, sir."

    if player:
        player.write_log(f"[YouTube] Getting info: {url}")

    info = _scrape_video_info(video_id)
    if not info:
        return "Could not retrieve video information, sir."

    lines = [
        f"{key.capitalize()}: {info[key]}"
        for key in ("title", "channel", "views", "duration", "likes")
        if key in info
    ]
    result = "\n".join(lines)

    if speak:
        speak(f"Here's the video info, sir. {result.replace(chr(10), '. ')}")

    return result


def _handle_trending(parameters: dict, player, speak) -> str:
    region = parameters.get("region", "TR").upper()

    if player:
        player.write_log(f"[YouTube] Trending: {region}")

    trending = _scrape_trending(region=region, max_results=8)
    if not trending:
        return f"Could not fetch trending videos for region {region}, sir."

    lines  = [f"Top trending videos in {region}:"]
    lines += [f"{v['rank']}. {v['title']} — {v['channel']}" for v in trending]
    result = "\n".join(lines)

    if speak:
        top3   = trending[:3]
        spoken = "Here are the top trending videos, sir. " + ". ".join(
            f"Number {v['rank']}: {v['title']} by {v['channel']}" for v in top3
        )
        speak(spoken)

    return result

_ACTION_MAP = {
    "play":       _handle_play,
    "pause":      _handle_pause,
    "stop":       _handle_pause,
    "resume":     _handle_resume,
    "unpause":    _handle_resume,
    "next":       _handle_next,
    "skip_ad":    _handle_skip_ad,
    "skip_ads":   _handle_skip_ad,
    "skipad":     _handle_skip_ad,
    "skip":       _handle_skip_ad,
    "home":       _handle_home,
    "homepage":   _handle_home,
    "main_page":  _handle_home,
    "back":       _handle_back,
    "reverse":    _handle_back,
    "go_back":    _handle_back,
    "previous":   _handle_back,
    "summarize":  _handle_summarize,
    "get_info":   _handle_get_info,
    "trending":   _handle_trending,
}


def youtube_video(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "play").lower().strip()

    if player:
        player.write_log(f"[YouTube] Action: {action}")
    print(f"[YouTube] ▶️  Action: {action}  Params: {params}")

    handler = _ACTION_MAP.get(action)
    if handler is None:
        return (
            f"Unknown YouTube action: '{action}'. "
            "Available: play, pause, stop, resume, next, skip_ad, home, back, reverse, summarize, get_info, trending."
        )

    try:
        if action == "play":
            return handler(params, player) or "Done."
        return handler(params, player, speak) or "Done."
    except Exception as e:
        print(f"[YouTube] ❌ Error in {action}: {e}")
        return f"YouTube {action} failed, sir: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "youtube_video",
    "description": (
        "ALWAYS use this tool whenever the user asks to play a song, music, video, or artist on YouTube or in their browser "
        "(e.g. 'play Arijit Singh on YouTube', 'open YouTube and play...', 'play some music', 'play something', 'play another song', 'next song', "
        "'play second video', 'play 2nd video', 'play first video'), "
        "OR when the user asks to SKIP ADS ('skip the ad', 'skip ad', 'skip ads'), "
        "OR when the user asks to PAUSE, STOP, or RESUME music playback, OR when asking to go to YouTube HOME page or go BACK/REVERSE. "
        "NEVER search YouTube for 'pause', 'stop', 'skip ad', or 'second video'. Also use for summarizing YouTube videos, getting video info, or trending videos."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "play | pause | stop | resume | next | skip_ad | home | back | reverse | summarize | get_info | trending (default: play)"
            },
            "query": {
                "type": "STRING",
                "description": "The song, artist, video name, ordinal, or search query to play (e.g. 'Arijit Singh', 'second video', 'another song', 'something')"
            },
            "browser": {
                "type": "STRING",
                "description": "Target browser if user specifies one (e.g. chrome, edge, firefox). Omit for default."
            },
            "save": {
                "type": "BOOLEAN",
                "description": "Save summary to Notepad (summarize only)"
            },
            "region": {
                "type": "STRING",
                "description": "Country code for trending e.g. TR, US"
            },
            "url": {
                "type": "STRING",
                "description": "Video URL for get_info action"
            }
        },
        "required": []
    },
    "handler": youtube_video,
}
