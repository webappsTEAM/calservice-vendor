"""
backend/workforce_api/management/commands/dispatch_worker.py

Authoritative Redis Dispatch Worker Management Command.
Consumes dispatch events from Redis Stream 'workforce:dispatch:jobs'
using Consumer Group 'workforce:dispatch:workers'.

For each event:
1. Locks the target ServiceRequest with select_for_update() in PostgreSQL.
2. Queries Redis GEO (workforce:technicians:geo) for nearby candidates within 20 km.
3. Passes shortlisted candidates to the authoritative 9-gate eligibility engine.
4. Atomically creates WorkforceJobOffer for the lowest non-empty wave.
5. Issues XACK to Redis Stream only after successful PostgreSQL commit.
6. Automatically claims and processes abandoned/pending events on startup/periodically.

Usage:
  Single pass (for test runs or cron):
    python manage.py dispatch_worker --once

  Continuous daemon mode:
    python manage.py dispatch_worker --batch-size 10 --block-ms 2000
"""
import logging
import os
import signal
import sys
import time
from django.core.management.base import BaseCommand

from workforce_api.services.redis_dispatch import (
    ensure_consumer_group,
    process_dispatch_stream_events,
    REDIS_DISPATCH_STREAM,
    REDIS_DISPATCH_GROUP,
)
from workforce_api.services.automatic_dispatch import dispatch_pending_jobs

logger = logging.getLogger("workforce.dispatch.worker")


class Command(BaseCommand):
    help = "Runs the Redis Stream automatic job dispatch worker."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process current pending/queued stream messages and exit immediately.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Maximum messages to consume per stream read (default: 10).",
        )
        parser.add_argument(
            "--block-ms",
            type=int,
            default=500,
            help="Milliseconds to block waiting for new stream messages (default: 500ms).",
        )
        parser.add_argument(
            "--worker-name",
            type=str,
            default="",
            help="Custom worker consumer name (default: worker-<pid>).",
        )
        parser.add_argument(
            "--reconcile-db",
            action="store_true",
            help="Run database unassigned jobs reconciliation on startup/sweep.",
        )

    def handle(self, *args, **options):
        run_once = options.get("once", False)
        batch_size = max(1, options.get("batch_size") or 10)
        block_ms = max(100, options.get("block_ms") or 2000)
        reconcile_db = options.get("reconcile_db", False)

        pid = os.getpid()
        worker_id = options.get("worker_name") or f"worker-{pid}"

        self.stdout.write(
            self.style.SUCCESS(
                f"[DISPATCH WORKER] Starting consumer '{worker_id}' on group '{REDIS_DISPATCH_GROUP}' "
                f"stream '{REDIS_DISPATCH_STREAM}' (batch: {batch_size}, block: {block_ms}ms)..."
            )
        )

        # Ensure Redis stream consumer group exists
        group_ready = ensure_consumer_group()
        if not group_ready:
            self.stdout.write(
                self.style.WARNING(
                    "[DISPATCH WORKER] Warning: Could not connect to Redis Stream or create consumer group. "
                    "Will retry during loop."
                )
            )

        # If requested or running recovery, reconcile any pending unassigned database jobs
        if reconcile_db:
            self.stdout.write("[DISPATCH WORKER] Reconciling unassigned database jobs...")
            sweep_res = dispatch_pending_jobs(limit=batch_size)
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DISPATCH WORKER] Reconciled {sweep_res.get('dispatched_count', 0)} jobs."
                )
            )

        if run_once:
            # Single pass mode
            processed = process_dispatch_stream_events(
                worker_id=worker_id,
                count=batch_size,
                block_ms=block_ms,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DISPATCH WORKER] Single pass completed. Processed {processed} event(s)."
                )
            )
            return

        # Continuous daemon mode
        shutdown_requested = False

        def handle_signal(sig, frame):
            nonlocal shutdown_requested
            shutdown_requested = True
            logger.info(f"[DISPATCH WORKER] Received signal {sig}. Initiating graceful shutdown...")

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        self.stdout.write(self.style.WARNING("[DISPATCH WORKER] Running in daemon mode. Press Ctrl+C to stop."))

        last_db_sweep = time.time()
        db_sweep_interval = 30.0  # Periodic fallback check every 30 seconds

        while not shutdown_requested:
            try:
                processed = process_dispatch_stream_events(
                    worker_id=worker_id,
                    count=batch_size,
                    block_ms=block_ms,
                )
                if processed > 0:
                    self.stdout.write(f"[DISPATCH WORKER] Processed {processed} message(s).")

                # Periodic database reconciliation sweep for jobs created while Redis was down
                now = time.time()
                if now - last_db_sweep > db_sweep_interval:
                    last_db_sweep = now
                    try:
                        dispatch_pending_jobs(limit=5)
                    except Exception as sw_err:
                        logger.debug(f"[DISPATCH_SWEEP_ERR] {sw_err}")

            except KeyboardInterrupt:
                break
            except Exception as loop_err:
                logger.error(f"[DISPATCH WORKER LOOP ERR] {loop_err}", exc_info=True)
                time.sleep(1.0)

        self.stdout.write(self.style.SUCCESS(f"[DISPATCH WORKER] Worker '{worker_id}' shut down cleanly."))
        sys.exit(0)
