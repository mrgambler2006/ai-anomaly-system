$python = "C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe"
Start-Process -WindowStyle Hidden -FilePath $python -ArgumentList "agent\monitor_agent.py --server-url http://127.0.0.1:8000 --interval 1 --popup-cooldown 1"
