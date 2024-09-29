import logging
import typing

import handlers.notes as notes_handlers

logger = logging.getLogger(__name__)


class YonoteClientProtocol(typing.Protocol):
    async def create_note(self, message: str) -> None:
        ...

    async def get_notes(self) -> list:
        ...


class YonoteService(notes_handlers.NotesServiceProtocol):
    def __init__(self, notes_client: YonoteClientProtocol) -> None:
        self._notes_client = notes_client

    async def create_note(self, text: str) -> None:
        await self._notes_client.create_note(text)

    async def get_notes(self) -> list:
        return await self._notes_client.get_notes()
