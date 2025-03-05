import asyncio
from contextlib import asynccontextmanager
from typing import Any, Callable, Coroutine

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from api import db
from api.v1 import alice


class FastapiFactory:
    def __init__(self, app_name: str, get_notes_service: Callable[[], Coroutine[Any, Any, None]],
                 close_notes_service: Callable[[], Coroutine[Any, Any, None]],
                 worker_service: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self.app = FastAPI(
            title=app_name,
            docs_url='/api/v1/openapi',
            openapi_url='/api/v1/openapi.json',
            default_response_class=ORJSONResponse,
            lifespan=self.lifespan
        )
        self.get_notes_service = get_notes_service
        self.close_notes_service = close_notes_service
        self.worker_service = worker_service
        self.add_app_routes()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        print("Starting FastAPI...")
        notes_service = await self.get_notes_service()
        db.notes_service = notes_service
        loop = asyncio.get_event_loop()
        loop.create_task(self.worker_service())
        yield
        print("Closing FastAPI...")
        await self.close_notes_service(notes_service)

    def add_app_routes(self) -> None:
        self.app.add_api_route('/', self.root_healthcheck)
        self.app.include_router(alice.router, prefix='/api/v1/alice', tags=['alice'])

    @staticmethod
    async def root_healthcheck() -> None:
        return ORJSONResponse({'ok': True})
