from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, status

from app.schemas import MeetingCreate, MeetingEvent, MeetingOut, MeetingStatus, MeetingUpdate

router = APIRouter(prefix="/meetings", tags=["meetings"])

MEETING_DURATION = timedelta(minutes=60)


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: MeetingCreate) -> MeetingOut:
    # TODO: рабочие часы, пересечения, БД
    now = datetime.now(UTC)
    starts = payload.starts_at.astimezone(UTC)
    return MeetingOut(
        id=1,
        manager_id=payload.manager_id,
        company_id=payload.company_id,
        starts_at=starts,
        ends_at=starts + MEETING_DURATION,
        status=MeetingStatus.scheduled,
        created_at=now,
        original_starts_at=starts,
        history=[MeetingEvent(kind="created", starts_at=starts, at=now)],
    )


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
