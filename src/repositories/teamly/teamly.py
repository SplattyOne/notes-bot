import logging
import typing
import uuid
from contextlib import asynccontextmanager

import aiohttp

import models.teamly as teamly_models
import services.notes as notes_services
import utils.http as http_utils

TEAMLY_API_URL = 'https://app4.teamly.ru'
TEAMLY_API_CREATE_NOTE = '/api/v1/wiki/properties/command/execute'
TEAMLY_API_GET_NOTES = '/api/v1/ql/content-database/content'

logger = logging.getLogger(__name__)


@asynccontextmanager
async def teamly_session_context(*args, **kwargs) -> typing.AsyncGenerator[aiohttp.ClientSession, None]:
    """Context manager for Teamly session"""
    async with aiohttp.ClientSession(TEAMLY_API_URL, *args, **kwargs) as session:
        yield session


class TeamlyAuthClientProtocol(typing.Protocol):
    async def get_token_headers(self) -> dict:
        ...


class TeamlyClient(notes_services.NoteClientProtocol):
    _integration_id = None
    _integration_url = None
    _client_secret = None
    _client_auth_code = None
    _teamly_tokens = None

    def __init__(self, teamly_session: aiohttp.ClientSession, teamly_auth: TeamlyAuthClientProtocol,
                 database_id: str, status_field_id: str, status_field_value: str, done_field_id: str) -> None:
        self._teamly_session = http_utils.ClientSession(teamly_session)
        self._teamly_auth = teamly_auth
        self._database_id = database_id
        self._status_field_id = status_field_id
        self._status_field_value = status_field_value
        self._done_field_id = done_field_id

    async def create_note(self, text: str) -> None:
        logger.debug('Teamly create note start')
        message = {
            "code": "article_create",
            "payload": {
                "entity": {
                    "spaceId": self._database_id,
                    "id": str(uuid.uuid4()),
                    "properties": [
                        {
                            "method": "add",
                            "code": "title",
                            "value": {
                                "text": text
                            },
                        },
                        {
                            "method": "add",
                            "code": self._status_field_id,
                            "value": self._status_field_value
                        }
                    ]
                }
            }
        }
        answer = await self._teamly_session.request(
            'POST', TEAMLY_API_CREATE_NOTE, message, headers=await self._teamly_auth.get_token_headers())
        logger.debug('Teamly create note answer: %s', answer)
        return

    async def get_notes(self) -> list[teamly_models.Note]:
        logger.debug('Teamly get notes start')
        message = {
            "query": {
                "__filter": {
                    "contentDatabaseId": self._database_id
                },
                "id": True,
                "title": True,
                "content": {
                    "article": {
                        "id": True,
                        "properties": {
                            "properties": True
                        }
                    },
                },
            }
        }
        answer = await self._teamly_session.request(
            'POST', TEAMLY_API_GET_NOTES, message, headers=await self._teamly_auth.get_token_headers())
        answer_model = teamly_models.NotesAnswer(**answer)
        notes = answer_model.to_notes(self._status_field_id, self._done_field_id)

        logger.debug('Teamly get notes answer: %s', notes)
        return notes

    async def get_done_notes(self) -> list[teamly_models.Note]:
        notes = await self.get_notes()
        done_notes = list(filter(lambda x: x.done, notes))
        return done_notes

    async def get_undone_notes(self) -> list[teamly_models.Note]:
        notes = await self.get_notes()
        undone_notes = list(filter(lambda x: not x.done, notes))
        return undone_notes

    async def delete_note(self, note_id: uuid.UUID) -> None:
        logger.debug('Teamly delete note start')
        raise NotImplementedError('Method not implemented for Teamly repository')
