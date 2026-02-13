import hashlib
import ipaddress
import time
from collections import defaultdict, deque

from flask import current_app, request


class InMemoryRateLimiter:
    def __init__(self):
        self._buckets = defaultdict(deque)

    def is_limited(self, key, limit, window_seconds):
        now = time.time()
        bucket = self._buckets[key]
        while bucket and bucket[0] <= now - window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return True
        bucket.append(now)
        return False


rate_limiter = InMemoryRateLimiter()


def mask_ip(ip_value):
    if not ip_value:
        return None
    try:
        ip = ipaddress.ip_address(ip_value)
    except ValueError:
        return None

    if isinstance(ip, ipaddress.IPv4Address):
        octets = ip_value.split(".")
        return ".".join(octets[:3]) + ".0/24"
    return str(ip)


def hash_value(raw_value):
    if not raw_value:
        return None
    salt = current_app.config.get("DATA_HASH_SALT", "dev-hash-salt")
    return hashlib.sha256(f"{salt}:{raw_value}".encode("utf-8")).hexdigest()


def request_ip_hash():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.remote_addr or ""
    masked = mask_ip(ip)
    return hash_value(masked)
