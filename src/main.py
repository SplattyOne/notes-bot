import aiohttp
import asyncio
import logging
import os

import uvicorn

from config.settings import get_settings, NoteAppType
from config.logging import configure_logging
from api.app import FastapiFactory
import handlers.notes as notes_handlers
import handlers.filter as filter_handlers
import repositories.teamly as teamly_repositories
import repositories.yonote as yonote_repositories
import repositories.notion as notion_repositories
import repositories.telegram as telegram_repositories
import repositories.qdrant as qdrant_repositories
import repositories.openai as openai_repositories
import services.teamly as teamly_services
import services.yonote as yonote_services
import services.notion as notion_services
import services.telegram as telegram_services
from utils.sync_tracker import SyncTracker
import utils.recognizer as recognizer_utils
import utils.scheduler as scheduler_utils
import utils.http as http_utils

logger = logging.getLogger(__name__)


class App:
    def __init__(self) -> None:
        self._settings = get_settings()
        configure_logging(self._settings)
        self._configure_dirs()

    def _configure_dirs(self):
        if not os.path.exists(self._settings.common.tmp_dir):
            os.mkdir(self._settings.common.tmp_dir)

    def _construct_notes_handler_services(
        self,
        teamly_session: aiohttp.ClientSession,
        notion_session: aiohttp.ClientSession,
        yonote_session: aiohttp.ClientSession
    ):
        for note_client_config in self._settings.transmit_to:
            if note_client_config.app == NoteAppType.TEAMLY:
                teamly_auth = teamly_repositories.TeamlyAuthClient(
                    teamly_session,
                    self._settings.common.tmp_dir,
                    note_client_config.integration_id,
                    note_client_config.integration_url,
                    note_client_config.client_secret,
                    note_client_config.client_auth_code
                )
                teamly_client = teamly_repositories.TeamlyClient(
                    teamly_session,
                    teamly_auth,
                    note_client_config.database_id,
                    note_client_config.status_field_id,
                    note_client_config.status_field_value,
                    note_client_config.done_field_id
                )
                teamly_service = teamly_services.TeamlyService(teamly_client)
                self._notes_handler = self._notes_handler.with_notes_service(
                    teamly_service,
                    note_client_config.delete_done_notes,
                    note_client_config.start_words
                )
            elif note_client_config.app == NoteAppType.NOTION:
                notion_client = notion_repositories.NotionClient(
                    notion_session,
                    note_client_config.token,
                    note_client_config.database_id,
                    note_client_config.status_field_id,
                    note_client_config.status_field_value,
                    note_client_config.done_field_id,
                    note_client_config.knowledge_database_id
                )
                notion_service = notion_services.NotionService(notion_client)
                self._notes_handler = self._notes_handler.with_notes_service(
                    notion_service,
                    note_client_config.delete_done_notes,
                    note_client_config.start_words
                )
            elif note_client_config.app == NoteAppType.YONOTE:
                yonote_client = yonote_repositories.YonoteClient(
                    yonote_session,
                    note_client_config.token,
                    note_client_config.database_id,
                    note_client_config.collection_id,
                    note_client_config.status_field_id,
                    note_client_config.status_field_value,
                    note_client_config.done_field_id
                )
                yonote_service = yonote_services.YonoteService(yonote_client)
                self._notes_handler = self._notes_handler.with_notes_service(
                    yonote_service,
                    note_client_config.delete_done_notes,
                    note_client_config.start_words
                )
            else:
                raise ValueError(f'Unknown note app {note_client_config.app}')

    async def run_async_worker(self) -> None:
        async with http_utils.aiohttp_session_context(teamly_repositories.TEAMLY_API_URL) as teamly_session, \
                http_utils.aiohttp_session_context(yonote_repositories.YONOTE_API_URL) as yonote_session, \
                http_utils.aiohttp_session_context(notion_repositories.NOTION_API_URL) as notion_session, \
                telegram_repositories.telegram_app_context(self._settings.transmit_from.token) as telegram_app:
            self._recognizer = recognizer_utils.SpeechRecognizer(self._settings.common.tmp_dir)
            telegram_client = telegram_repositories.TelegramClient(
                telegram_app,
                self._recognizer,
                self._settings.common.tmp_dir,
                self._settings.transmit_from.allowed_users
            )
            telegram_service = telegram_services.TelegramService(telegram_client)
            vector_store = qdrant_repositories.QdrantVectorStore(
                self._settings.qdrant.url, self._settings.qdrant.collection)
            ai_service = openai_repositories.OpenAIService(
                self._settings.openai.api_key,
                self._settings.openai.embed_model,
                self._settings.openai.main_model,
                self._settings.openai.image_model
            )
            sync_tracker = SyncTracker()
            self._notes_handler = notes_handlers.NotesHandler(telegram_service, filter_handlers.NotesFilter)
            self._construct_notes_handler_services(teamly_session, notion_session, yonote_session)
            self._notes_handler.with_sync_knowledge(
                await self.get_notes_service(),
                vector_store, ai_service, sync_tracker
            )

            await self._notes_handler.transmit_messages()
            await scheduler_utils.Scheduler().run_job(
                self._notes_handler.etl_knowledge_to_vector_db,
                every_seconds=self._settings.common.etl_knowledge_interval_seconds
            )
            await scheduler_utils.Scheduler().run_job(
                self._notes_handler.delete_done_notes,
                every_seconds=self._settings.common.delete_done_notes_interval_seconds
            )
            while True:
                await asyncio.sleep(5)

    async def run_async_worker_safe(self) -> None:
        try:
            await self.run_async_worker()
        except asyncio.CancelledError:
            pass

    async def get_notes_service(self) -> notion_services.NotionService:
        notion_session = aiohttp.ClientSession(notion_repositories.NOTION_API_URL)
        notion_client_config = self._settings.get_first_notion_client_config()
        notion_client = notion_repositories.NotionClient(
            notion_session,
            notion_client_config.token,
            notion_client_config.database_id,
            notion_client_config.status_field_id,
            notion_client_config.status_field_value,
            notion_client_config.done_field_id,
            notion_client_config.knowledge_database_id
        )
        notion_service = notion_services.NotionService(notion_client)
        return notion_service

    @staticmethod
    async def close_notes_service(notion_service: notion_services.NotionService):
        await notion_service._notes_client._notion_session._session.close()

    def run(self) -> None:
        logger.warning('Starting app...')
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run_async_worker_safe())

    def run_with_api(self) -> None:
        logger.warning('Starting app and api...')
        app = FastapiFactory(
            self._settings.common.api_name,
            get_notes_service=self.get_notes_service,
            close_notes_service=self.close_notes_service,
            worker_service=self.run_async_worker_safe
        )
        uvicorn.run(
            app.app,
            host=self._settings.common.api_host,
            port=int(self._settings.common.api_port)
        )

    def close(self) -> None:
        logger.warning('Closing app...')


if __name__ == '__main__':
    app = App()
    try:
        app.run_with_api()
    except KeyboardInterrupt:
        pass
    finally:
        app.close()
