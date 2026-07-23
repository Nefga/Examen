@echo off
cd /d "%~dp0clientes\java"
javac ClienteEcosistemaJava.java
if errorlevel 1 pause & exit /b 1
java ClienteEcosistemaJava
pause
