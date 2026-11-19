from datetime import UTC

from fastapi import APIRouter, Depends, status

from app.db import Conn, get_conn
from app.errors import Conflict, NotFound
from app.rules import MEETING_DURATION, check_working_time
from app.schemas import MeetingCreate, MeetingOut, MeetingStatus, MeetingUpdate

router = APIRouter(prefix="/meetings", tags=["meetings"])


def load_meeting(conn: Conn, meeting_id: int) -> dict:
    meeting = conn.execute("SELECT * FROM meetings WHERE id = %s", (meeting_id,)).fetchone()
    if meeting is None:
        raise NotFound("meeting_not_found", "Встреча не найдена")

    history = conn.execute(
        "SELECT kind, starts_at, created_at AS at FROM meeting_events WHERE meeting_id = %s ORDER BY id",
        (meeting_id,),
    ).fetchall()
    # первое событие всегда created, нём изначальное время
    return {**meeting, "original_starts_at": history[0]["starts_at"], "history": history}


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: MeetingCreate, conn: Conn = Depends(get_conn)):
    check_working_time(payload.starts_at)

    if conn.execute("SELECT 1 FROM managers WHERE id = %s", (payload.manager_id,)).fetchone() is None:
        raise NotFound("manager_not_found", "Менеджер не найден")
    if conn.execute("SELECT 1 FROM companies WHERE id = %s", (payload.company_id,)).fetchone() is None:
        raise NotFound("company_not_found", "Компания не найдена")

    starts_at = payload.starts_at.astimezone(UTC)
    # пересечения у менеджера и вторую активную встречу у компании не пустят ограничения в БД (409)
    meeting = conn.execute(
        """
        INSERT INTO meetings (manager_id, company_id, starts_at, ends_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (payload.manager_id, payload.company_id, starts_at, starts_at + MEETING_DURATION),
    ).fetchone()
    conn.execute(
        "INSERT INTO meeting_events (meeting_id, kind, starts_at) VALUES (%s, 'created', %s)",
        (meeting["id"], starts_at),
    )
    return load_meeting(conn, meeting["id"])


@router.patch("/{meeting_id}", response_model=MeetingOut)
def update_meeting(meeting_id: int, payload: MeetingUpdate, conn: Conn = Depends(get_conn)):
    # FOR UPDATE - блокируем строку, чтобы параллельный перенос/отмена ждали нас
    meeting = conn.execute("SELECT * FROM meetings WHERE id = %s FOR UPDATE", (meeting_id,)).fetchone()
    if meeting is None:
        raise NotFound("meeting_not_found", "Встреча не найдена")
    if meeting["status"] == MeetingStatus.cancelled:
        raise Conflict("meeting_cancelled", "Встреча уже отменена, её нельзя изменить")

    if payload.status == MeetingStatus.cancelled:
        conn.execute("UPDATE meetings SET status = 'cancelled' WHERE id = %s", (meeting_id,))
        conn.execute(
            "INSERT INTO meeting_events (meeting_id, kind, starts_at) VALUES (%s, 'cancelled', %s)",
            (meeting_id, meeting["starts_at"]),
        )
    else:
        check_working_time(payload.starts_at)
        starts_at = payload.starts_at.astimezone(UTC)
        # старую запись не трогаем, только обновляем время и пишем событие в историю
        conn.execute(
            "UPDATE meetings SET starts_at = %s, ends_at = %s WHERE id = %s",
            (starts_at, starts_at + MEETING_DURATION, meeting_id),
        )
        conn.execute(
            "INSERT INTO meeting_events (meeting_id, kind, starts_at) VALUES (%s, 'rescheduled', %s)",
            (meeting_id, starts_at),
        )

    return load_meeting(conn, meeting_id)
