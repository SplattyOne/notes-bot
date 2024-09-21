import logging
import typing

logger = logging.getLogger(__name__)


class MessageServiceProtocol(typing.Protocol):
    async def handle_messages(self, callback: typing.Coroutine) -> None:
        ...

    async def handle_notes_request(self, callback: typing.Coroutine) -> None:
        ...


class NotesServiceProtocol(typing.Protocol):
    async def create_note(self, text: str) -> None:
        ...

    async def get_notes(self) -> dict:
        ...


class NotesHandler:
    def __init__(self, message_service: MessageServiceProtocol, notes_service: NotesServiceProtocol) -> None:
        self._message_service = message_service
        self._notes_service = notes_service

    async def transmit_messages(self) -> None:
        await self._message_service.handle_messages(self._notes_service.create_note)
        await self._message_service.handle_notes_request(self._notes_service.get_notes)
        logger.info(
            'Message handlers initialized (%s) => {%s}.',
            self._message_service.__class__.__name__,
            self._notes_service.__class__.__name__,
        )
