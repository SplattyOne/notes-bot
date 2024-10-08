from pydantic import BaseModel

import models.notes as notes_models


class Note(notes_models.Note):
    pass


class NotesAnswer(BaseModel):
    """Notes from yonote"""
    pagination: dict
    data: list[dict]
    propsPolicies: list[dict]
    policies: list[dict]
    count: int
    status: int
    ok: bool

    def to_notes(self, status_field: str, done_field: str) -> list[Note]:
        notes = list(map(lambda x: {
            'id': x.get('id'),
            'title': x.get('title'),
            **x.get('properties', {})
        }, self.data))
        return list(map(lambda x: Note(
            id=x.get('id'),
            title=x.get('title'),
            status=x.get(status_field)[0] if x.get(status_field) else None,
            done=x.get(done_field) == '1'
        ), notes))
