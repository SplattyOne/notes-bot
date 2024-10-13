import uuid

from pydantic import BaseModel

import models.notes as notes_models


class Note(notes_models.Note):
    pass


class NotesAnswer(BaseModel):
    """Notes from notion"""
    object: str
    results: list[dict]
    request_id: uuid.UUID
    type: str

    def to_notes(self) -> list[Note]:
        notes = list(map(lambda x: {
            'id': x.get('id'),
            **x.get('properties', {})
        }, self.results))
        return list(map(lambda x: Note(
            id=x.get('id'),
            title=x.get('Name', {}).get('title', [{}])[0].get('plain_text'),
            status=x.get('Status', {}).get('status', {}).get('id'),
            done=x.get('Done', {}).get('checkbox', False)
        ), notes))
