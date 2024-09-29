import logging
import typing
import uuid
from contextlib import asynccontextmanager

import aiohttp

import models.yonote as yonote_models
import utils.http as http_utils

YONOTE_API_URL = 'https://app.yonote.ru'
YONOTE_API_CREATE_NOTE = '/api/documents.create'
YONOTE_API_GET_NOTES = '/api/database.rows.list?limit=100&offset=0'

logger = logging.getLogger(__name__)


@asynccontextmanager
async def yonote_session_context(*args, **kwargs) -> typing.AsyncGenerator[aiohttp.ClientSession, None]:
    """Context manager for Yonote session"""
    async with aiohttp.ClientSession(YONOTE_API_URL, *args, **kwargs) as session:
        yield session


class YonoteClient:

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
        undone_notes = list(filter(lambda x: not x.done, notes))
        undone_notes_titles = list(map(lambda x: '[%s] %s' % (
            x.status,
            x.title
        ), undone_notes))

        logger.debug('Yonote get notes answer: %s', undone_notes_titles)
        return sorted(undone_notes_titles)
