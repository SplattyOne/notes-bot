import typing
import uuid

import handlers.notes as notes_handlers
import models.notes as notes_models


class NoteClientProtocol(typing.Protocol):
    async def create_note(self, message: str) -> None:
        ...

    async def get_notes(self) -> list[notes_models.Note]:
        ...

    async def get_undone_notes(self) -> list[notes_models.Note]:
        ...

    async def get_done_notes(self) -> list[notes_models.Note]:
        ...

    async def delete_note(self, note_id: uuid.UUID) -> None:
        ...


class NoteService(notes_handlers.NotesServiceProtocol):
    def __init__(self, notes_client: NoteClientProtocol) -> None:
        self._notes_client = notes_client

    async def create_note(self, text: str) -> None:
        await self._notes_client.create_note(text)

    async def get_notes(self) -> list[notes_models.Note]:
        return await self._notes_client.get_notes()

    async def get_undone_note_titles(self) -> list[str]:
        undone_notes = await self._notes_client.get_undone_notes()
        undone_note_titles = list(map(lambda x: '[%s] %s' % (
            x.status[:5],
            x.title
        ), undone_notes))
        return sorted(undone_note_titles)

    async def get_done_note_ids(self) -> list[uuid.UUID]:
        done_notes = await self._notes_client.get_done_notes()
        done_note_ids = list(map(lambda x: x.id, done_notes))
        return done_note_ids

    async def delete_note(self, note_id: uuid.UUID) -> None:
        return await self._notes_client.delete_note(note_id)
