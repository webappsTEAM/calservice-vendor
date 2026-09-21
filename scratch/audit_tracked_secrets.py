import subprocess
import re
import os

res = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
files = res.stdout.strip().split("\n")

patterns = {
    "DB_PASSWORD": re.compile(r"DB_PASSWORD\s*[:=]\s*['\"]?([^'\"\s\n]+)"),
    "SECRET_KEY": re.compile(r"(?:DJANGO_)?SECRET_KEY\s*[:=]\s*['\"]?([^'\"\s\n]+)"),
    "JWT_SECRET": re.compile(r"JWT_SECRET(?:_KEY)?\s*[:=]\s*['\"]?([^'\"\s\n]+)"),
    "GOOGLE_MAPS_KEY": re.compile(r"GOOGLE_MAPS_(?:API_)?KEY\s*[:=]\s*['\"]?([^'\"\s\n]+)"),
    "SMTP_PASSWORD": re.compile(r"EMAIL_HOST_PASSWORD\s*[:=]\s*['\"]?([^'\"\s\n]+)"),
    "WORKFORCE_WEBHOOK_SECRET": re.compile(r"WORKFORCE_WEBHOOK_SECRET\s*[:=]\s*['\"]?([^'\"\s\n]+)"),
}

safe_placeholders = {
    "", "change-me", "your_db_password", "your-secret-key-matching-primary-backend",
    "None", "test_key", "test_secret", "django-insecure-...", "your_shared_webhook_secret_here"
}

print("AUDITING ALL TRACKED FILES AT HEAD FOR POTENTIAL SECRETS:")
print("=" * 80)

hits = []
for f in files:
    if not f or f.startswith("node_modules") or f.endswith((".png", ".ico", ".jpg", ".svg", ".lock")):
        continue
    try:
        with open(f, "r", encoding="utf-8", errors="ignore") as fp:
            content = fp.read()
        for name, pat in patterns.items():
            matches = pat.findall(content)
            for m in matches:
                m_clean = m.strip("'\";,")
                if m_clean not in safe_placeholders and not m_clean.startswith("test_"):
                    # Record hit with masked value
                    masked = m_clean[:3] + "***" + (m_clean[-2:] if len(m_clean) > 5 else "")
                    hits.append((f, name, masked))
    except Exception as exc:
        pass

if not hits:
    print("[+] Clean! No real-looking secrets detected in tracked files.")
else:
    for f, name, masked in hits:
        print(f"File: {f} | Key: {name} | Value (Masked): {masked}")

print("=" * 80)
