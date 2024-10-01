import logging

import services.notes as notes_services

logger = logging.getLogger(__name__)


class TeamlyService(notes_services.NoteService):
    """Concrete realization of Teamly Service"""
