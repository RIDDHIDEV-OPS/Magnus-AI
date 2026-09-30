"""
Macro & Routine Manager for Magnus AI.
Allows executing and saving multi-step routine macros (e.g., 'work mode', 'study mode', 'night mode').
"""
import json
import time
from pathlib import Path
import sys

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

_CONFIG_PATH = _get_base_dir() / "config" / "macros.json"

_PRESET_ROUTINES = {
    "work": {
        "description": "Sets up workspace: opens VS Code, Chrome, and adjusts audio.",
        "steps": [
            {"action": "setting", "name": "volume_set", "value": "40"},
            {"action": "open", "target": "code"},
            {"action": "open", "target": "chrome"},
        ]
    },
    "study": {
        "description": "Sets quiet study atmosphere: opens notes, browser, and lowers volume.",
        "steps": [
            {"action": "setting", "name": "volume_set", "value": "25"},
            {"action": "open", "target": "chrome"},
            {"action": "open", "target": "notepad"},
        ]
    },
    "night": {
        "description": "Night wind-down: dims screen, lowers volume, and plays relaxing lofi beats.",
        "steps": [
            {"action": "setting", "name": "volume_set", "value": "20"},
            {"action": "setting", "name": "brightness_down", "value": "30"},
            {"action": "youtube", "query": "lofi hip hop radio beats to relax study to"},
        ]
    },
    "chill": {
        "description": "Chill mode: sets comfortable volume and plays relaxing background music.",
        "steps": [
            {"action": "setting", "name": "volume_set", "value": "35"},
            {"action": "youtube", "query": "chill ambient music"},
        ]
    },
    "reset": {
        "description": "Minimizes open windows and returns to clean desktop.",
        "steps": [
            {"action": "setting", "name": "show_desktop", "value": ""},
        ]
    }
}

def _load_macros() -> dict:
    if not _CONFIG_PATH.exists():
        _save_macros(_PRESET_ROUTINES)
        return dict(_PRESET_ROUTINES)
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        # Merge built-ins if missing
        for k, v in _PRESET_ROUTINES.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return dict(_PRESET_ROUTINES)

def _save_macros(macros: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(macros, indent=2, ensure_ascii=False), encoding="utf-8")

def _execute_step(step: dict) -> str:
    stype = step.get("action", "")
    try:
        if stype == "open":
            from actions.open_app import open_app
            target = step.get("target", "")
            if target:
                open_app(parameters={"app_name": target})
                time.sleep(0.3)
                return f"Opened {target}"

        elif stype == "setting":
            from actions.computer_settings import computer_settings
            name = step.get("name", "")
            val = str(step.get("value", ""))
            computer_settings(parameters={"action": name, "value": val})
            time.sleep(0.2)
            return f"Applied setting {name}"

        elif stype == "youtube":
            from actions.youtube_video import youtube_video
            query = step.get("query", "relaxing music")
            youtube_video(parameters={"action": "play", "query": query})
            return f"Playing '{query}'"
    except Exception as e:
        return f"Step error: {e}"
    return "Skipped step"


def macro_manager(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "run").strip().lower()
    name = params.get("name", "").strip().lower()

    macros = _load_macros()

    # ── Action: List Macros ──────────────────────────────────────────────────
    if action in ("list", "show", "get"):
        lines = ["Available voice routines:"]
        for m_name, m_data in macros.items():
            desc = m_data.get("description", "Routine")
            lines.append(f"• '{m_name} mode' — {desc}")
        return "\n".join(lines)

    # ── Action: Run Macro ────────────────────────────────────────────────────
    if action in ("run", "execute", "start"):
        # Normalize name aliases
        clean_name = name.replace(" mode", "").replace("_mode", "").replace(" routine", "").strip()
        matched_key = None
        for k in macros:
            if clean_name == k or clean_name in k or k in clean_name:
                matched_key = k
                break

        if not matched_key:
            available = ", ".join(f"'{k}'" for k in macros.keys())
            return f"Routine '{name}' not found. Available routines: {available}."

        macro_data = macros[matched_key]
        steps = macro_data.get("steps", [])
        if not steps:
            return f"Routine '{matched_key}' has no configured steps."

        results = []
        for step in steps:
            r = _execute_step(step)
            results.append(r)

        return f"Activated {matched_key} mode: {', '.join(results)}."

    # ── Action: Save Macro ───────────────────────────────────────────────────
    if action in ("save", "create", "add"):
        steps_raw = params.get("steps", "")
        if not name:
            return "Please provide a name for the new routine."
        clean_name = name.replace(" mode", "").strip()
        # Create a simple macro
        macros[clean_name] = {
            "description": f"Custom user routine for {clean_name}",
            "steps": []
        }
        _save_macros(macros)
        return f"Routine '{clean_name}' saved."

    return "Unknown macro command. Use 'run', 'list', or 'save'."


TOOL = {
    "name": "macro_manager",
    "description": (
        "Runs or lists multi-step automated routines/macros on the computer, such as 'work mode', "
        "'study mode', 'night mode', 'chill mode', or 'reset desktop'. "
        "Call this whenever the user says 'start work mode', 'activate study mode', 'turn on night mode', "
        "'chill mode', or asks about available routines."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'run' (default), 'list', or 'save'",
                "enum": ["run", "list", "save"]
            },
            "name": {
                "type": "STRING",
                "description": "Name of the routine (e.g. 'work', 'study', 'night', 'chill', 'reset')"
            }
        },
        "required": ["name"]
    },
    "handler": macro_manager,
}
