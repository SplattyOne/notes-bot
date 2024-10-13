import logging
import uuid

import aiohttp

import models.notion as notion_models
import services.notes as notes_services
import utils.http as http_utils

NOTION_API_URL = 'https://api.notion.com'
NOTION_API_CREATE_NOTE = '/v1/pages'
NOTION_API_DELETE_NOTE = '/v1/pages'
NOTION_API_GET_NOTES = '/v1/databases'

logger = logging.getLogger(__name__)


class NotionClient(notes_services.NoteClientProtocol):

    def __init__(self, notion_session: aiohttp.ClientSession, notion_token: str, database_id: str,
                 status_field_id: str, status_field_value: str, done_field_id: str) -> None:
        self._notion_session = http_utils.ClientSession(notion_session)
        self._notion_token = notion_token
        self._database_id = database_id
        self._status_field_id = status_field_id
        self._status_field_value = status_field_value
        self._done_field_id = done_field_id

    def _get_token_headers(self) -> dict:
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._notion_token}',
            'Notion-Version': '2022-06-28',
        }

    async def create_note(self, text: str) -> None:
        logger.debug('Notion create note start')
        message = {
            'parent': {
                'database_id': self._database_id
            },
            'properties': {
                'Name': {'title': [{'text': {'content': text}}]},
                'Status': {'status': {'id': self._status_field_value}},
            }
        }
        answer = await self._notion_session.request(
            'POST', NOTION_API_CREATE_NOTE, message, headers=self._get_token_headers())
        logger.debug('Notion create note answer: %s', answer)
        return

    async def get_notes(self, message: dict = {}) -> list[notion_models.Note]:
        logger.debug('Notion get notes start')
        answer = await self._notion_session.request(
            'POST', NOTION_API_GET_NOTES + f'/{self._database_id}/query', message, headers=self._get_token_headers())
        answer_model = notion_models.NotesAnswer(**answer)
        notes = answer_model.to_notes()

        logger.debug('Notion get notes answer: %s', notes)
        return notes

    async def get_done_notes(self) -> list[notion_models.Note]:
        message = {
            'filter': {
                'property': self._done_field_id,
                'checkbox': {
                    'equals': True
                }
            }
        }
        return await self.get_notes(message)

    async def get_undone_notes(self) -> list[notion_models.Note]:
        message = {
            'filter': {
                'property': self._done_field_id,
                'checkbox': {
                    'equals': False
                }
            }
        }
        return await self.get_notes(message)

    async def delete_note(self, note_id: uuid.UUID) -> None:
        logger.debug('Notion delete note start')
        message = {
            'archived': True,
        }
        answer = await self._notion_session.request(
            'PATCH', NOTION_API_DELETE_NOTE + f'/{note_id}', message, headers=self._get_token_headers())
        logger.debug('Notion delete note answer: %s', answer)
        return
