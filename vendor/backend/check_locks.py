import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT
            blocked_locks.pid     AS blocked_pid,
            blocked_activity.usename  AS blocked_user,
            blocking_locks.pid    AS blocking_pid,
            blocking_activity.usename AS blocking_user,
            blocked_activity.query    AS blocked_statement,
            blocking_activity.query   AS blocking_statement,
            age(now(), blocked_activity.query_start) AS blocked_duration
        FROM  pg_catalog.pg_locks         blocked_locks
        JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
        JOIN pg_catalog.pg_locks         blocking_locks 
            ON blocking_locks.locktype = blocked_locks.locktype
            AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
            AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
            AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
            AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
            AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
            AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
            AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
            AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
            AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
            AND blocking_locks.pid != blocked_locks.pid
        JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
        WHERE NOT blocked_locks.granted;
    """)
    rows = cursor.fetchall()
    print(f"Blocked queries count: {len(rows)}")
    for r in rows:
        print(f"Blocked PID {r[0]} ({r[6]}) waiting for Blocking PID {r[2]}")
        print(f"  Blocked query: {r[4][:120]}")
        print(f"  Blocking query: {r[5][:120]}")
