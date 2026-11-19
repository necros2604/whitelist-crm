from datetime import UTC, datetime

from fastapi import APIRouter, status

from app.schemas import CallCreate, CallOut

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("", response_model=CallOut, status_code=status.HTTP_201_CREATED)
def create_call(payload: CallCreate) -> CallOut:
    # TODO: проверить компанию и встречу, обновить статус компании
    return CallOut(id=1, created_at=datetime.now(UTC), **payload.model_dump())
