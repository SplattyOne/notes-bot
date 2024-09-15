import logging
import os
import typing
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import aiohttp
import orjson

import models.teamly as teamly_models

TEAMLY_API_URL = 'https://app4.teamly.ru'
TEAMLY_API_AUTH = '/api/v1/auth/integration/authorize'
TEAMLY_API_REFRESH = '/api/v1/auth/integration/refresh'
TEAMLY_API_CREATE_NOTE = '/api/v1/wiki/properties/command/execute'
TEAMLY_TOKEN_FILE = 'teamly_tokens.json'

logger = logging.getLogger(__name__)


@asynccontextmanager
async def teamly_session_context(*args, **kwargs) -> typing.AsyncGenerator[aiohttp.ClientSession, None]:
    """Context manager for Teamly session"""
    async with aiohttp.ClientSession(TEAMLY_API_URL, *args, **kwargs) as session:
        yield session


class TeamlyClient:
    _integration_id = None
    _integration_url = None
    _client_secret = None
    _client_auth_code = None
    _teamly_tokens = None

    def __init__(self, teamly_session: aiohttp.ClientSession, tmp_dir: str, database_id: str,
                 status_field_id: str, status_field_value: str) -> None:
        self._teamly_session = teamly_session
        self._tmp_dir = tmp_dir
        self._database_id = database_id
        self._status_field_id = status_field_id
        self._status_field_value = status_field_value

    def with_session(
            self, integration_id: str, integration_url: str, client_secret: str, client_auth_code: str):
        self._integration_id = integration_id
        self._integration_url = integration_url
        self._client_secret = client_secret
        self._client_auth_code = client_auth_code
        return self

    async def _request(self, url: str, json_data: dict, **kwargs) -> dict:
        async with self._teamly_session.post(
            url,
            json=json_data,
            **kwargs
        ) as response:
            text_response = await response.text()
            try:
                answer = orjson.loads(text_response)
            except orjson.JSONDecodeError:
                logger.error('Wrong json answer: %s', text_response)
                raise
            return answer

    async def _get_auth_tokens(self) -> teamly_models.AuthTokensAnswer:
        logger.debug('Teamly auth start')
        message_auth = {
            'client_id': self._integration_id,
            'redirect_uri': self._integration_url,
            'client_secret': self._client_secret,
            'code': self._client_auth_code
        }
        answer = await self._request(TEAMLY_API_AUTH, message_auth)
        logger.debug('Teamly auth answer: %s', answer)
        return teamly_models.AuthTokensAnswer(**answer)

    async def _refresh_auth_tokens(self, refresh_token: str) -> teamly_models.AuthTokensAnswer:
        logger.debug('Teamly refresh start')
        message_refresh = {
            'client_id': self._integration_id,
            'client_secret': self._client_secret,
            'refresh_token': refresh_token
        }
        answer = await self._request(TEAMLY_API_REFRESH, message_refresh)
        logger.debug('Teamly refresh answer: %s', answer)
        return teamly_models.AuthTokensAnswer(**answer)

    def _read_tokens(self) -> teamly_models.AuthTokens:
        if self._teamly_tokens:
            return self._teamly_tokens
        teamly_tokens_path = os.path.join(self._tmp_dir, TEAMLY_TOKEN_FILE)
        if not os.path.exists(teamly_tokens_path):
            open(teamly_tokens_path, 'w').close()
        with open(teamly_tokens_path, 'r') as file_opened:
            content = file_opened.read()
        try:
            teamly_tokens = orjson.loads(content)
        except orjson.JSONDecodeError:
            teamly_tokens = {}
        self._teamly_tokens = teamly_models.AuthTokens(**teamly_tokens)
        return self._teamly_tokens

    def _write_tokens(self, teamly_tokens: teamly_models.AuthTokens) -> None:
        teamly_tokens_path = os.path.join(self._tmp_dir, TEAMLY_TOKEN_FILE)
        with open(teamly_tokens_path, 'w') as file_opened:
            file_opened.write(teamly_tokens.model_dump_json())
        self._teamly_tokens = teamly_tokens

    async def _handle_tokens(self) -> teamly_models.AuthTokens:
        teamly_tokens = self._read_tokens()
        if not teamly_tokens.refresh_token_expires_at or \
                datetime.fromtimestamp(teamly_tokens.refresh_token_expires_at) < datetime.now():
            answer = await self._get_auth_tokens()
            self._write_tokens(answer.to_auth_tokens())
        if not teamly_tokens.access_token_expires_at or \
                datetime.fromtimestamp(teamly_tokens.access_token_expires_at) < datetime.now():
            answer = await self._refresh_auth_tokens(teamly_tokens.refresh_token)
            self._write_tokens(answer.to_auth_tokens())
        return teamly_tokens

    async def _get_token_headers(self) -> dict:
        teamly_tokens = await self._handle_tokens()
        return {
            'X-Account-Slug': teamly_tokens.slug,
            'Authorization': 'Bearer %s' % (teamly_tokens.access_token,)
        }

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
        answer = await self._request(
            TEAMLY_API_CREATE_NOTE, message_create, headers=await self._get_token_headers())
        logger.debug('Teamly create note answer: %s', answer)
        return answer
