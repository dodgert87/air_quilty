from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.models.sensor import SensorDataIn, SensorDataOut
from app.models.response import Response
from app.domain.sensor_logic import get_latest_sensor_data, create_sensor_data

router = APIRouter(prefix="/sensor", tags=["Sensor Data"])


@router.get("/latest", response_model=Response.success[list[SensorDataOut]])
async def fetch_latest_sensor_data():
    try:
        data = await get_latest_sensor_data()
        return Response.success(
            message=Response.message.OK,
            http_code=Response.http.OK,
            app_code=Response.code.OK,
            data=data
        )
    except Exception as e:
        return JSONResponse(
            status_code=Response.http.SERVER_ERROR,
            content=Response.error(
                message=Response.message.UNKNOWN_ERROR,
                http_code=Response.http.SERVER_ERROR,
                app_code=Response.code.UNKNOWN_ERROR,
                errors={"error": str(e)}
            ).model_dump()
        )


@router.post("/", response_model=Response.success[SensorDataOut])
async def create_sensor_data_endpoint(data: SensorDataIn):
    try:
        new_entry = await create_sensor_data(data)
        return Response.success(
            message=Response.message.CREATED,
            http_code=Response.http.CREATED,
            app_code=Response.code.CREATED,
            data=new_entry
        )
    except Exception as e:
        return JSONResponse(
            status_code=Response.http.SERVER_ERROR,
            content=Response.error(
                message=Response.message.UNKNOWN_ERROR,
                http_code=Response.http.SERVER_ERROR,
                app_code=Response.code.UNKNOWN_ERROR,
                errors={"error": str(e)}
            ).model_dump()
        )
