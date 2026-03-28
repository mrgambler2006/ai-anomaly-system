@echo off
cd /d "%~dp0.."
"C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
