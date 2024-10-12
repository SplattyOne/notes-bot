import logging
import uuid

import aiohttp

import models.yonote as yonote_models
import services.notes as notes_services
import utils.http as http_utils

YONOTE_API_URL = 'https://app.yonote.ru'
YONOTE_API_CREATE_NOTE = '/api/documents.create'
YONOTE_API_DELETE_NOTE = '/api/documents.delete'
YONOTE_API_GET_NOTES = '/api/database.rows.list?limit=100&offset=0'

logger = logging.getLogger(__name__)


class YonoteClient(notes_services.NoteClientProtocol):

    def __init__(self, yonote_session: aiohttp.ClientSession, yonote_token: str, database_id: str,
                 collection_id: str, status_field_id: str, status_field_value: str, done_field_id: str) -> None:
        self._yonote_session = http_utils.ClientSession(yonote_session)
        self._yonote_token = yonote_token
        self._database_id = database_id
        self._collection_id = collection_id
        self._status_field_id = status_field_id
        self._status_field_value = status_field_value
        self._done_field_id = done_field_id

    def _get_token_headers(self) -> dict:
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._yonote_token}',
        }

    async def create_note(self, text: str) -> None:
        logger.debug('Yonote create note start')
        message = {
            'id': str(uuid.uuid4()),
            'parentDocumentId': self._database_id,
            'collectionId': self._collection_id,
            'title': text,
            'properties': {
                self._status_field_id: [self._status_field_value],
                self._done_field_id: 0,
            },
            'type': 'row',
            'publish': True,
            'text': '',
        }
        answer = await self._yonote_session.request(
            'POST', YONOTE_API_CREATE_NOTE, message, headers=self._get_token_headers())
        logger.debug('Yonote create note answer: %s', answer)
        return

    async def get_notes(self) -> list[yonote_models.Note]:
        logger.debug('Yonote get notes start')
        message = {
            'parentDocumentId': self._database_id,
        }
        answer = await self._yonote_session.request(
            'POST', YONOTE_API_GET_NOTES, message, headers=self._get_token_headers())
        answer_model = yonote_models.NotesAnswer(**answer)
        notes = answer_model.to_notes(self._status_field_id, self._done_field_id)

        logger.debug('Yonote get notes answer: %s', notes)
        return notes

    async def get_done_notes(self) -> list[yonote_models.Note]:
        notes = await self.get_notes()
        done_notes = list(filter(lambda x: x.done, notes))
        return done_notes

    async def get_undone_notes(self) -> list[yonote_models.Note]:
        notes = await self.get_notes()
        undone_notes = list(filter(lambda x: not x.done, notes))
        return undone_notes

    async def delete_note(self, note_id: uuid.UUID) -> None:
        logger.debug('Yonote delete note start')
        message = {
            'id': str(note_id),
            'permanent': False,
        }
        answer = await self._yonote_session.request(
            'POST', YONOTE_API_DELETE_NOTE, message, headers=self._get_token_headers())
        logger.debug('Yonote delete note answer: %s', answer)
        return
