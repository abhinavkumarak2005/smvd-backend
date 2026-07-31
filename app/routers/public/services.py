from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas.service import ServiceResponse
from app.repositories.service_repo import ServiceRepo, get_service_repo

router = APIRouter(tags=["Services"])


@router.get("/services", response_model=list[ServiceResponse])
async def list_services(
    repo: ServiceRepo = Depends(get_service_repo),
):
    """List all active services. No auth required."""
    return await repo.get_all_services(active_only=True)


@router.get("/services/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: UUID,
    repo: ServiceRepo = Depends(get_service_repo),
):
    """Get a single service by ID. No auth required."""
    service = await repo.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service
