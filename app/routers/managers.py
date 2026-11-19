from datetime import date

from fastapi import APIRouter, Query

from app.schemas import ManagerSchedule

router = APIRouter(prefix="/managers", tags=["managers"])


@router.get("/{manager_id}/schedule", response_model=ManagerSchedule)
def get_schedule(
    manager_id: int,
    day: date = Query(alias="date"),  # день по Алматы
) -> ManagerSchedule:
    # TODO: встречи за день из БД
    return ManagerSchedule(manager_id=manager_id, date=day, meetings=[])
