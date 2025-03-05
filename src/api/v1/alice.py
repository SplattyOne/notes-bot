import logging

from fastapi import APIRouter, Depends, status, Request
import pydantic

from api.models import AliceMessage
from api.db import get_notes_service, NotesServiceProtocol
from config.settings import get_alice_settings


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/message/',
             status_code=status.HTTP_201_CREATED,
             summary="Insert message from Alice.",
             )
async def get_alice_message(request: Request,
                            notes_service: NotesServiceProtocol = Depends(get_notes_service)) -> dict:
    try:
        req_data = AliceMessage(**await request.json())
    except pydantic.ValidationError as e:
        logger.error(f'Parsing error: {e}')
        return {'response': {'text': 'Ошибка сценария'}}
    response = {
        'session': req_data.session,
        'version': req_data.version,
        'response': {'end_session': False}
    }
    if req_data.user_id != get_alice_settings().user_id:
        logger.error(f'Unknown user: {req_data.user_id}')
        return {'response': {'text': 'Ошибка сценария'}}
    if req_data.message:
        logger.info(f'Got message from alice: {req_data.message}')
        await notes_service.create_note(req_data.message)
        response['response']['text'] = 'Заметка сохранена'
        response['response']['end_session'] = True
    else:
        response['response']['text'] = 'Привет! Диктуй заметку'
    return response
