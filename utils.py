import functools
from typing import Callable, Any
import time

def timed_cache(ttl_seconds=60):
    """Simple in-process ttl cache decorator"""
    def deco(func):
        cache = {}
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            if key in cache:
                ts, val = cache[key]
                if now - ts < ttl_seconds:
                    return val
            val = await func(*args, **kwargs)
            cache[key] = (now, val)
            return val
        return wrapper
    return deco