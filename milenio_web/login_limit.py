"""A bounded login-attempt counter for the single-instance workshop."""
import ipaddress
import sqlite3
import time
from contextlib import closing

from django.conf import settings
from django.utils.crypto import salted_hmac


def reserve_login(address):
    """Return a reservation to release on success, or the seconds a client must wait."""
    try:
        client = ipaddress.ip_address(address)
        key = (client.packed if client.version == 4 else client.packed[:8])
    except ValueError:
        key = b"unknown"
    # At most 65,536 rows; no raw address or username is retained.
    bucket = int.from_bytes(salted_hmac("cloud-login", key, algorithm="sha256").digest()[:2], "big")
    now = int(time.time())
    database = settings.DATA_DIR / ".login-limits.sqlite3"
    with closing(sqlite3.connect(database, timeout=3)) as connection, connection:
        connection.execute("CREATE TABLE IF NOT EXISTS quota (bucket INTEGER PRIMARY KEY, expires INTEGER, used INTEGER)")
        connection.execute("BEGIN IMMEDIATE")
        previous = connection.execute("SELECT expires, used FROM quota WHERE bucket=?", (bucket,)).fetchone()
        if previous and previous[0] > now:
            if previous[1] >= 10:
                return None, previous[0] - now
            connection.execute("UPDATE quota SET used=used+1 WHERE bucket=?", (bucket,))
            expires = previous[0]
        else:
            expires = now + 300
            connection.execute("INSERT OR REPLACE INTO quota VALUES (?, ?, 1)", (bucket, expires))
    return (bucket, expires), 0


def release_success(reservation):
    # Count failed attempts without locking out a shift sharing the same shop Wi-Fi.
    # A success may only return its own slot and only in the same window.
    with closing(sqlite3.connect(settings.DATA_DIR / ".login-limits.sqlite3", timeout=3)) as connection, connection:
        connection.execute("UPDATE quota SET used=used-1 WHERE bucket=? AND expires=? AND used>0", reservation)
