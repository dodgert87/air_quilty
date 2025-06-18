from fastapi import APIRouter
from app.api.webhook import webhook


router = APIRouter()
router.include_router(webhook.router)