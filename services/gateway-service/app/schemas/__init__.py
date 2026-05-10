"""Gateway service schemas package."""
from app.schemas.assessments import CreateAssessmentSessionRequest, SubmitAssessmentAnswerRequest
from app.schemas.consultations import ConsultationTurnRequest, CreateConsultationRequest

__all__ = [
    "ConsultationTurnRequest",
    "CreateAssessmentSessionRequest",
    "CreateConsultationRequest",
    "SubmitAssessmentAnswerRequest",
]
