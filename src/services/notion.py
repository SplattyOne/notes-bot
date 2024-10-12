import logging

import services.notes as notes_services

logger = logging.getLogger(__name__)


class NotionService(notes_services.NoteService):
    """Concrete realization of Notion Service"""
