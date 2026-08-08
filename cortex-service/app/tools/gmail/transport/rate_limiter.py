"""Per-project token-bucket limiter to pre-empt 429s."""

import asyncio
import time

class TokenBucketLimiter:
    def __init__(self, rate_per_sec: float = 5.0, burst: int = 10):
        self.rate = rate_per_sec
        self.capacity = burst
        self._tokens: dict[str, float] = {}
        self._last_check: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, project_id: str):
        async with self._lock:
            now = time.monotonic()
            last = self._last_check.get(project_id, now)
            tokens = self._tokens.get(project_id, self.capacity)
            
            # Replenish tokens based on time passed
            tokens = min(self.capacity, tokens + (now - last) * self.rate)
            
            while tokens < 1:
                await asyncio.sleep((1 - tokens) / self.rate)
                now = time.monotonic()
                tokens = min(self.capacity, tokens + (now - last) * self.rate)
                last = now
                
            tokens -= 1
            self._tokens[project_id] = tokens
            self._last_check[project_id] = now