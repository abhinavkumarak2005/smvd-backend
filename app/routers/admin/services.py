from datetime import date
from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.models.schemas.service import ServiceCreateRequest, ServiceUpdateRequest, ServiceResponse
from app.repositories import service_repo
from app.services import audit_service

router = APIRouter(tags=["Admin - Services"])

@router.get("/admin/services", response_model=list[ServiceResponse])
async def list_all_services(
    repo: service_repo.ServiceRepo = Depends(service_repo.get_service_repo),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """List all services, including inactive ones."""
    return await repo.get_all_services(active_only=False)

@router.get("/admin/services/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: UUID,
    repo: service_repo.ServiceRepo = Depends(service_repo.get_service_repo),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Get service details."""
    service = await repo.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@router.post("/admin/services", response_model=ServiceResponse, status_code=201)
async def create_service(
    body: ServiceCreateRequest,
    repo: service_repo.ServiceRepo = Depends(service_repo.get_service_repo),
    current_user: CurrentUser = Depends(require_role("super_admin")),
):
    """Create a new service. Requires super_admin."""
    service = await repo.create_service(body.model_dump())
    await audit_service.write_log("service.created", service_id=str(service["id"]), admin_id=str(current_user.id))
    return service

@router.put("/admin/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    body: ServiceUpdateRequest,
    repo: service_repo.ServiceRepo = Depends(service_repo.get_service_repo),
    current_user: CurrentUser = Depends(require_role("super_admin")),
):
    """Update an existing service. Requires super_admin."""
    service = await repo.update_service(service_id, body.model_dump())
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    await audit_service.write_log("service.updated", service_id=str(service_id), admin_id=str(current_user.id))
    return service

@router.patch("/admin/services/{service_id}/toggle")
async def toggle_service(
    service_id: UUID,
    repo: service_repo.ServiceRepo = Depends(service_repo.get_service_repo),
    current_user: CurrentUser = Depends(require_role("super_admin")),
):
    """Toggle a service active/inactive. Requires super_admin."""
    service = await repo.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
        
    new_status = not service["is_active"]
    await repo.toggle_active(service_id, new_status)
    await audit_service.write_log("service.toggled", service_id=str(service_id), is_active=new_status, admin_id=str(current_user.id))
    return {"message": f"Service is now {'active' if new_status else 'inactive'}"}
