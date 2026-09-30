# 🌌 MAGNUS AI
### High-Performance Desktop Voice AI Assistant & Autonomous System Agent

Developed and Maintained by **Riddhi Das**

---

## 📖 Overview

**Magnus AI** is a state-of-the-art, cross-platform personal desktop AI assistant powered by the Google Gemini Live API. It delivers seamless bidirectional audio streaming with near-zero latency, dynamic visual awareness, persistent memory, and deep operating system control.

Featuring an interactive Quantum Orb interface with reactive visual waveforms, Magnus AI can see through your screen or webcam, listen to your speech with real-time turn detection, speak with expressive natural voices, manage applications, and automate computer tasks—all with zero subscriptions and complete privacy.

---

## 👤 Developer Details

* **Creator & Developer:** Riddhi Das
* **Project:** Magnus AI
* **Architecture:** Python, PyQt6, Google Gemini Live WebSockets API, Win32 Automation

---

## ✨ Key Features

### 🎙️ Ultra-Low Latency Voice Streaming
* **Instant Turn Detection:** Configured with real-time endpointing (~250ms silence detection) for instant vocal responses.
* **Multilingual Adaptation:** Greets in English by default and instantly switches to any language spoken by the user.
* **Echo Suppression & Tail Guard:** Prevents the assistant from picking up its own voice output.
* **Push-to-Talk & Wake Control:** Global hotkeys and background wake detection.

### 🔮 Interactive Quantum Orb & Holographic HUD
* **Dynamic Visualizer:** Responsive glowing quantum orb and audio spectrum waveforms that pulse in sync with microphone and assistant audio.
* **Live Telemetry:** Real-time hardware monitoring (CPU, RAM, GPU, and temperature).
* **Multi-Theme Engine:** Customizable HUD colors and modern sleek aesthetics.

### 🖥️ Native Computer & Application Control
* **Foreground Window Enforcer:** Automatically forces newly opened apps (Chrome, File Explorer, Microsoft Store UWP apps, etc.) directly to the front.
* **Instant Window Switching:** Detects already-running applications and brings them forward immediately without duplicate processes.
* **System Settings:** Control system volume, brightness, power state, and Wi-Fi via voice.
* **Desktop Automation:** Screen reading, mouse clicks, keystrokes, and file navigation.

### 🧠 Persistent Local Memory
* **Local Context Storage:** Automatically stores user preferences, facts, and conversation history in local JSON storage (`memory/long_term.json`).
* **On-Demand Memory Recall:** Fast local lookup without sending unnecessary context over the network.

### 👁️ Multimodal Visual Intelligence
* **Screen Perception:** Captures and analyzes current desktop activity, code, or documents.
* **Camera Input:** Webcam video feed integration for real-world object and environment awareness.

### 🧩 Self-Describing Modular Actions & Plugins
* Easily extend capabilities by adding Python modules to `actions/` or `plugins/`.
* Discovered and registered dynamically on application startup.

---

## 🗂️ Project Structure

```
Magnus-AI/
├── main.py                   # Core orchestrator — Gemini Live session, audio pipeline, tool routing
├── ui.py                     # PyQt6 HUD — Quantum Orb, audio spectrum, status indicators, settings drawer
├── setup.py                  # Automated platform-aware dependency installer
│
├── actions/                  # Built-in system capabilities and tools
│   ├── open_app.py           # Application launcher with Win32 foreground enforcement
│   ├── browser_control.py    # Web browser navigation and tab control
│   ├── computer_control.py   # Mouse, keyboard, window focus, and desktop automation
│   ├── computer_settings.py  # System volume, brightness, Wi-Fi, and power management
│   ├── file_controller.py    # Local file creation, movement, renaming, and deletion
│   ├── file_processor.py     # Document reading, analysis, and summarization
│   ├── screen_processor.py   # Desktop screen and webcam capture
│   ├── weather_report.py     # Real-time weather reporting
│   ├── web_search.py         # Grounded Google search integration
│   ├── youtube_video.py      # Media and music playback
│   └── reminder.py           # Scheduled system alerts and notifications
│
├── core/                     # Internal engine logic
│   ├── prompt.txt            # System instructions, personality protocols, and execution rules
│   ├── gemini.py             # Gemini API client, fallback ladder, and error handling
│   ├── audio_devices.py      # Audio input/output device detection and resolution
│   ├── action_loader.py      # Dynamic tool discovery and registration engine
│   └── hotkey.py             # Global push-to-talk key listeners
│
├── memory/                   # State and configuration
│   ├── config_manager.py     # Settings and API key manager
│   ├── memory_manager.py     # Long-term memory store reader and writer
│   └── long_term.json        # Saved user memory and preferences
│
└── config/
    └── api_keys.json         # API keys and runtime configuration
```

---

## ⚡ Quick Start

### 1. Requirements
* **Operating System:** Windows 10/11, macOS, or Linux (Windows recommended for full OS integration)
* **Python:** 3.11, 3.12, or 3.13
* **Hardware:** Working microphone and speakers / headphones
* **API Key:** Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/app/apikey))

### 2. Installation
1. Clone or download the repository to your local machine.
2. Open a terminal in the project directory and install dependencies:
   ```bash
   python setup.py
   ```
   *Alternatively:*
   ```bash
   pip install -r requirements.txt
   ```

### 3. Configuration
Add your Gemini API Key in `config/api_keys.json`:
```json
{
    "gemini_api_key": "YOUR_GEMINI_API_KEY",
    "assistant_name": "MAGNUS AI",
    "user_name": "Riddhi Das"
}
```

### 4. Running the Assistant
Launch Magnus AI:
```bash
python main.py
```

---

## 🔒 Privacy & Data Security

* **Local-First Processing:** Memories, preferences, and configurations reside strictly on your local machine (`config/api_keys.json` and `memory/long_term.json`).
* **No Telemetry or Tracking:** Zero telemetry servers, third-party analytics, or background tracking.
* **Direct Audio Streaming:** Live audio is streamed directly to Google's official Gemini API endpoint and stops immediately when muted or closed.

---

## 📜 Project Info

* **Project:** Magnus AI
* **Author:** Riddhi Das
* **Status:** Active Development
