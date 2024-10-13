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
    delete_done_notes: bool = False
    start_words: list[str] = []

    async def create_note(self, text: str) -> None:
        ...

    async def get_undone_note_titles(self) -> list[str]:
        ...

    async def get_done_note_ids(self) -> list[uuid.UUID]:
        ...

    async def delete_note(self, id: uuid.UUID) -> None:
        ...


class NotesFilterProtocol(typing.Protocol):
    def get_needed_to_create_notes(self, text: str) -> list[NotesServiceProtocol]:
        ...


class NotesHandler:
    def __init__(self, message_service: MessageServiceProtocol, filter_class: type[NotesFilterProtocol]) -> None:
        self._message_service = message_service
        self._filter_class = filter_class
        self._notes_services: list[NotesServiceProtocol] = []

    def with_notes_service(self, notes_service: NotesServiceProtocol,
                           delete_done_notes: bool, start_words: list[str]) -> typing.Self:
        notes_service.delete_done_notes = delete_done_notes
        notes_service.start_words = start_words
        self._notes_services += [notes_service]
        return self

    async def _create_notes(self, text: str) -> None:
        for notes_service in self._filter_class(self._notes_services).get_needed_to_create_notes(text):
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
            if notes_service.delete_done_notes:
                note_ids = await notes_service.get_done_note_ids()
                for note_id in note_ids:
                    await notes_service.delete_note(note_id)
