import asyncio
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class SyncTracker:
    def __init__(self, sync_file: str = 'last_sync.txt'):
        self.sync_file = sync_file

    async def get_last_sync_time(self) -> str | None:
        """Get last sync timestamp from file (async)."""
        if not await asyncio.to_thread(os.path.exists, self.sync_file):
            return None
        try:
            def _read(path: str) -> str:
                with open(path, 'r') as f:
                    return f.read().strip()
            return await asyncio.to_thread(_read, self.sync_file)
        except Exception:
            return None

    async def update_sync_time(self, timestamp: str) -> None:
        """Update last sync timestamp to file (async)."""
        try:
            def _write(path: str, data: str) -> None:
                with open(path, 'w') as f:
                    f.write(data)
            await asyncio.to_thread(_write, self.sync_file, timestamp)
        except Exception as e:
            logger.warning(f'Could not update sync time: {e}')

    def get_current_time(self) -> str:
        """Get current ISO timestamp."""
        return datetime.utcnow().isoformat() + 'Z'
