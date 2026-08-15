import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.database import get_db

from app.core.dependencies import get_current_user, RoleRequirement
from app.modules.users.model import User


from app.modules.queries.model import ContactQuery
from app.modules.queries.schema import QueryCreate, QueryOut, QueryStatusUpdate
from app.modules.auth.schema import ApiResponse


router = APIRouter(prefix="/queries", tags=["Contact Queries & Messages"])

# Admin access guard
require_admin = RoleRequirement(["Admin"])


@router.post("", response_model=ApiResponse[QueryOut])
async def submit_contact_query(
    payload: QueryCreate,
    db: AsyncSession = Depends(get_db)
):
    """Public endpoint for any user to submit a contact query form."""
    new_query = ContactQuery(
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
        phone=payload.phone.strip(),
        message=payload.message.strip(),
        status="Recent"
    )
    db.add(new_query)
    await db.commit()
    await db.refresh(new_query)

    return ApiResponse(
        success=True,
        message="Thank you! Your query message has been submitted successfully.",
        data=QueryOut.model_validate(new_query)
    )


@router.get("", response_model=ApiResponse[List[QueryOut]], dependencies=[Depends(require_admin)])
async def get_queries(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: Recent, Viewed"),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to fetch list of queries, optionally filtered by status ('Recent' or 'Viewed')."""
    stmt = select(ContactQuery)
    if status_filter:
        normalized_status = status_filter.capitalize()
        if normalized_status in ["Recent", "Viewed"]:
            stmt = stmt.where(ContactQuery.status == normalized_status)

    stmt = stmt.order_by(desc(ContactQuery.created_at))
    res = await db.execute(stmt)
    queries = res.scalars().all()

    return ApiResponse(
        success=True,
        message=f"Fetched {len(queries)} query messages",
        data=[QueryOut.model_validate(q) for q in queries]
    )


@router.get("/my", response_model=ApiResponse[List[QueryOut]])
async def get_my_queries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User endpoint to fetch list of queries submitted by the logged-in user."""
    stmt = select(ContactQuery).where(ContactQuery.email == current_user.email.lower()).order_by(desc(ContactQuery.created_at))
    res = await db.execute(stmt)
    queries = res.scalars().all()

    return ApiResponse(
        success=True,
        message=f"Fetched {len(queries)} user queries",
        data=[QueryOut.model_validate(q) for q in queries]
    )



@router.patch("/{query_id}/status", response_model=ApiResponse[QueryOut], dependencies=[Depends(require_admin)])
async def update_query_status(
    query_id: uuid.UUID,
    payload: QueryStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to toggle status of a query between 'Recent' and 'Viewed'."""
    stmt = select(ContactQuery).where(ContactQuery.id == query_id)
    res = await db.execute(stmt)
    query_obj = res.scalar_one_or_none()

    if not query_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query message not found"
        )

    query_obj.status = payload.status
    await db.commit()
    await db.refresh(query_obj)

    return ApiResponse(
        success=True,
        message=f"Query marked as {query_obj.status}",
        data=QueryOut.model_validate(query_obj)
    )
