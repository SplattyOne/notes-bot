import logging
import typing

import handlers.notes as notes_handlers

logger = logging.getLogger(__name__)


class TeamlyClientProtocol(typing.Protocol):
    async def create_note(message: str) -> None:
        ...


class TeamlyService(notes_handlers.NotesServiceProtocol):
    def __init__(self, teamly_client: TeamlyClientProtocol) -> None:
        self._teamly_client = teamly_client

    async def create_note(self, text: str) -> None:
        await self._teamly_client.create_note(text)
