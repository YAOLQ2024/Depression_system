from __future__ import annotations

from fastapi import APIRouter

from app.services.catalog_loader import load_doctor_personas, load_workflow_summary
from app.services.responses import success_response

router = APIRouter(prefix="/api/v1", tags=["catalog"])


@router.get("/catalog/doctor-personas")
def doctor_personas():
    return success_response({"items": load_doctor_personas()})


@router.get("/catalog/workflow-summary")
def workflow_summary():
    return success_response({"workflow": load_workflow_summary()})


@router.get("/system/bootstrap")
def system_bootstrap():
    return success_response(
        {
            "doctor_personas": load_doctor_personas(),
            "workflow": load_workflow_summary(),
        }
    )
