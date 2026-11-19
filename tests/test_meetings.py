import threading

# 2026-11-20 - пятница. 10:00 по Алматы = 05:00 UTC
FRIDAY_10_00 = "2026-11-20T10:00:00+05:00"
FRIDAY_10_30 = "2026-11-20T10:30:00+05:00"
FRIDAY_11_00 = "2026-11-20T11:00:00+05:00"
FRIDAY_15_00 = "2026-11-20T15:00:00+05:00"
FRIDAY_17_30 = "2026-11-20T17:30:00+05:00"

AIGUL_ID = 1
ERLAN_ID = 2


def create_company(client, bin):
    response = client.post("/companies", json={"name": f"ТОО {bin}", "bin": bin, "phone": "+77011234567"})
    return response.json()["id"]


def create_meeting(client, company_id, starts_at, manager_id=AIGUL_ID):
    return client.post(
        "/meetings",
        json={"manager_id": manager_id, "company_id": company_id, "starts_at": starts_at},
    )


def count_meetings(db):
    return db.execute("SELECT count(*) AS n FROM meetings").fetchone()["n"]


def test_create_meeting(client, db):
    company_id = create_company(client, "100000000001")

    response = create_meeting(client, company_id, FRIDAY_10_00)

    assert response.status_code == 201
    meeting = response.json()
    # отдаём в UTC, конец = начало + 60 минут
    assert meeting["starts_at"] == "2026-11-20T05:00:00Z"
    assert meeting["ends_at"] == "2026-11-20T06:00:00Z"
    assert meeting["status"] == "scheduled"
    assert meeting["original_starts_at"] == "2026-11-20T05:00:00Z"
    assert [event["kind"] for event in meeting["history"]] == ["created"]

    saved_meeting = db.execute("SELECT * FROM meetings WHERE id = %s", (meeting["id"],)).fetchone()
    assert saved_meeting["manager_id"] == AIGUL_ID
    assert saved_meeting["company_id"] == company_id


def test_meeting_overlap(client, db):
    first_company_id = create_company(client, "100000000001")
    second_company_id = create_company(client, "100000000002")
    assert create_meeting(client, first_company_id, FRIDAY_10_00).status_code == 201

    # у того же менеджера 10:30-11:30 пересекается с 10:00-11:00
    response = create_meeting(client, second_company_id, FRIDAY_10_30)

    assert response.status_code == 409
    assert response.json()["error"] == "manager_busy"
    assert count_meetings(db) == 1


def test_meetings_back_to_back_no_conflict(client):
    first_company_id = create_company(client, "100000000001")
    second_company_id = create_company(client, "100000000002")
    assert create_meeting(client, first_company_id, FRIDAY_10_00).status_code == 201

    # 11:00-12:00 сразу после 10:00-11:00 - не конфликт
    response = create_meeting(client, second_company_id, FRIDAY_11_00)

    assert response.status_code == 201


def test_company_one_active_meeting(client):
    company_id = create_company(client, "100000000001")
    assert create_meeting(client, company_id, FRIDAY_10_00, manager_id=AIGUL_ID).status_code == 201

    # другой менеджер и другое время, но у компании уже есть активная встреча
    response = create_meeting(client, company_id, FRIDAY_15_00, manager_id=ERLAN_ID)

    assert response.status_code == 409
    assert response.json()["error"] == "company_has_meeting"


def test_meeting_outside_working_hours(client, db):
    company_id = create_company(client, "100000000001")

    response = create_meeting(client, company_id, FRIDAY_17_30)

    assert response.status_code == 422
    assert response.json()["error"] == "outside_working_hours"
    assert count_meetings(db) == 0


def test_meeting_unknown_manager(client):
    company_id = create_company(client, "100000000001")
    unknown_manager_id = 999

    response = create_meeting(client, company_id, FRIDAY_10_00, manager_id=unknown_manager_id)

    assert response.status_code == 404
    assert response.json()["error"] == "manager_not_found"


def reschedule_meeting(client, meeting_id, starts_at):
    return client.patch(f"/meetings/{meeting_id}", json={"starts_at": starts_at})


def cancel_meeting(client, meeting_id):
    return client.patch(f"/meetings/{meeting_id}", json={"status": "cancelled"})


def test_reschedule_keeps_history(client):
    company_id = create_company(client, "100000000001")
    meeting_id = create_meeting(client, company_id, FRIDAY_10_00).json()["id"]

    response = reschedule_meeting(client, meeting_id, FRIDAY_15_00)

    assert response.status_code == 200
    meeting = response.json()
    assert meeting["starts_at"] == "2026-11-20T10:00:00Z"
    assert meeting["ends_at"] == "2026-11-20T11:00:00Z"
    # изначальное время не потерялось
    assert meeting["original_starts_at"] == "2026-11-20T05:00:00Z"
    assert [event["kind"] for event in meeting["history"]] == ["created", "rescheduled"]
    assert [event["starts_at"] for event in meeting["history"]] == [
        "2026-11-20T05:00:00Z",
        "2026-11-20T10:00:00Z",
    ]


def test_reschedule_overlapping_own_old_time(client):
    company_id = create_company(client, "100000000001")
    meeting_id = create_meeting(client, company_id, FRIDAY_10_00).json()["id"]

    # 10:30-11:30 пересекается со старым 10:00-11:00, но это та же встреча - не конфликт
    response = reschedule_meeting(client, meeting_id, FRIDAY_10_30)

    assert response.status_code == 200


def test_reschedule_into_busy_slot(client, db):
    first_company_id = create_company(client, "100000000001")
    second_company_id = create_company(client, "100000000002")
    create_meeting(client, first_company_id, FRIDAY_10_00)
    second_meeting_id = create_meeting(client, second_company_id, FRIDAY_11_00).json()["id"]

    response = reschedule_meeting(client, second_meeting_id, FRIDAY_10_30)

    assert response.status_code == 409
    assert response.json()["error"] == "manager_busy"
    saved_meeting = db.execute("SELECT starts_at FROM meetings WHERE id = %s", (second_meeting_id,)).fetchone()
    assert saved_meeting["starts_at"].isoformat() == "2026-11-20T06:00:00+00:00"


def test_reschedule_outside_working_hours(client):
    company_id = create_company(client, "100000000001")
    meeting_id = create_meeting(client, company_id, FRIDAY_10_00).json()["id"]

    response = reschedule_meeting(client, meeting_id, FRIDAY_17_30)

    assert response.status_code == 422
    assert response.json()["error"] == "outside_working_hours"


def test_cancel_meeting_frees_slot(client):
    first_company_id = create_company(client, "100000000001")
    second_company_id = create_company(client, "100000000002")
    meeting_id = create_meeting(client, first_company_id, FRIDAY_10_00).json()["id"]

    response = cancel_meeting(client, meeting_id)

    assert response.status_code == 200
    meeting = response.json()
    assert meeting["status"] == "cancelled"
    assert [event["kind"] for event in meeting["history"]] == ["created", "cancelled"]
    # отменённая встреча не занимает слот менеджера
    assert create_meeting(client, second_company_id, FRIDAY_10_00).status_code == 201


def test_cancelled_meeting_cannot_be_changed(client):
    company_id = create_company(client, "100000000001")
    meeting_id = create_meeting(client, company_id, FRIDAY_10_00).json()["id"]
    cancel_meeting(client, meeting_id)

    response = reschedule_meeting(client, meeting_id, FRIDAY_15_00)

    assert response.status_code == 409
    assert response.json()["error"] == "meeting_cancelled"


def test_same_slot_at_the_same_time(client, db):
    first_company_id = create_company(client, "100000000001")
    second_company_id = create_company(client, "100000000002")
    start_together = threading.Barrier(2)
    status_codes = []

    def book(company_id):
        start_together.wait()
        status_codes.append(create_meeting(client, company_id, FRIDAY_10_00).status_code)

    threads = [threading.Thread(target=book, args=(company_id,)) for company_id in (first_company_id, second_company_id)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # один успел, второй получил конфликт (не 500 и не 503), в БД одна встреча
    assert sorted(status_codes) == [201, 409]
    assert count_meetings(db) == 1
