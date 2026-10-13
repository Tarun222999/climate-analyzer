from collections import deque
from time import monotonic


class RequestRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock=monotonic,
    ):
        if limit < 1 or window_seconds <= 0:
            raise ValueError("Request limit and window must be positive")

        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self.events: dict[str, deque[float]] = {}

    def reserve(self, client_key: str) -> float:
        now = self.clock()
        cutoff = now - self.window_seconds

        # Remove expired requests and inactive client entries.
        for key in list(self.events):
            timestamps = self.events[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if not timestamps:
                del self.events[key]

        timestamps = self.events.setdefault(client_key, deque())

        if len(timestamps) >= self.limit:
            return timestamps[0] + self.window_seconds - now

        timestamps.append(now)
        return 0.0
        

class RequestConcurrencyLimiter:
    def __init__(self, maximum_active: int):
        if maximum_active < 1:
            raise ValueError("Maximum active requests must be positive")

        self.maximum_active = maximum_active
        self.active = 0

    def try_acquire(self) -> bool:
        if self.active >= self.maximum_active:
            return False

        self.active += 1
        return True

    def release(self) -> None:
        if self.active <= 0:
            raise RuntimeError("No active request to release")

        self.active -= 1