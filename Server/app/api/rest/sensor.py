from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import JSONResponse

from app.services.sensor_service import get_latest_sensor_data, insert_sensor_data
from app.models.sensor import SensorDataOut, SensorDataIn
from app.infrastructure.database.dependencies import get_db
from app.models.response import Response

router = APIRouter(prefix="/sensor", tags=["Sensor Data"])


@router.get("/latest", response_model=Response.success[list[SensorDataOut]])
async def fetch_latest_sensor_data(db: AsyncSession = Depends(get_db)):
    try:
        data = await get_latest_sensor_data(db) # type: ignore
        return Response.success(
            message=Response.message.OK,
            http_code=Response.http.OK,
            app_code=Response.code.OK,
            data=data
        )
    except SQLAlchemyError as e:
        return JSONResponse(
            status_code=Response.http.SERVER_ERROR,
            content=Response.error(
                message=Response.message.DB_ERROR,
                http_code=Response.http.SERVER_ERROR,
                app_code=Response.code.DB_ERROR,
                errors={"db": str(e)}
            ).model_dump()
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
async def create_sensor_data(data: SensorDataIn, db: AsyncSession = Depends(get_db)):
    try:
        new_entry = await insert_sensor_data(db, data)
        return Response.success(
            message=Response.message.CREATED,
            http_code=Response.http.CREATED,
            app_code=Response.code.CREATED,
            data=new_entry
        )
    except SQLAlchemyError as e:
        return JSONResponse(
            status_code=Response.http.SERVER_ERROR,
            content=Response.error(
                message=Response.message.DB_ERROR,
                http_code=Response.http.SERVER_ERROR,
                app_code=Response.code.DB_ERROR,
                errors={"db": str(e)}
            ).model_dump()
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
