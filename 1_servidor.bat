@echo off
cd /d "%~dp0Server_2"
if not exist node_modules npm install
npm start
pause
