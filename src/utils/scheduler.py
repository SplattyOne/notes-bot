import typing

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


class Scheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()

    async def run_job(self, func: typing.Coroutine, every_seconds: int) -> None:
        trigger = IntervalTrigger(seconds=every_seconds)
        self._scheduler.add_job(func, trigger=trigger)
        self._scheduler.start()
