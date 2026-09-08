@echo off
cd /d "e:\Porter\Calservices\Calservices\vendor\backend"
start "Vendor-Backend" /min "C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe" manage.py runserver 127.0.0.1:8001 --noreload
cd /d "e:\Porter\Calservices\Calservices\vendor\frontend"
start "Vendor-Frontend" /min cmd /c "set CI=true && npx vite --port 5176 --host"
