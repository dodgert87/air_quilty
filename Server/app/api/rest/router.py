from fastapi import APIRouter
from app.api.rest import sensor

router = APIRouter()
router.include_router(sensor.router)
