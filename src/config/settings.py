from functools import lru_cache

import pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramSettings(BaseSettings):
    """Telegram integration settings, more info:
    https://core.telegram.org/bots/api#authorizing-your-bot"""
    model_config = SettingsConfigDict(
        env_file='.env.local', env_file_encoding='utf-8', extra='ignore')
    token: str = pydantic.Field(None, alias='TELEGRAM_TOKEN')
    allowed_users: list = pydantic.Field(None, alias='TELEGRAM_ALLOWED_USERS')


class TeamlySettings(BaseSettings):
    """Teamly integration settings, more info:
    https://academy.teamly.ru/space/5019017b-ad03-4c00-bdc0-0952fc1cac88/article/dfa9a32d-02c8-4f35-95d9-c98ca2e478c0"""
    model_config = SettingsConfigDict(
        env_file='.env.local', env_file_encoding='utf-8', extra='ignore')
    integration_id: str = pydantic.Field(None, alias='TEAMLY_INTEGRATION_ID')
    integration_url: str = pydantic.Field(None, alias='TEAMLY_INTEGRATION_URL')
    client_secret: str = pydantic.Field(None, alias='TEAMLY_CLIENT_SECRET')
    client_auth_code: str = pydantic.Field(None, alias='TEAMLY_AUTH_CODE')
    # ID of database and status field for adding new rows
    database_id: str = pydantic.Field(None, alias='TEAMLY_DATABASE_ID')
    status_field_id: str = pydantic.Field(None, alias='TEAMLY_STATUS_FIELD_ID')
    status_field_value: str = pydantic.Field(None, alias='TEAMLY_STATUS_FIELD_VALUE')


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env.local', env_file_encoding='utf-8', extra='ignore')
    telegram: TelegramSettings = TelegramSettings()
    teamly: TeamlySettings = TeamlySettings()

    log_level: str = pydantic.Field('INFO', alias='LOG_LEVEL')
    tmp_dir: str = pydantic.Field('tmp', alias='TMP_DIR')


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
