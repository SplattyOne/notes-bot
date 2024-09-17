import logging
import typing
import uuid
from contextlib import asynccontextmanager

import aiohttp

import utils.http as http_utils

TEAMLY_API_URL = 'https://app4.teamly.ru'
TEAMLY_API_CREATE_NOTE = '/api/v1/wiki/properties/command/execute'

logger = logging.getLogger(__name__)


@asynccontextmanager
async def teamly_session_context(*args, **kwargs) -> typing.AsyncGenerator[aiohttp.ClientSession, None]:
    """Context manager for Teamly session"""
    async with aiohttp.ClientSession(TEAMLY_API_URL, *args, **kwargs) as session:
        yield session


class TeamlyAuthClientProtocol(typing.Protocol):
    async def get_token_headers(self) -> dict:
        ...


class TeamlyClient:
    _integration_id = None
    _integration_url = None
    _client_secret = None
    _client_auth_code = None
    _teamly_tokens = None

    def __init__(self, teamly_session: aiohttp.ClientSession, teamly_auth: TeamlyAuthClientProtocol,
                 database_id: str, status_field_id: str, status_field_value: str) -> None:
        self._teamly_session = http_utils.ClientSession(teamly_session)
        self._teamly_auth = teamly_auth
        self._database_id = database_id
        self._status_field_id = status_field_id
        self._status_field_value = status_field_value

    async def create_note(self, text: str) -> None:
        logger.debug('Teamly create note start')
        message_create = {
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
            'POST', TEAMLY_API_CREATE_NOTE, message_create, headers=await self._teamly_auth.get_token_headers())
        logger.debug('Teamly create note answer: %s', answer)
        return answer
