import logging

import services.notes as notes_services

logger = logging.getLogger(__name__)


class YonoteService(notes_services.NoteService):
    """Concrete realization of Yonote Service"""
