"""
Clipboard Intelligence Action for Magnus AI.
Enables reading, writing, and analyzing the system clipboard via voice.
"""
import sys
import subprocess

def _get_clipboard_text() -> str:
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception:
        pass

    # Windows fallback via powershell
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            text=True,
            timeout=2,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return out.strip()
    except Exception:
        return ""

def _set_clipboard_text(text: str) -> bool:
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass

    try:
        p = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
            stdin=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        p.communicate(input=text, timeout=2)
        return True
    except Exception:
        return False


def clipboard_action(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "read").strip().lower()
    text = params.get("text", "")

    if action in ("read", "get", "paste", "show"):
        content = _get_clipboard_text()
        if not content:
            return "The clipboard is currently empty."
        # Truncate if very large so LLM context isn't overwhelmed
        if len(content) > 1500:
            preview = content[:1500] + "\n...(truncated remaining text)"
            return f"Clipboard contents ({len(content)} characters):\n{preview}"
        return f"Clipboard contents:\n{content}"

    elif action in ("copy", "set", "write"):
        if not text:
            return "No text provided to copy to clipboard."
        if _set_clipboard_text(text):
            return f"Copied to clipboard: '{text[:80]}{'...' if len(text) > 80 else ''}'."
        return "Failed to set clipboard contents."

    elif action in ("clear", "empty"):
        _set_clipboard_text("")
        return "Clipboard cleared."

    return "Unknown clipboard action. Use 'read', 'copy', or 'clear'."


TOOL = {
    "name": "clipboard_action",
    "description": (
        "Reads, writes, or clears the computer's system clipboard. "
        "Use this whenever the user asks 'what's on my clipboard?', 'read my clipboard', "
        "'copy this to clipboard', or asks you to review or debug text they just copied."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action to perform: 'read' (default), 'copy', or 'clear'",
                "enum": ["read", "copy", "clear"]
            },
            "text": {
                "type": "STRING",
                "description": "Text to copy to clipboard (required only if action is 'copy')"
            }
        },
        "required": []
    },
    "handler": clipboard_action,
}
