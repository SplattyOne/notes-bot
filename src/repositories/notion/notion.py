from datetime import datetime
import logging
from operator import itemgetter
import uuid

import aiohttp

import models.notion as notion_models
import services.notes as notes_services
import utils.http as http_utils

NOTION_API_URL = 'https://api.notion.com'
NOTION_API_PAGES = '/v1/pages'
NOTION_API_DATABASES = '/v1/databases'
NOTION_API_BLOCKS = '/v1/blocks'

logger = logging.getLogger(__name__)


class NotionClient(notes_services.NoteClientProtocol):

    def __init__(self, notion_session: aiohttp.ClientSession, notion_token: str, database_id: str,
                 status_field_id: str, status_field_value: str, done_field_id: str, knowledge_database_id: str) -> None:
        self._notion_session = http_utils.ClientSession(notion_session)
        self._notion_token = notion_token
        self._database_id = database_id
        self._status_field_id = status_field_id
        self._status_field_value = status_field_value
        self._done_field_id = done_field_id
        self._knowledge_database_id = knowledge_database_id

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
            'POST', NOTION_API_PAGES, message, headers=self._get_token_headers())
        logger.debug('Notion create note answer: %s', answer)
        return

    async def get_notes(self, message: dict = {}) -> list[notion_models.Note]:
        logger.debug('Notion get notes start')
        answer = await self._notion_session.request(
            'POST', NOTION_API_DATABASES + f'/{self._database_id}/query', message, headers=self._get_token_headers())
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
            'PATCH', NOTION_API_PAGES + f'/{note_id}', message, headers=self._get_token_headers())
        logger.debug('Notion delete note answer: %s', answer)
        return

    async def list_pages(self, modified_since: str | None = None, flexible_limit: int | None = None) -> list[dict]:
        logger.debug('Notion list pages start')
        # get all pages iteratively
        pages: list[dict] = []
        next_cursor = None
        while True:
            message = {}
            if next_cursor:
                message["start_cursor"] = next_cursor
            url = NOTION_API_DATABASES + f'/{self._knowledge_database_id}/query'
            answer = await self._notion_session.request('POST', url, message, headers=self._get_token_headers())
            results: list[dict] = answer.get("results", [])
            pages.extend(results)
            next_cursor = answer.get("next_cursor")
            if not answer.get("has_more"):
                break
        logger.debug(f"Found {len(pages)} pages")
        # filter modified_since
        if modified_since:
            pages = self._filter_pages_by_edited_time(pages, modified_since)
        if flexible_limit:
            pages = self._filter_pages_by_flexible_limit(pages, flexible_limit)
        return pages

    @staticmethod
    def _filter_pages_by_edited_time(results: list[dict], modified_since: str) -> list[dict]:
        try:
            filter_time = datetime.fromisoformat(modified_since.replace('Z', '+00:00'))
            filtered_results = []
            for page in results:
                page_time_str = page.get('last_edited_time', '')
                if page_time_str:
                    try:
                        page_time = datetime.fromisoformat(page_time_str.replace('Z', '+00:00'))
                        if page_time > filter_time:
                            filtered_results.append(page)
                    except ValueError:
                        filtered_results.append(page)
            logger.debug(f"After filtering by datetime: {len(filtered_results)} pages")
            return filtered_results
        except Exception as e:
            logger.error(f"Error filtering by datetime: {e}, returning all pages")
            return results

    @staticmethod
    def _filter_pages_by_flexible_limit(results: list[dict], flexible_limit: int) -> list[dict]:
        try:
            sorted_results = sorted(results, key=itemgetter("last_edited_time"))
            filtered_results = sorted_results[:flexible_limit]
            # If there are more pages, check theirs last_edited_time, if it is not the same as in last_element.
            # Without this doing, other pages with same last_edited_time will be lost.
            if len(filtered_results) != len(sorted_results):
                last_elem_page_time_str = filtered_results[-1].get('last_edited_time', '')
                for page in sorted_results[flexible_limit:]:
                    if last_elem_page_time_str == page.get('last_edited_time', ''):
                        filtered_results += [page]
                    else:
                        break
            logger.debug(f"After filtering by flexible_limit {flexible_limit}: {len(filtered_results)} pages")
            return filtered_results
        except Exception as e:
            logger.error(f"Error filtering by flexible_limit {flexible_limit}: {e}, returning all pages")
            return results

    async def get_page_blocks(self, page_id: str) -> list[dict]:
        logger.debug('Notion get page blocks start')
        blocks: list[dict] = []
        next_cursor = None
        while True:
            message = {}
            if next_cursor:
                message["start_cursor"] = next_cursor
            url = NOTION_API_BLOCKS + f'/{page_id}/children'
            answer = await self._notion_session.request('GET', url, None, params=message,
                                                        headers=self._get_token_headers())
            results: list[dict] = answer.get("results", [])
            blocks.extend(results)
            # get with block children
            for block in results:
                if block.get("has_children"):
                    child_blocks = await self.get_page_blocks(block['id'])
                    blocks.extend(child_blocks)
            next_cursor = answer.get("next_cursor")
            if not answer.get("has_more"):
                break
        logger.debug(f"Found {len(blocks)} blocks")
        return blocks
