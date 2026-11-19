from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query

from app.db import Conn, get_conn
from app.errors import NotFound
from app.routers.meetings import load_meeting
from app.rules import ALMATY
from app.schemas import ManagerSchedule

router = APIRouter(prefix="/managers", tags=["managers"])


@router.get("/{manager_id}/schedule", response_model=ManagerSchedule)
def get_schedule(
    manager_id: int,
    day: date = Query(alias="date"),  # день по Алматы
    conn: Conn = Depends(get_conn),
):
    if conn.execute("SELECT 1 FROM managers WHERE id = %s", (manager_id,)).fetchone() is None:
        raise NotFound("manager_not_found", "Менеджер не найден")

    # границы дня по Алматы, в БД сравнение идёт уже в UTC
    day_start = datetime.combine(day, time(0, 0), tzinfo=ALMATY)
    day_end = day_start + timedelta(days=1)

    # отменённые не показываем - в расписании только то, что реально будет
    rows = conn.execute(
        """
        SELECT id FROM meetings
        WHERE manager_id = %s AND status = 'scheduled'
          AND starts_at >= %s AND starts_at < %s
        ORDER BY starts_at
        """,
        (manager_id, day_start, day_end),
    ).fetchall()

    meetings = [load_meeting(conn, row["id"]) for row in rows]
    return {"manager_id": manager_id, "date": day, "meetings": meetings}
