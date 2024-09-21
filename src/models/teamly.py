import uuid

from pydantic import BaseModel


class AuthTokens(BaseModel):
    access_token: str = None
    refresh_token: str = None
    access_token_expires_at: int = None
    refresh_token_expires_at: int = None
    slug: str = None


class AuthTokensAnswer(BaseModel):
    access_token: str
    refresh_token: str
    access_token_expires_at: int
    refresh_token_expires_at: int
    accounts: list[dict]

    def to_auth_tokens(self) -> dict:
        return AuthTokens(**self.model_dump(exclude=('accounts',)), slug=self.accounts[0].get('slug'))


class Note(BaseModel):
    id: uuid.UUID
    title: str | None
    status: str | None
    done: bool | None


class NotesAnswer(BaseModel):
    """Notes from teamly"""
    id: uuid.UUID
    title: str
    content: list[dict]

    def to_notes(self, status_field: str, done_field: str) -> list[Note]:
        notes = list(map(lambda x: {
            'id': x.get('article', {}).get('id'),
            **x.get('article', {}).get('properties', {}).get('properties', {})
        }, self.content))
        return list(map(lambda x: Note(
            id=x.get('id'),
            title=x.get('title', {}).get('text'),
            status=x.get(status_field),
            done=x.get(done_field)
        ), notes))
