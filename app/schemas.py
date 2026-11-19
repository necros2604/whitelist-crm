from datetime import date, datetime
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import AwareDatetime, BaseModel, Field, model_validator

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    error: str = Field(examples=["manager_busy"])
    message: str = Field(examples=["У менеджера уже есть встреча в это время"])


# статус компании = результат последнего звонка
class CompanyStatus(StrEnum):
    new = "new"
    no_answer = "no_answer"
    refused = "refused"
    meeting_set = "meeting_set"


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    bin: str = Field(pattern=r"^\d{12}$", description="БИН, 12 цифр")
    phone: str = Field(min_length=5, max_length=32)


class CompanyOut(CompanyCreate):
    id: int
    status: CompanyStatus
    created_at: datetime


class CallResult(StrEnum):
    no_answer = "no_answer"
    refused = "refused"
    meeting_set = "meeting_set"


class CallCreate(BaseModel):
    company_id: int
    result: CallResult
    meeting_id: int | None = None
    comment: str | None = None

    @model_validator(mode="after")
    def check_meeting_id(self):
        # есть ли такая встреча в БД - проверим в сервисе
        if self.result == CallResult.meeting_set and self.meeting_id is None:
            raise ValueError("meeting_id обязателен при result=meeting_set")
        if self.result != CallResult.meeting_set and self.meeting_id is not None:
            raise ValueError("meeting_id допустим только при result=meeting_set")
        return self


class CallOut(CallCreate):
    id: int
    created_at: datetime


class MeetingStatus(StrEnum):
    scheduled = "scheduled"
    cancelled = "cancelled"


class MeetingCreate(BaseModel):
    manager_id: int
    company_id: int
    # только с таймзоной, иначе непонятно UTC это или Алматы
    starts_at: AwareDatetime = Field(examples=["2026-11-19T05:00:00Z"])


# либо перенос (starts_at), либо отмена (status=cancelled)
class MeetingUpdate(BaseModel):
    starts_at: AwareDatetime | None = None
    status: MeetingStatus | None = None

    @model_validator(mode="after")
    def check_one_action(self):
        if (self.starts_at is None) == (self.status is None):
            raise ValueError("Передайте либо starts_at (перенос), либо status=cancelled (отмена)")
        if self.status == MeetingStatus.scheduled:
            raise ValueError("Через status можно только отменить встречу: status=cancelled")
        return self


class MeetingEvent(BaseModel):
    kind: str = Field(examples=["created", "rescheduled", "cancelled"])
    starts_at: datetime | None
    at: datetime


class MeetingOut(BaseModel):
    id: int
    manager_id: int
    company_id: int
    starts_at: datetime
    ends_at: datetime
    status: MeetingStatus
    created_at: datetime
    original_starts_at: datetime
    history: list[MeetingEvent]


class ManagerSchedule(BaseModel):
    manager_id: int
    date: date  # день по Алматы
    meetings: list[MeetingOut]
