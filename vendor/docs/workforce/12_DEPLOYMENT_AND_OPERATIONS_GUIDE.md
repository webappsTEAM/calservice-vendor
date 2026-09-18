# 12. Production Deployment & Operations Guide

## 1. Production Architecture Overview

The production deployment runs on an Ubuntu Linux VPS connected to a managed Supabase PostgreSQL cluster.

```
                            INTERNET / CLIENTS
                                     │
                                     ▼
                     ┌───────────────────────────────┐
                     │          Nginx Proxy          │
                     │  - SSL / TLS Termination      │
                     │  - Static Asset Caching       │
                     │  - Rate Limiting              │
                     └───────────────┬───────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
       ┌───────────────────────────┐   ┌───────────────────────────┐
       │   Frontend Static Root    │   │      Gunicorn / DRF       │
       │     (/var/www/vendor)     │   │   (127.0.0.1:8001)        │
       │   React 18 + Vite SPA     │   │   workforce-backend       │
       └───────────────────────────┘   └─────────────┬─────────────┘
                                                     │
                                       ┌─────────────┴─────────────┐
                                       ▼                           ▼
                         ┌───────────────────────────┐   ┌───────────────────┐
                         │   workforce-dispatch      │   │     Supabase      │
                         │   (5s Auto-Sweep Daemon)  │   │    PostgreSQL     │
                         └───────────────────────────┘   └───────────────────┘
```

---

## 2. Backend Systemd Service Units

### 2.1 Workforce Backend API (`/etc/systemd/system/workforce-backend.service`)
```ini
[Unit]
Description=Workforce Django REST Backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/sevo-vendor/vendor/backend
EnvironmentFile=/home/ubuntu/sevo-vendor/vendor/backend/.env
ExecStart=/home/ubuntu/sevo-vendor/vendor/backend/.venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8001 \
    --timeout 60 \
    workforce_core.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 2.2 VPS Dispatch Engine Daemon (`/etc/systemd/system/workforce-dispatch.service`)
```ini
[Unit]
Description=Workforce 5-Second Dispatch Sweep Daemon
After=network.target workforce-backend.service

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/sevo-vendor/vendor/backend
EnvironmentFile=/home/ubuntu/sevo-vendor/vendor/backend/.env
ExecStart=/home/ubuntu/sevo-vendor/vendor/backend/.venv/bin/python manage.py run_dispatch_daemon --interval 5
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 3. Nginx Reverse Proxy Configuration

```nginx
server {
    listen 80;
    server_name vendor.calservice.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name vendor.calservice.com;

    ssl_certificate /etc/letsencrypt/live/vendor.calservice.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vendor.calservice.com/privkey.pem;

    root /var/www/vendor/dist;
    index index.html;

    # Frontend SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API reverse proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

---

## 4. Frontend Build & Deployment Script

```bash
cd /home/ubuntu/sevo-vendor/vendor/frontend
npm ci
npm run build
sudo rm -rf /var/www/vendor/dist/*
sudo cp -r dist/* /var/www/vendor/dist/
sudo systemctl reload nginx
```
