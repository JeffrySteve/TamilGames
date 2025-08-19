# TamilGames

Interactive camera-based learning games for kids with Tamil language support.

## Features
- Drag-Drop word matching with Tamil text and dwell-to-grab UX
- Finger Counting up to 10 using both hands via MediaPipe Hands
- Mosquito Killing game to learn Tamil numbers (pinch gesture)
- Tkinter GUI with fullscreen toggle and camera settings

## Requirements
- Windows with a webcam
- Python 3.11 (recommended for MediaPipe)

## Setup (Windows PowerShell)
```powershell
# 1) Create and activate venv (if not already)
python -m venv .venv311
& .\.venv311\Scripts\Activate.ps1

# 2) Install dependencies
pip install -r requirements.txt
```

## Run
```powershell
python main.py
```

Tips:
- Press F11 to toggle fullscreen; ESC to exit fullscreen.
- Use Camera Settings in the menu to pick the right camera.

## Troubleshooting
- If MediaPipe fails to install, ensure Python 3.11 is used and venv is active.
- For smoother video, a MJPG-capable webcam helps.