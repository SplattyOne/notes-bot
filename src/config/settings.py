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
    app: BotAppType = BotAppType.TELEGRAM.value
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


class NotionNoteApp(NoteApp):
    """Notion integration settings, more info:
    https://developers.notion.com/reference/intro"""
    app: NoteAppType = NoteAppType.NOTION.value
    token: str


class TeamlyNoteApp(NoteApp):
    """Teamly integration settings, more info:
    https://academy.teamly.ru/space/5019017b-ad03-4c00-bdc0-0952fc1cac88/article/dfa9a32d-02c8-4f35-95d9-c98ca2e478c0"""
    app: NoteAppType = NoteAppType.TEAMLY.value
    integration_id: str
    integration_url: str
    client_secret: str
    client_auth_code: str


class YonoteNoteApp(NoteApp):
    """Yonote integration settings, more info:
    https://yonote.ru/developers#section/Vvedenie"""
    app: NoteAppType = NoteAppType.YONOTE.value
    token: str
    collection_id: str


class CommonSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env.local', env_file_encoding='utf-8', extra='ignore')

    log_level: str = Field('INFO', alias='LOG_LEVEL')
    tmp_dir: str = Field('tmp', alias='TMP_DIR')

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


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')

    common: CommonSettings = get_common_settings()
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


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
