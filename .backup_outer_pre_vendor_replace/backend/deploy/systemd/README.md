# X-11: supervising the automatic dispatch engine

## What this is

`workforce_api/management/commands/dispatch_pending_workforce_jobs.py` is the
only mechanism in this codebase that periodically re-evaluates *all* pending
jobs and sweeps expired offers on a fixed cadence. It already:

- runs a continuous loop (`--loop --interval N`),
- writes a heartbeat row every cycle (`WorkforceEventLog`,
  `event_type="dispatch_engine_heartbeat"`) so liveness is externally
  observable (surfaced today via the admin endpoint at
  `workforce_api/views.py:7759`),
- catches exceptions per-cycle so one bad cycle doesn't kill the loop.

Two things independently reduce, but do not eliminate, reliance on that
loop actually running continuously:

- `service_requests/models.py` calls `dispatch_job(self)` synchronously when
  a new job is created, so most jobs get an initial dispatch attempt
  immediately, without waiting for the loop.
- `workforce_api/views.py`'s `WorkforceJobListView.get()` opportunistically
  calls `expire_and_reassign_offers()` every time a technician's app polls
  its job list, so expired offers usually get swept as a side effect of
  normal app traffic even if the loop isn't running.

What is genuinely missing -- and what the command's own docstring/comment
already flags -- is that nothing restarts the loop if the *process* itself
dies (uncaught exception outside its own try/except, the host OOM-killing
it, a reboot), and nothing starts it automatically when the server boots.
Until a technician's app happens to poll, or a new job happens to be
created, dispatch for jobs sitting in a gap between those events depends on
someone noticing the loop is down and restarting it by hand.

`workforce-dispatch-engine.service` in this directory is a systemd unit
template that closes that specific gap: `Restart=always` + `WantedBy=multi-
user.target` gives the loop OS-level supervision (auto-restart-on-crash,
auto-start-on-boot), same as any other production service, without any of
the loop's own Python code changing.

## What this is not

It is not wired into any deployment automatically, and it does not run
until a human installs it. It is a template with `REPLACE_WITH_*`
placeholders for the deploy user, the repo's absolute path on the target
host, and the virtualenv's python -- values only known at actual deploy
time, which is why this was added as a template rather than guessed.

## Install (one-time, per server)

```
sudo cp deploy/systemd/workforce-dispatch-engine.service /etc/systemd/system/
sudo nano /etc/systemd/system/workforce-dispatch-engine.service   # fill in the REPLACE_WITH_* values
sudo systemctl daemon-reload
sudo systemctl enable --now workforce-dispatch-engine
```

## Verify

```
sudo systemctl status workforce-dispatch-engine
sudo journalctl -u workforce-dispatch-engine -f
```

Or check the heartbeat row directly / via the existing admin endpoint that
already reads `WorkforceEventLog(event_type="dispatch_engine_heartbeat")` --
`last_heartbeat` should advance roughly every `--interval` seconds.

## If this server doesn't use systemd

The same `python manage.py dispatch_pending_workforce_jobs --loop --interval
5` command works under any process supervisor with restart-on-crash and
start-on-boot (supervisord, a Docker `restart: always` policy plus a
dedicated container/service, a Kubernetes Deployment with 1 replica, etc.).
The systemd unit here is a ready-to-use option, not a requirement -- what
matters for X-11 is that *some* supervisor is actually running the loop in
production, not which one.
