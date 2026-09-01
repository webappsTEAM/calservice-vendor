# CalTrack Workforce — Production VPS Deployment Guide

## 1. Architecture Overview

```
                                  INTERNET
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                         │
                 ▼                                         ▼
     ┌───────────────────────┐                 ┌───────────────────────┐
     │   Customer Frontend   │                 │  Workforce Frontend   │
     │   (Vercel / Netlify)  │                 │  (Vercel / Netlify)   │
     └───────────┬───────────┘                 └───────────┬───────────┘
                 │                                         │
                 │ HTTPS (Port 443)                        │ HTTPS (Port 443)
                 │                                         │
                 ▼                                         ▼
   ═════════════════════════════════════════════════════════════════════════
                              PRODUCTION VPS
   ═════════════════════════════════════════════════════════════════════════
                 │
                 ▼
          ┌─────────────┐
          │    Nginx    │  (Reverse Proxy / SSL Termination)
          └──────┬──────┘
                 │
                 ├──────────────────────────────┐
                 │ HTTP (127.0.0.1:8001)        │ HTTP (127.0.0.1:8001)
                 ▼                              ▼
     ┌──────────────────────┐       ┌──────────────────────┐
     │   Django Backend     │       │   Dispatch Worker    │
     │   (Gunicorn/Uvicorn) │       │  (manage.py worker)  │
     └───────────┬──────────┘       └───────────┬──────────┘
                 │                              │
                 │ redis://127.0.0.1:6379/0     │ redis://127.0.0.1:6379/0
                 ▼                              ▼
          ┌─────────────────────────────────────────────┐
          │             Redis Server 8.x                │
          │  • Bound strictly to 127.0.0.1 (Loopback)   │
          │  • Protected mode: YES                      │
          │  • WAN Port 6379: BLOCKED BY FIREWALL       │
          │  • live-location, SSE Pub/Sub, GEO, Streams │
          └─────────────────────────────────────────────┘
                 │
                 │ TLS / SSL WAN Connection (Port 6543 / 5432)
                 ▼
   ═════════════════════════════════════════════════════════════════════════
                      SUPABASE POSTGRESQL (CLOUD)
   ═════════════════════════════════════════════════════════════════════════
          • Authoritative Source of Truth
          • ServiceRequest, WorkforceJobOffer, Employee, User, History
   ═════════════════════════════════════════════════════════════════════════
```

---

## 2. Security & Firewall Rules (UFW)

Redis MUST NOT be publicly exposed under any circumstance.

### Apply Firewall Rules on VPS:
```bash
# 1. Default policy: deny all incoming traffic
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 2. Allow SSH (Port 22), HTTP (80), and HTTPS (443) only
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 3. Explicitly verify Port 6379 is NOT allowed:
sudo ufw status verbose

# 4. Enable UFW
sudo ufw enable
```

### Redis Configuration Security:
In `/etc/redis/redis.conf`:
```conf
bind 127.0.0.1 ::1
protected-mode yes
port 6379
```

---

## 3. Environment Variables Configuration (`.env`)

On the VPS, create `/var/www/workforce/backend/.env`:

```ini
# Database (Supabase Cloud Pooler)
DB_NAME=postgres
DB_USER=your_supabase_user
DB_PASSWORD=your_supabase_password
DB_HOST=aws-0-ap-south-1.pooler.supabase.com
DB_PORT=6543
DB_SSLMODE=require

# Django
DJANGO_SECRET_KEY=your-production-secret-key-min-50-chars
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=api.yourdomain.com,127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=https://workforce.yourdomain.com,https://customer.yourdomain.com

# Redis (Strictly local loopback for standalone VPS)
REDIS_URL=redis://127.0.0.1:6379/0

# Dispatch Settings
DISPATCH_LOCATION_MAX_AGE_SECONDS=120
DISPATCH_CANDIDATE_RADIUS_KM=20.0
REDIS_DISPATCH_STREAM=workforce:dispatch:jobs
REDIS_DISPATCH_GROUP=workforce:dispatch:workers
REDIS_GEO_KEY=workforce:technicians:geo
REDIS_TECH_LAST_SEEN_KEY=workforce:technicians:last_seen
```

*(Note: If deploying via Docker Compose with internal redis service, set `REDIS_URL=redis://redis:6379/0`)*

---

## 4. Nginx Reverse Proxy & Unbuffered Server-Sent Events (SSE)

Nginx acts as the public-facing reverse proxy and SSL terminator.

> [!IMPORTANT]
> By default, Nginx buffers upstream responses (`proxy_buffering on;`). For Server-Sent Events (SSE) live map tracking (`/api/workforce/realtime/stream/`), buffering **MUST BE DISABLED** (`proxy_buffering off;`) and proxy read timeouts must be extended (`proxy_read_timeout 86400s;`). Otherwise, Nginx holds location packets in memory, creating latency spikes and dropping idle connections every 60 seconds!

### Nginx Site Configuration (`/etc/nginx/sites-available/workforce`):
```nginx
upstream workforce_backend {
    server 127.0.0.1:8001;
    keepalive 32;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Static & Media uploads
    location /static/ {
        alias /var/www/workforce/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    location /media/ {
        alias /var/www/workforce/backend/media/;
        expires 7d;
    }

    # CRITICAL: Server-Sent Events (SSE) Realtime Stream Endpoint
    location /api/workforce/realtime/stream/ {
        proxy_pass http://workforce_backend;
        proxy_http_version 1.1;

        # Disable Connection hop-by-hop header for persistent keepalive
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CRITICAL SSE DIRECTIVES:
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # General REST API endpoints
    location / {
        proxy_pass http://workforce_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 10s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

---

## 5. Production Process Management (systemd)

We recommend **systemd** for Linux/Ubuntu VPS deployments because it natively manages startup order, automatic restarts upon crash, graceful SIGTERM termination, and centralized journal logging.

### Step 1: Copy Service Files
```bash
sudo cp deploy/systemd/workforce-backend.service /etc/systemd/system/
sudo cp deploy/systemd/workforce-dispatch-worker.service /etc/systemd/system/
```

### Step 2: Reload & Enable Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable redis
sudo systemctl enable workforce-backend
sudo systemctl enable workforce-dispatch-worker
```

### Step 3: Start Services
```bash
sudo systemctl start redis
sudo systemctl start workforce-backend
sudo systemctl start workforce-dispatch-worker
```

### Step 4: Verify Status
```bash
sudo systemctl status redis
sudo systemctl status workforce-backend
sudo systemctl status workforce-dispatch-worker
```

### View Live Logs:
```bash
# Backend logs
sudo journalctl -u workforce-backend -f

# Dispatch worker logs
sudo journalctl -u workforce-dispatch-worker -f
```

---

## 6. Startup & Failure Scenarios Handled

| Scenario | Expected Behavior | Automated Recovery |
|---|---|---|
| **Redis starts before Django** | Normal clean boot. | Immediate socket connection. |
| **Django starts before Redis** | Django boots cleanly. GPS & live tracking fall back gracefully to Supabase DB. | Auto-reconnects on next request once Redis is up. |
| **Worker starts before Redis** | Worker logs warning and retries in loop. | Auto-connects and ensures consumer group upon Redis startup. |
| **Worker process crashes** | systemd triggers `RestartSec=5s`. | Recovers unacked messages via `XCLAIM` and resumes. |
| **Redis process restarts** | Worker logs error, sleeps 1s, reconnects. | Reclaims pending messages; no duplicate offers created. |
| **VPS reboot** | systemd starts Redis → Backend → Worker automatically. | Zero manual intervention required. |
