import asyncio

from collections import deque
from time import monotonic



class UsageBudget:
    def __init__(
        self,
        limits=((60, 540), (3600, 4500), (86400, 9000)),
        clock=monotonic,
    ):
        self.limits = limits
        self.clock = clock
        self.events = deque()

    def reserve(self, cost: int) -> float:
        """Return 0 if reserved, or seconds to wait without reserving."""
        if cost <= 0 or cost > min(limit for _, limit in self.limits):
            raise ValueError("Request cost must fit within each budget")

        now = self.clock()
        longest_window = max(window for window, _ in self.limits)

        while self.events and self.events[0][0] <= now - longest_window:
            self.events.popleft()

        delays = []
        for window, limit in self.limits:
            active = [
                (timestamp, units)
                for timestamp, units in self.events
                if timestamp > now - window
            ]
            used = sum(units for _, units in active)

            if used + cost > limit:
                for timestamp, units in active:
                    used -= units
                    if used + cost <= limit:
                        delays.append(timestamp + window - now)
                        break

        if delays:
            return max(delays)

        self.events.append((now, cost))
        return 0.0



outgoing_budget = UsageBudget()

class UsageLimitError(Exception):
    def __init__(self,retry_after:float):
        self.retry_after = retry_after;
        super().__init__("Outgoing API budget exhausted")
    
async def wait_for_usage(cost:int,max_wait:float=60.0)->None:
    deadline = monotonic() + max_wait;
    
    while True:
           delay = outgoing_budget.reserve(cost)
           if delay == 0:
             return 
           if delay > deadline - monotonic():
            raise UsageLimitError(delay)
           await asyncio.sleep(delay)
    
