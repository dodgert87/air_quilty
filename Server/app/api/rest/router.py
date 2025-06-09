from fastapi import APIRouter
from app.api.rest import sensor_metadata
from app.api.rest import auth

router = APIRouter()
router.include_router(sensor_metadata.router)
router.include_router(auth.router)

