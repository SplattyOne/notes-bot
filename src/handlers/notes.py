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

    async def get_notes(self) -> list:
        ...


class NotesHandler:
    def __init__(self, message_service: MessageServiceProtocol) -> None:
        self._message_service = message_service
        self._notes_services: list[NotesServiceProtocol] = []

    def with_notes_service(self, notes_service: NotesServiceProtocol) -> typing.Self:
        self._notes_services += [notes_service]
        return self

    async def _create_notes(self, text: str) -> None:
        for notes_service in self._notes_services:
            await notes_service.create_note(text)

    async def _get_notes(self) -> list:
        notes = []
        for notes_service in self._notes_services:
            notes += [notes_service.__class__.__name__ + ':']
            notes += await notes_service.get_notes()
        return '\n'.join(notes)

    async def transmit_messages(self) -> None:
        await self._message_service.handle_messages(self._create_notes)
        await self._message_service.handle_notes_request(self._get_notes)
        logger.info(
            'Message handlers initialized (%s) => {%s}.',
            self._message_service.__class__.__name__,
            list(map(lambda x: x.__class__.__name__, self._notes_services)),
        )
