from fastapi import APIRouter
from app.api.rest import sensor
from app.api.rest import auth

router = APIRouter()
router.include_router(sensor.router)
router.include_router(auth.router)

