from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.services import eeg_explanation_service as service
from app.services.responses import error_response, success_response

router = APIRouter(prefix='/api/v1/multimodal/sessions/{session_id}/eeg', tags=['eeg'])


class ExplanationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    inference_id: UUID
    target_class: Literal[0, 1, 2]


def invoke(function, session_id, user_id, **kwargs):
    if not user_id:
        raise HTTPException(401, detail=error_response(message='missing acting user id', code=4013))
    try:
        return function(session_id, user_id, **kwargs)
    except service.EegExplanationError as exc:
        raise HTTPException(exc.status_code, detail=error_response(message=exc.message, code=exc.code)) from exc


@router.get('/windows')
def windows(session_id: str, x_mcs_user_id: str | None = Header(default=None),
            cursor: str | None = Query(default=None, max_length=1024), limit: int = Query(default=20, ge=1, le=100)):
    return success_response(invoke(service.list_windows, session_id, x_mcs_user_id, cursor=cursor, limit=limit))


@router.post('/explanations')
def request_explanation(session_id: str, payload: ExplanationRequest, x_mcs_user_id: str | None = Header(default=None)):
    result = invoke(service.request_explanation, session_id, x_mcs_user_id,
                    inference_id=str(payload.inference_id), target_class=payload.target_class)
    return JSONResponse(success_response(result), status_code=202 if result['status'] in {'queued', 'running'} else 200)


@router.get('/explanations')
def explanation_history(session_id: str, target_class: int = Query(default=2, ge=0, le=2),
                        x_mcs_user_id: str | None = Header(default=None),
                        cursor: str | None = Query(default=None, max_length=1024), limit: int = Query(default=20, ge=1, le=100)):
    return success_response(invoke(service.list_explanations, session_id, x_mcs_user_id,
                                  target_class=target_class, cursor=cursor, limit=limit))


@router.get('/explanations/{explanation_id}')
def explanation_detail(session_id: str, explanation_id: str, x_mcs_user_id: str | None = Header(default=None)):
    return success_response(invoke(service.get_explanation, session_id, x_mcs_user_id, explanation_id=explanation_id))
