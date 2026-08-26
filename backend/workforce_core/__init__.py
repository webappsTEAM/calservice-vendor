"""Workforce Core Django Package."""
from django.db.backends.signals import connection_created


def _set_connection_safeguards(sender, connection, **kwargs):
    if getattr(connection, "vendor", "") == "postgresql":
        try:
            with connection.cursor() as cur:
                cur.execute("SET idle_in_transaction_session_timeout = 10000")
        except Exception:
            pass


connection_created.connect(_set_connection_safeguards)
