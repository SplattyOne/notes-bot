from enum import Enum

import handlers.notes as notes_handlers


class FilterModes(Enum):
    CREATE_ALL = 'CREATE_ALL'
    CREATE_WITH_FILTER = 'CREATE_WITH_FILTER'


class NotesFilter(notes_handlers.NotesFilterProtocol):
    _mode: FilterModes = FilterModes.CREATE_ALL

    def __init__(self, notes_services: list[notes_handlers.NotesServiceProtocol]) -> None:
        self._notes_services = notes_services
        if len(self._get_note_service_with_start_words()) > 0:
            self._mode = FilterModes.CREATE_WITH_FILTER

    @staticmethod
    def _is_start_word_exists(start_words: list[str], text: str) -> bool:
        for start_word in start_words:
            if text.strip().lower().startswith(start_word.lower()):
                return True
        return False

    def _get_note_service_with_start_words(self) -> list[notes_handlers.NotesServiceProtocol]:
        return list(filter(lambda x: len(x.start_words) > 0, self._notes_services))

    def _get_note_service_without_start_words(self) -> list[notes_handlers.NotesServiceProtocol]:
        return list(filter(lambda x: len(x.start_words) == 0, self._notes_services))

    def get_needed_to_create_notes(self, text: str) -> list[notes_handlers.NotesServiceProtocol]:
        if self._mode == FilterModes.CREATE_ALL:
            return self._notes_services
        needed_to_create_notes = []
        for notes_service in self._get_note_service_with_start_words():
            if self._is_start_word_exists(notes_service.start_words, text):
                needed_to_create_notes += [notes_service]
        if len(needed_to_create_notes) > 0:
            return needed_to_create_notes
        return self._get_note_service_without_start_words()
