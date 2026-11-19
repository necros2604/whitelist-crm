from tests.test_meetings import AIGUL_ID, ERLAN_ID, cancel_meeting, create_company, create_meeting

FRIDAY = "2026-11-20"
FRIDAY_10_00 = "2026-11-20T10:00:00+05:00"
FRIDAY_12_00 = "2026-11-20T12:00:00+05:00"
FRIDAY_15_00 = "2026-11-20T15:00:00+05:00"
FRIDAY_16_00 = "2026-11-20T16:00:00+05:00"
MONDAY_10_00 = "2026-11-23T10:00:00+05:00"


def get_schedule(client, manager_id, day):
    return client.get(f"/managers/{manager_id}/schedule", params={"date": day})


def test_schedule_for_day(client):
    late_company_id = create_company(client, "100000000001")
    early_company_id = create_company(client, "100000000002")
    other_manager_company_id = create_company(client, "100000000003")
    other_day_company_id = create_company(client, "100000000004")
    cancelled_company_id = create_company(client, "100000000005")

    # создаём не по порядку, чтобы проверить сортировку
    create_meeting(client, late_company_id, FRIDAY_15_00)
    create_meeting(client, early_company_id, FRIDAY_10_00)
    # это не должно попасть в расписание Айгуль на пятницу
    create_meeting(client, other_manager_company_id, FRIDAY_12_00, manager_id=ERLAN_ID)
    create_meeting(client, other_day_company_id, MONDAY_10_00)
    cancelled_meeting_id = create_meeting(client, cancelled_company_id, FRIDAY_16_00).json()["id"]
    cancel_meeting(client, cancelled_meeting_id)

    response = get_schedule(client, AIGUL_ID, FRIDAY)

    assert response.status_code == 200
    schedule = response.json()
    assert schedule["manager_id"] == AIGUL_ID
    assert schedule["date"] == FRIDAY
    assert [meeting["company_id"] for meeting in schedule["meetings"]] == [
        early_company_id,
        late_company_id,
    ]


def test_schedule_empty_day(client):
    response = get_schedule(client, AIGUL_ID, FRIDAY)

    assert response.status_code == 200
    assert response.json()["meetings"] == []


def test_schedule_unknown_manager(client):
    unknown_manager_id = 999

    response = get_schedule(client, unknown_manager_id, FRIDAY)

    assert response.status_code == 404
    assert response.json()["error"] == "manager_not_found"
