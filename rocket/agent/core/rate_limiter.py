"""Rate limiter for API calls.

Prevents overwhelming the API with too many requests.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Deque
from collections import deque


@dataclass
class RateLimiter:
    """
    Token bucket rate limiter.
    
    Limits requests to max_requests per window_seconds.
    """
    
    max_requests: int = 1
    window_seconds: float = 2.0
    
    def __post_init__(self):
        self._timestamps: Deque[float] = deque(maxlen=self.max_requests)
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> float:
        """
        Acquire a request slot.
        
        Returns the wait time (0 if no wait needed).
        """
        async with self._lock:
            now = time.time()
            
            # Remove expired timestamps
            while self._timestamps and now - self._timestamps[0] > self.window_seconds:
                self._timestamps.popleft()
            
            # Check if we can proceed
            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(now)
                return 0.0
            
            # Calculate wait time
            oldest = self._timestamps[0]
            wait_time = self.window_seconds - (now - oldest)
            
            if wait_time > 0:
                print(f"[RATE LIMIT] Waiting {wait_time:.2f}s before next request")
                await asyncio.sleep(wait_time)
            
            self._timestamps.append(time.time())
            return wait_time
    
    def sync_acquire(self) -> float:
        """Synchronous version of acquire."""
        now = time.time()
        
        # Remove expired timestamps
        while self._timestamps and now - self._timestamps[0] > self.window_seconds:
            self._timestamps.popleft()
        
        # Check if we can proceed
        if len(self._timestamps) < self.max_requests:
            self._timestamps.append(now)
            return 0.0
        
        # Calculate wait time
        oldest = self._timestamps[0]
        wait_time = self.window_seconds - (now - oldest)
        
        if wait_time > 0:
            print(f"[RATE LIMIT] Waiting {wait_time:.2f}s before next request")
            time.sleep(wait_time)
        
        self._timestamps.append(time.time())
        return wait_time


# Global rate limiter instance
RATE_LIMITER = RateLimiter(max_requests=1, window_seconds=2.0)


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter."""
    return RATE_LIMITER
