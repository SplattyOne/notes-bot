from functools import lru_cache

from handlers.notes import NotesServiceProtocol

notes_service: NotesServiceProtocol | None = None


@lru_cache
def get_notes_service() -> NotesServiceProtocol:
    return notes_service
