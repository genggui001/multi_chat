from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, Response

router = APIRouter()

SESSION_KEY = "session_id"


def get_session_id(response: Response, session_id: Optional[UUID] = Cookie(None)) -> UUID:
    if session_id is None:
        session_id = uuid4()
        response.set_cookie(
            SESSION_KEY, str(session_id), httponly=True, samesite="none"
        )
    return session_id


@router.get("/restart")
def restart(response: Response) -> Response:
    response.set_cookie(SESSION_KEY, str(uuid4()), httponly=True)
    response.status_code = 200
    return response
