import logging

import aiohttp
import orjson

logger = logging.getLogger(__name__)


class ClientSession:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def request(self, method: str, url: str, json_data: dict | None, **kwargs) -> dict:
        async with self._session.request(
            method,
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
