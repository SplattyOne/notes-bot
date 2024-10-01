import logging
import typing
import uuid

logger = logging.getLogger(__name__)


class MessageServiceProtocol(typing.Protocol):
    async def handle_messages(self, callback: typing.Coroutine) -> None:
        ...

    async def handle_notes_request(self, callback: typing.Coroutine) -> None:
        ...


class NotesServiceProtocol(typing.Protocol):
    async def create_note(self, text: str) -> None:
        ...

    async def get_undone_note_titles(self) -> list[str]:
        ...

    async def get_done_note_ids(self) -> list[uuid.UUID]:
        ...

    async def delete_note(self, id: uuid.UUID) -> None:
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

    async def _get_notes(self) -> str:
        notes = []
        for notes_service in self._notes_services:
            notes += [notes_service.__class__.__name__ + ':']
            notes += await notes_service.get_undone_note_titles()
        return '\n'.join(notes)

    async def transmit_messages(self) -> None:
        await self._message_service.handle_messages(self._create_notes)
        await self._message_service.handle_notes_request(self._get_notes)
        logger.info(
            'Message handlers initialized (%s) => {%s}.',
            self._message_service.__class__.__name__,
            list(map(lambda x: x.__class__.__name__, self._notes_services)),
        )

    async def delete_done_notes(self) -> None:
        logger.debug('Delete done notes')
        for notes_service in self._notes_services:
            note_ids = await notes_service.get_done_note_ids()
            for note_id in note_ids:
                await notes_service.delete_note(note_id)
