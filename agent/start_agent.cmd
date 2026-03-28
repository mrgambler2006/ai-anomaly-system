@echo off
cd /d "%~dp0.."
"C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe" agent\monitor_agent.py --server-url http://127.0.0.1:8000 --interval 1 --popup-cooldown 1
