import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.model import User
from app.modules.auth.schema import ApiResponse
from app.core.exceptions import NotFoundException, ValidationException

from app.modules.templates.schema import (
    GenerateReportRequest,
    ReportFeedbackSubmit,
    ReportQualityResponse,
    ReportExplanationResponse,
    ReportVersionResponse,
    ReportAuditResponse
)
from app.modules.templates.services.report_intelligence_coordinator import report_intelligence_coordinator
from app.modules.templates.services.feedback_service import feedback_service

logger = logging.getLogger(__name__)

report_router = APIRouter(prefix="/api/reports", tags=["Report Intelligence"])


@report_router.post("/generate", response_model=ApiResponse[ReportVersionResponse])
@report_router.post("/generate/", response_model=ApiResponse[ReportVersionResponse])
async def generate_report(
    payload: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    """Triggers the safety narrative report generation and deterministic computations pipeline."""
    try:
        report = await report_intelligence_coordinator.generate_assisted_report(
            db=db,
            dataset_id=payload.dataset_id,
            generated_by=payload.generated_by
        )
        return ApiResponse(
            success=True,
            message="Report narrative and quality validation generated successfully",
            data=ReportVersionResponse.model_validate(report)
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as ex:
        logger.error(f"Failed to generate report: {ex}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@report_router.get("/{id}", response_model=ApiResponse[ReportVersionResponse])
@report_router.get("/{id}/", response_model=ApiResponse[ReportVersionResponse])
async def get_report_details(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    """Fetches details of a generated report version by ID."""
    try:
        report = await report_intelligence_coordinator.get_report(db, id)
        return ApiResponse(
            success=True,
            message="Fetched report details successfully",
            data=ReportVersionResponse.model_validate(report)
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@report_router.post("/{id}/approve", response_model=ApiResponse[dict])
@report_router.post("/{id}/approve/", response_model=ApiResponse[dict])
async def approve_report_version(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Promotes safety report version status to Approved."""
    try:
        await feedback_service.approve_report(
            db=db,
            report_id=id,
            performed_by=current_user.email
        )
        return ApiResponse(
            success=True,
            message="Report approved and logged in audit history",
            data={}
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@report_router.post("/{id}/feedback", response_model=ApiResponse[dict])
@report_router.post("/{id}/feedback/", response_model=ApiResponse[dict])
async def submit_reviewer_feedback(
    id: uuid.UUID,
    payload: ReportFeedbackSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submits manual narrative corrections, logs edits audits, and triggers stylistic continuous learning."""
    try:
        await feedback_service.submit_report_feedback(
            db=db,
            report_id=id,
            performed_by=current_user.email,
            rating=payload.rating,
            comments=payload.comments,
            narrative_corrections=payload.narrative_corrections
        )
        return ApiResponse(
            success=True,
            message="Reviewer corrections applied and style learned",
            data={}
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@report_router.get("/{id}/quality", response_model=ApiResponse[ReportQualityResponse])
@report_router.get("/{id}/quality/", response_model=ApiResponse[ReportQualityResponse])
async def get_report_quality_score(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    """Retrieves completeness, formatting, consistency quality score and recommendations."""
    try:
        gen = await report_intelligence_coordinator.get_report_generation(db, id)
        suggestions = gen.quality_suggestions or {}
        return ApiResponse(
            success=True,
            message="Fetched report quality metrics successfully",
            data=ReportQualityResponse(
                overall_score=gen.quality_score,
                completeness_score=suggestions.get("completeness_score", 0.0),
                consistency_score=suggestions.get("consistency_score", 0.0),
                formatting_score=suggestions.get("formatting_score", 0.0),
                suggestions=suggestions.get("suggestions", [])
            )
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@report_router.get("/{id}/explanation", response_model=ApiResponse[ReportExplanationResponse])
@report_router.get("/{id}/explanation/", response_model=ApiResponse[ReportExplanationResponse])
async def get_report_explanations(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    """Retrieves explainability details and reasons for AI generation parameters."""
    try:
        gen = await report_intelligence_coordinator.get_report_generation(db, id)
        explanations = gen.explanations or {}
        return ApiResponse(
            success=True,
            message="Fetched AI decision explanations successfully",
            data=ReportExplanationResponse(
                decisions=explanations.get("decisions", []),
                overall_explanation=explanations.get("overall_explanation", "")
            )
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@report_router.get("/{id}/audit-trail", response_model=ApiResponse[List[ReportAuditResponse]])
@report_router.get("/{id}/audit-trail/", response_model=ApiResponse[List[ReportAuditResponse]])
async def get_report_audit_trail(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    """Retrieves full changelogs of updates performed on this report version."""
    try:
        trail = await feedback_service.get_audit_trail(db, id)
        return ApiResponse(
            success=True,
            message="Fetched report audit trail log successfully",
            data=[ReportAuditResponse.model_validate(t) for t in trail]
        )
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))
