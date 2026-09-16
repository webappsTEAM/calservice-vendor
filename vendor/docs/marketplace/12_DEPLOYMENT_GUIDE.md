# 12. Production Deployment Guide

## Production Environment
- **Server IP**: `187.52.121.98`
- **Vendor Frontend**: `/var/www/calservices/current-vendor/frontend/dist`
- **Vendor Backend**: `/var/www/calservices/current-vendor/backend`
- **PM2 Process**: `calservices-vendor-backend` (ID 1)
- **Database**: PostgreSQL on Supabase

## Deployment Procedure

### Step 1: Database Migration
Verify and execute new migrations against the shared Supabase PostgreSQL:
```bash
/var/www/calservices/shared/venv/vendor/bin/python /var/www/calservices/current-vendor/backend/manage.py migrate workforce_api
```
Migrations applied:
- `0030_vendor_store_and_capability` (Store, Deals, Coupons)
- `0031_multi_vendor_orders_ledger_and_cart` (Cart, Orders, Ledger, Settlement, Reviews)

### Step 2: Backend Reload
Restart the backend gunicorn worker with zero downtime:
```bash
pm2 reload calservices-vendor-backend
```

### Step 3: Frontend Compilation & Dist Deployment
Compile Vite production assets and unpack to Nginx document root:
```bash
cd /var/www/calservices/current-vendor/frontend
npm run build
```
Nginx automatically serves the updated single-page application with cached assets invalidated via content hashing.

### Step 4: Verification Smoke Test
Run the automated validation script:
```bash
python run_full_marketplace_verification.py
```
Ensure all tests report `PASS`.
