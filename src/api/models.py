from pydantic import BaseModel


class AliceMessage(BaseModel):
    """Base model Alice message."""
    session: dict | None
    request: dict | None
    version: str | None

    @property
    def user_id(self):
        if not self.session:
            return None
        return self.session.get('user', {}).get('user_id')

    @property
    def message(self):
        if not self.request:
            return None
        return self.request.get('original_utterance')
