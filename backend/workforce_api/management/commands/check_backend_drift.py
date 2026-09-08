"""
Fail when the two copies of this Django project drift apart.

The repository holds the same project twice: backend/ is what the deploy
pipeline ships, vendor/backend/ is what the development server runs. Every
change has to be made in both, and when one is forgotten nothing says so --
the code keeps working for whoever is looking at it and breaks only for the
other side.

That has already cost, at minimum:

  * generate_quote_number() defined only in vendor/backend/, so the shipping
    copy raised NameError on the first quote created
  * is_quotation_service() and nine estimation models missing from the shipping
    copy, so it could not even import its own URLconf
  * the RazorpayX duplicate-webhook guard present only in the shipping copy,
    leaving the development copy able to refund a failed payout twice
  * four job routes (hold, resume, customer-cancel-sync, clawback-sync)
    unrouted in the shipping copy
  * seventeen ServiceRequest columns undeclared in the development copy, so
    quote approval assigned subtotal_amount, discount_amount, final_amount and
    payment_collected_at and saved none of them

Run this in CI. It turns a defect nobody finds for months into a failing build.
Delete it the day the duplicate directory goes away -- that is the real fix,
and this is the tourniquet.
"""
import hashlib
import os

from django.core.management.base import BaseCommand, CommandError

APPS = [
    "accounts", "common", "companies", "employees", "service_requests",
    "time_tracking", "vendor_wallet", "workforce_api", "workforce_core",
]
LOOSE_FILES = ["manage.py", "requirements.txt"]
SKIP_DIRS = {"__pycache__", ".venv", "media", "scratch", "migrations_backup"}
SKIP_EXT = {".pyc", ".pyo", ".sqlite3", ".log", ".b64"}


def _digest(path):
    with open(path, "rb") as fh:
        # CRLF churn is not divergence; .gitattributes normalises it anyway.
        return hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()


def _collect(root):
    found = {}
    for app in APPS:
        base = os.path.join(root, app)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if os.path.splitext(name)[1] in SKIP_EXT:
                    continue
                full = os.path.join(dirpath, name)
                found[os.path.relpath(full, root)] = full
    for name in LOOSE_FILES:
        full = os.path.join(root, name)
        if os.path.exists(full):
            found[name] = full
    return found


class Command(BaseCommand):
    help = "Fail if backend/ and vendor/backend/ have drifted apart."

    def add_arguments(self, parser):
        parser.add_argument(
            "--repo-root", default=None,
            help="Repository root. Defaults to two levels above this project.",
        )

    def handle(self, *args, **options):
        root = options["repo_root"]
        if not root:
            # Walk up until we find the directory holding BOTH copies, so the
            # command works from either one. Checking only for "backend" is not
            # enough: vendor/ contains a directory of that name too.
            probe = os.path.abspath(os.getcwd())
            root = None
            for _ in range(5):
                probe = os.path.dirname(probe)
                if not probe:
                    break
                if os.path.isdir(os.path.join(probe, "backend")) and os.path.isdir(
                    os.path.join(probe, "vendor", "backend")
                ):
                    root = probe
                    break
            if not root:
                raise CommandError(
                    "Could not locate the repository root holding both backend/ and "
                    "vendor/backend/. Pass --repo-root."
                )

        shipped = os.path.join(root, "backend")
        dev = os.path.join(root, "vendor", "backend")
        for path, label in ((shipped, "backend/"), (dev, "vendor/backend/")):
            if not os.path.isdir(path):
                raise CommandError(f"Could not find {label} under {root}. Pass --repo-root.")

        a, b = _collect(shipped), _collect(dev)

        only_shipped = sorted(set(a) - set(b))
        only_dev = sorted(set(b) - set(a))
        differing = sorted(
            rel for rel in set(a) & set(b) if _digest(a[rel]) != _digest(b[rel])
        )

        if not (only_shipped or only_dev or differing):
            self.stdout.write(self.style.SUCCESS(
                f"The two backend copies match ({len(a)} files compared)."
            ))
            return

        lines = ["The two backend copies have drifted apart.", ""]
        if differing:
            lines.append(f"Differing content ({len(differing)}):")
            lines += [f"    {rel}" for rel in differing]
        if only_shipped:
            lines.append(f"\nOnly in backend/ — the development copy is missing these ({len(only_shipped)}):")
            lines += [f"    {rel}" for rel in only_shipped]
        if only_dev:
            lines.append(f"\nOnly in vendor/backend/ — THE SHIPPING COPY IS MISSING THESE ({len(only_dev)}):")
            lines += [f"    {rel}" for rel in only_dev]
        lines += [
            "",
            "Anything listed under the shipping copy is a defect that will appear",
            "only in production. Reconcile both copies before merging.",
        ]
        raise CommandError("\n".join(lines))
