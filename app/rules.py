from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.errors import BusinessRuleError

ALMATY = ZoneInfo("Asia/Almaty")
MEETING_DURATION = timedelta(minutes=60)
WORK_START_HOUR = 9
WORK_END_HOUR = 18


def is_working_time(starts_at: datetime) -> bool:
    # переводим в Алматы, потому что рабочие часы считаются по местному времени
    start = starts_at.astimezone(ALMATY)
    end = start + MEETING_DURATION

    if start.weekday() >= 5:  # 5 - суббота, 6 - воскресенье
        return False

    day_start = start.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
    day_end = start.replace(hour=WORK_END_HOUR, minute=0, second=0, microsecond=0)
    # встреча должна уместиться целиком: 17:00-18:00 можно, 17:30-18:30 нельзя
    return day_start <= start and end <= day_end


def check_working_time(starts_at: datetime) -> None:
    if not is_working_time(starts_at):
        raise BusinessRuleError(
            "outside_working_hours",
            "Встреча должна быть в пн-пт с 09:00 до 18:00 по Алматы и целиком умещаться в это время",
        )
