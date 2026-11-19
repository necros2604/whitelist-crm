from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status

from app.db import Conn, get_conn
from app.errors import NotFound
from app.rules import MEETING_DURATION, check_working_time
from app.schemas import MeetingCreate, MeetingEvent, MeetingOut, MeetingStatus, MeetingUpdate

router = APIRouter(prefix="/meetings", tags=["meetings"])


def load_meeting(conn: Conn, meeting_id: int) -> dict:
    meeting = conn.execute("SELECT * FROM meetings WHERE id = %s", (meeting_id,)).fetchone()
    if meeting is None:
        raise NotFound("meeting_not_found", "Встреча не найдена")

    history = conn.execute(
        "SELECT kind, starts_at, created_at AS at FROM meeting_events WHERE meeting_id = %s ORDER BY id",
        (meeting_id,),
    ).fetchall()
    # первое событие всегда created - в нём изначальное время
    return {**meeting, "original_starts_at": history[0]["starts_at"], "history": history}


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: MeetingCreate, conn: Conn = Depends(get_conn)):
    check_working_time(payload.starts_at)

    if conn.execute("SELECT 1 FROM managers WHERE id = %s", (payload.manager_id,)).fetchone() is None:
        raise NotFound("manager_not_found", "Менеджер не найден")
    if conn.execute("SELECT 1 FROM companies WHERE id = %s", (payload.company_id,)).fetchone() is None:
        raise NotFound("company_not_found", "Компания не найдена")

    starts_at = payload.starts_at.astimezone(UTC)
    # пересечения у менеджера и вторую активную встречу у компании не пустят ограничения в БД -> 409
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
def update_meeting(meeting_id: int, payload: MeetingUpdate) -> MeetingOut:
    # TODO: БД, проверки как при создании, история
    now = datetime.now(UTC)
    original = now.replace(minute=0, second=0, microsecond=0)
    starts = payload.starts_at.astimezone(UTC) if payload.starts_at else original
    history = [MeetingEvent(kind="created", starts_at=original, at=now)]
    if payload.starts_at:
        history.append(MeetingEvent(kind="rescheduled", starts_at=starts, at=now))
    else:
        history.append(MeetingEvent(kind="cancelled", starts_at=None, at=now))
    return MeetingOut(
        id=meeting_id,
        manager_id=1,
        company_id=1,
        starts_at=starts,
        ends_at=starts + MEETING_DURATION,
        status=payload.status or MeetingStatus.scheduled,
        created_at=now,
        original_starts_at=original,
        history=history,
    )
