# 13. Marketplace Rollback Plan

## Overview
In the event of an unexpected regression or critical incident, this rollback plan restores the system to the previous verified release point while preserving database integrity.

## Rollback Scenarios & Actions

### Scenario 1: Frontend Defect
- If a UI bug occurs on the vendor portal:
  1. Restore the previous frontend build:
     ```bash
     cp -r /var/www/calservices/current-vendor/frontend/dist.bak /var/www/calservices/current-vendor/frontend/dist
     ```
  2. Clear browser cache and verify.

### Scenario 2: Backend API Error
- If an uncaught 500 error occurs in the marketplace API:
  1. Check logs via PM2:
     ```bash
     pm2 logs calservices-vendor-backend --lines 100
     ```
  2. If emergency rollback is required, switch the PM2 process back to the previous release symlink:
     ```bash
     pm2 reload calservices-vendor-backend
     ```

### Scenario 3: Database Rollback Safety (Rule 35 Compliance)
- If migration `0031` must be rolled back:
  1. **DO NOT** execute destructive drop queries on live tables containing customer orders or ledger entries.
  2. Backup the database:
     ```bash
     pg_dump -U postgres -h [supabase-host] [database] > /var/backups/marketplace_backup_$(date +%Y%m%d).sql
     ```
  3. Revert migration step to 0030:
     ```bash
     python manage.py migrate workforce_api 0030_vendor_store_and_capability
     ```

### Emergency Stop Controls (Feature Flags)
Marketplace capabilities can be disabled instantly without code rollback by toggling settings in `workforce_core/settings.py`:
- `GROCERY_MARKETPLACE_ENABLED = False`
- `GROCERY_CHECKOUT_ENABLED = False`
When disabled, the public cart and checkout endpoints return:
```json
{
  "error": "The grocery marketplace is temporarily paused for routine maintenance."
}
```
