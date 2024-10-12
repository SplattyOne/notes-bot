import logging
import typing
from contextlib import asynccontextmanager

import aiohttp
import orjson
import pydantic

logger = logging.getLogger(__name__)


@asynccontextmanager
async def aiohttp_session_context(*args, **kwargs) -> typing.AsyncGenerator[aiohttp.ClientSession, None]:
    """Context manager for aiohttp session"""
    async with aiohttp.ClientSession(*args, **kwargs) as session:
        yield session


class ClientSession:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    @staticmethod
    def load_json_answer(text_response: str) -> dict:
        try:
            return orjson.loads(text_response)
        except orjson.JSONDecodeError:
            logger.error('Wrong json answer: %s', text_response)
            raise

    @staticmethod
    def convert_answer_to_model(answer: dict, answer_model: pydantic.BaseModel) -> pydantic.BaseModel:
        try:
            return answer_model(**answer)
        except pydantic.ValidationError:
            logger.error('Validation answer error: %s', answer)
            raise

    async def request(self, method: str, url: str, json_data: dict | None, **kwargs) -> dict:
        async with self._session.request(
            method,
            url,
            json=json_data,
            **kwargs
        ) as response:
            text_response = await response.text()
            answer = self.load_json_answer(text_response)
            if kwargs.get('answer_model'):
                return self.convert_answer_to_model(answer, kwargs.get('answer_model'))
            return answer
