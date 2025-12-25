import os
import shutil
from enum import Enum
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    YamlConfigSettingsSource,
    SettingsConfigDict,
    PydanticBaseSettingsSource
)


CWD = os.getcwd()
CONFIG_FILE_NAME = 'config.yaml'
CONFIG_FILE_EXAMPLE_NAME = 'config.example.yaml'


class EnumWithList(Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class NoteAppType(EnumWithList):
    NOTION = 'NOTION'
    TEAMLY = 'TEAMLY'
    YONOTE = 'YONOTE'


class BotAppType(EnumWithList):
    TELEGRAM = 'TELEGRAM'


class BotApp(BaseModel):
    app: BotAppType


class TelegramBotApp(BotApp):
    """Telegram integration settings, more info:
    https://core.telegram.org/bots/api#authorizing-your-bot"""
    app: BotAppType = BotAppType.TELEGRAM
    token: str
    allowed_users: list[str]


class NoteApp(BaseModel):
    app: NoteAppType
    database_id: str
    status_field_id: str
    status_field_value: str
    done_field_id: str
    start_words: list[str] = []
    delete_done_notes: bool = False
    knowledge_database_id: str = ''


class NotionNoteApp(NoteApp):
    """Notion integration settings, more info:
    https://developers.notion.com/reference/intro"""
    app: NoteAppType = NoteAppType.NOTION
    token: str


class TeamlyNoteApp(NoteApp):
    """Teamly integration settings, more info:
    https://academy.teamly.ru/space/5019017b-ad03-4c00-bdc0-0952fc1cac88/article/dfa9a32d-02c8-4f35-95d9-c98ca2e478c0"""
    app: NoteAppType = NoteAppType.TEAMLY
    integration_id: str
    integration_url: str
    client_secret: str
    client_auth_code: str


class YonoteNoteApp(NoteApp):
    """Yonote integration settings, more info:
    https://yonote.ru/developers#section/Vvedenie"""
    app: NoteAppType = NoteAppType.YONOTE
    token: str
    collection_id: str


class CommonSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env.local', env_file_encoding='utf-8', extra='ignore')

    log_level: str = Field('INFO', alias='LOG_LEVEL')
    tmp_dir: str = Field('tmp', alias='TMP_DIR')

    api_host: str = Field('0.0.0.0', alias='API_HOST')
    api_port: str = Field('8888', alias='API_PORT')
    api_name: str = Field('Notes bot', alias='API_NAME')

    etl_knowledge_interval_seconds: int = Field(default=300, alias="ETL_KNOWLEDGE_INTERVAL_SECONDS")
    delete_done_notes_interval_seconds: int = Field(default=300, alias="DELETE_DONE_NOTES_INTERVAL_SECONDS")

    @field_validator('tmp_dir', mode='after')
    @classmethod
    def transform_to_abs_path(cls, path: str) -> str:
        if not isinstance(path, str):
            raise TypeError('Error: Path must be str.')
        if os.path.isabs(path):
            return path
        return os.path.join(CWD, path)

    @property
    def config_path(self) -> str:
        return os.path.join(self.tmp_dir, CONFIG_FILE_NAME)


@lru_cache
def get_common_settings() -> CommonSettings:
    common_settings = CommonSettings()
    if not os.path.exists(common_settings.config_path):
        shutil.copy2(CONFIG_FILE_EXAMPLE_NAME, common_settings.config_path)
    return common_settings


class AliceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env.local', env_file_encoding='utf-8', extra='ignore')

    user_id: str = Field(None, alias='ALICE_USER_ID')


@lru_cache
def get_alice_settings() -> AliceSettings:
    return AliceSettings()


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env.local', env_file_encoding='utf-8', extra='ignore')

    url: str = Field('http://localhost:6333', alias='QDRANT_URL')
    collection: str = Field('notion_pages', alias='QDRANT_COLLECTION')
    max_context_chunks: int = Field(default=6, alias="MAX_CONTEXT_CHUNKS")


@lru_cache
def get_qdrant_settings() -> QdrantSettings:
    return QdrantSettings()


class OpenaiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env.local', env_file_encoding='utf-8', extra='ignore')

    api_key: str = Field(alias="OPENAI_API_KEY")
    main_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    embed_model: str = Field(default="text-embedding-3-large", alias="OPENAI_EMBED_MODEL")
    image_model: str = Field(default="gpt-image-1", alias="OPENAI_IMAGE_MODEL")

    chunk_size: int = Field(default=1200, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    temperature: float = Field(default=0.2, alias="TEMPERATURE")
    max_concurrent_requests: int = Field(default=3, alias="MAX_CONCURRENT_REQUESTS")


@lru_cache
def get_openai_settings() -> OpenaiSettings:
    return OpenaiSettings()


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env.local', env_file_encoding='utf-8', extra='ignore')

    common: CommonSettings = get_common_settings()
    alice: AliceSettings = get_alice_settings()
    qdrant: QdrantSettings = get_qdrant_settings()
    openai: OpenaiSettings = get_openai_settings()

    transmit_from: TelegramBotApp = Field(alias='transmit_from')
    transmit_to: list[
        NotionNoteApp | TeamlyNoteApp | YonoteNoteApp] = Field(alias='transmit_to')

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        **kwargs
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        config_path = get_common_settings().config_path
        return (YamlConfigSettingsSource(settings_cls, yaml_file=config_path, yaml_file_encoding='utf-8'),)

    def get_first_notion_client_config(self) -> NotionNoteApp | None:
        return next((x for x in self.transmit_to if x.app == NoteAppType.NOTION), None)


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
