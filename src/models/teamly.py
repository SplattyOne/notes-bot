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
