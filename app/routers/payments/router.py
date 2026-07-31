from fastapi import APIRouter
from app.routers.payments import orders, webhook

router = APIRouter()
router.include_router(orders.router)
router.include_router(webhook.router)
