from datetime import datetime

import pytest

from app.rules import is_working_time


# 2026-11-20 - пятница, 2026-11-21 - суббота. Алматы = UTC+5
@pytest.mark.parametrize(
    "starts_at, expected",
    [
        ("2026-11-20T09:00:00+05:00", True),   # начало рабочего дня
        ("2026-11-20T08:59:00+05:00", False),  # на минуту раньше
        ("2026-11-20T17:00:00+05:00", True),   # заканчивается ровно в 18:00
        ("2026-11-20T17:01:00+05:00", False),  # заканчивается в 18:01
        ("2026-11-20T17:30:00+05:00", False),  # пример из задания
        ("2026-11-20T12:00:00Z", True),        # 17:00 по Алматы
        ("2026-11-20T12:30:00Z", False),       # 17:30 по Алматы
        ("2026-11-21T10:00:00+05:00", False),  # суббота
    ],
)
def test_working_hours_boundaries(starts_at, expected):
    assert is_working_time(datetime.fromisoformat(starts_at)) is expected
