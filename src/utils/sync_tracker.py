import asyncio
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class SyncTracker:
    def __init__(self, sync_file: str = 'last_sync.txt'):
        self._sync_file: str = sync_file
        self._sync_time: str = ""

    async def get_last_sync_time(self) -> str | None:
        """Get last sync timestamp from file (async)."""
        if not await asyncio.to_thread(os.path.exists, self._sync_file):
            return None
        try:
            def _read(path: str) -> str:
                with open(path, 'r') as f:
                    return f.read().strip()
            self._sync_time = await asyncio.to_thread(_read, self._sync_file)
            return self._sync_time
        except Exception:
            return None

    async def update_sync_time(self, timestamp: str) -> None:
        """Update last sync timestamp to file (async)."""
        try:
            def _write(path: str, data: str) -> None:
                with open(path, 'w') as f:
                    f.write(data)
            await asyncio.to_thread(_write, self._sync_file, timestamp)
            self._sync_time = timestamp
        except Exception as e:
            logger.warning(f'Could not update sync time: {e}')

    async def update_sync_time_if_bigger(self, timestamp: str) -> None:
        """Update last sync timestamp to file (async) if it is bigger than prev."""
        if not timestamp:
            return
        if not self._sync_time or self._is_bigger(timestamp, self._sync_time):
            return await self.update_sync_time(timestamp)

    @staticmethod
    def _is_bigger(new_timestamp: str, prev_timestamp: str) -> bool:
        try:
            new_time = datetime.fromisoformat(new_timestamp.replace('Z', '+00:00'))
            prev_time = datetime.fromisoformat(prev_timestamp.replace('Z', '+00:00'))
            if new_time > prev_time:
                return True
        except ValueError:
            pass
        return False
