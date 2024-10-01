import uuid

from pydantic import BaseModel


class Note(BaseModel):
    id: uuid.UUID
    title: str | None
    status: str | None
    done: bool | None
