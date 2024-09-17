import logging
import os
from datetime import datetime

import aiohttp
import orjson

import models.teamly as teamly_models
from .teamly import TeamlyAuthClientProtocol
import utils.http as http_utils

TEAMLY_API_AUTH = '/api/v1/auth/integration/authorize'
TEAMLY_API_REFRESH = '/api/v1/auth/integration/refresh'
TEAMLY_TOKEN_FILE = 'teamly_tokens.json'

logger = logging.getLogger(__name__)


class TeamlyAuthClient(TeamlyAuthClientProtocol):
    _teamly_tokens = None

    def __init__(self, teamly_session: aiohttp.ClientSession, tmp_dir: str,
                 integration_id: str, integration_url: str, client_secret: str, client_auth_code: str) -> None:
        self._teamly_session = http_utils.ClientSession(teamly_session)
        self._tmp_dir = tmp_dir
        self._integration_id = integration_id
        self._integration_url = integration_url
        self._client_secret = client_secret
        self._client_auth_code = client_auth_code

    async def _get_auth_tokens(self) -> teamly_models.AuthTokensAnswer:
        logger.debug('Teamly auth start')
        message_auth = {
            'client_id': self._integration_id,
            'redirect_uri': self._integration_url,
            'client_secret': self._client_secret,
            'code': self._client_auth_code
        }
        answer = await self._teamly_session.request('POST', TEAMLY_API_AUTH, message_auth)
        logger.debug('Teamly auth answer: %s', answer)
        return teamly_models.AuthTokensAnswer(**answer)

    async def _refresh_auth_tokens(self, refresh_token: str) -> teamly_models.AuthTokensAnswer:
        logger.debug('Teamly refresh start')
        message_refresh = {
            'client_id': self._integration_id,
            'client_secret': self._client_secret,
            'refresh_token': refresh_token
        }
        answer = await self._teamly_session.request('POST', TEAMLY_API_REFRESH, message_refresh)
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

    def _write_tokens(self, teamly_tokens: teamly_models.AuthTokens) -> teamly_models.AuthTokens:
        teamly_tokens_path = os.path.join(self._tmp_dir, TEAMLY_TOKEN_FILE)
        with open(teamly_tokens_path, 'w') as file_opened:
            file_opened.write(teamly_tokens.model_dump_json())
        self._teamly_tokens = teamly_tokens
        return teamly_tokens

    async def _handle_tokens(self) -> teamly_models.AuthTokens:
        teamly_tokens = self._read_tokens()
        if not teamly_tokens.refresh_token_expires_at or \
                datetime.fromtimestamp(teamly_tokens.refresh_token_expires_at) < datetime.now():
            answer = await self._get_auth_tokens()
            teamly_tokens = self._write_tokens(answer.to_auth_tokens())
        if not teamly_tokens.access_token_expires_at or \
                datetime.fromtimestamp(teamly_tokens.access_token_expires_at) < datetime.now():
            answer = await self._refresh_auth_tokens(teamly_tokens.refresh_token)
            teamly_tokens = self._write_tokens(answer.to_auth_tokens())
        return teamly_tokens

    async def get_token_headers(self) -> dict:
        teamly_tokens = await self._handle_tokens()
        return {
            'X-Account-Slug': teamly_tokens.slug,
            'Authorization': 'Bearer %s' % (teamly_tokens.access_token,)
        }
