from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.schemas.risk import (
    CreateRiskEvaluationRequest,
    OverrideRiskEvaluationRequest,
)
from app.services.responses import error_response, success_response
from app.services.risk_engine import (
    RiskServiceError,
    create_risk_evaluation,
    get_risk_evaluation,
    get_risk_explanation,
    override_risk_evaluation,
)

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


def _translate_error(exc: RiskServiceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=error_response(message=exc.message, code=exc.code),
    )


@router.post("/evaluations")
def post_risk_evaluation(
    payload: CreateRiskEvaluationRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        evaluation_payload = create_risk_evaluation(
            payload,
            acting_user_id=x_mcs_user_id,
        )
    except RiskServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"risk_evaluation": evaluation_payload},
        message="risk evaluation created",
    )


@router.get("/evaluations/{evaluation_id}")
def get_risk_evaluation_by_id(
    evaluation_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        evaluation_payload = get_risk_evaluation(
            evaluation_id,
            acting_user_id=x_mcs_user_id,
        )
    except RiskServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"risk_evaluation": evaluation_payload})


@router.get("/evaluations/{evaluation_id}/explanations")
def get_risk_explanation_by_id(
    evaluation_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        explanation_payload = get_risk_explanation(
            evaluation_id,
            acting_user_id=x_mcs_user_id,
        )
    except RiskServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(explanation_payload)


@router.post("/evaluations/{evaluation_id}/override")
def post_risk_override(
    evaluation_id: str,
    payload: OverrideRiskEvaluationRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        override_payload = override_risk_evaluation(
            evaluation_id,
            payload,
            acting_user_id=x_mcs_user_id,
        )
    except RiskServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"risk_override": override_payload},
        message="risk override recorded",
    )
