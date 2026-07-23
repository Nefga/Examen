@echo off
cd /d "%~dp0puente_serial"
py -m pip install -r requirements.txt
py puente_esp32_socketio.py --puerto COM3
pause
