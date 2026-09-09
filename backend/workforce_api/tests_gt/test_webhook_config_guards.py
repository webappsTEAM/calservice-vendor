"""
The two settings that make cross-app webhooks work, and what happens when
they are wrong.

WORKFORCE_WEBHOOK_SECRET already fails closed in production. This module
pins the sibling guard for CUSTOMER_APP_BASE_URL, which is easier to miss
precisely because getting it wrong is SILENT: webhook delivery is
fire-and-forget on a background thread, so an unset base URL in production
means every event this app sends -- leg changes, stop progress, proof of
delivery, live GPS, the final-fare reconciliation -- is POSTed to localhost,
fails, and is logged at INFO. The vendor side looks healthy while the
customer's tracking never moves.
"""
import re

from django.conf import settings
from django.test import SimpleTestCase

SETTINGS_FILE = "workforce_core/settings.py"


def _settings_source():
    with open(SETTINGS_FILE, encoding="utf-8", errors="replace") as fh:
        return fh.read()


class WebhookConfigGuardTests(SimpleTestCase):
    def test_the_base_url_guard_exists_and_is_production_only(self):
        src = _settings_source()
        self.assertIn("CRITICAL CONFIG ERROR: CUSTOMER_APP_BASE_URL", src)
        # Guarded on `not DEBUG` so local development still works unset.
        self.assertRegex(
            src,
            r"if not DEBUG and CUSTOMER_APP_BASE_URL\.startswith\(\s*\(\s*[\"']http://localhost",
        )

    def test_the_secret_guard_still_fails_closed_in_production(self):
        src = _settings_source()
        self.assertIn(
            "CRITICAL SECURITY ERROR: WORKFORCE_WEBHOOK_SECRET environment variable is mandatory",
            src,
        )

    def test_no_skeleton_key_default_remains(self):
        # The old well-known literal must not be reachable as a value --
        # only referenced in the comment explaining its removal.
        src = _settings_source()
        for line in src.splitlines():
            if "wf_webhook_secret_default" in line:
                stripped = line.strip()
                self.assertTrue(
                    stripped.startswith("#"),
                    f"the old default appears as code, not a comment: {stripped[:90]}",
                )

    def test_the_sender_targets_the_receivers_real_path(self):
        # A typo here would 404 every webhook, silently, for the same
        # fire-and-forget reason.
        with open("workforce_api/services/customer_webhook.py",
                  encoding="utf-8", errors="replace") as fh:
            sender = fh.read()
        self.assertIn("/api/workforce-integration/webhook/", sender)
        self.assertIn("X-Workforce-Webhook-Secret", sender)

    def test_base_url_is_normalised_without_a_trailing_slash(self):
        # The sender concatenates a path onto it; a trailing slash would
        # produce a double slash and, on some deployments, a redirect that
        # drops the POST body.
        self.assertFalse(settings.CUSTOMER_APP_BASE_URL.endswith("/"))
