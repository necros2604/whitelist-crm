from tests.test_meetings import FRIDAY_10_00, create_company, create_meeting


def create_call(client, company_id, result, meeting_id=None):
    return client.post(
        "/calls",
        json={"company_id": company_id, "result": result, "meeting_id": meeting_id},
    )


def company_status(db, company_id):
    return db.execute("SELECT status FROM companies WHERE id = %s", (company_id,)).fetchone()["status"]


def count_calls(db):
    return db.execute("SELECT count(*) AS n FROM calls").fetchone()["n"]


def test_call_meeting_set(client, db):
    company_id = create_company(client, "100000000001")
    meeting_id = create_meeting(client, company_id, FRIDAY_10_00).json()["id"]

    response = create_call(client, company_id, "meeting_set", meeting_id)

    assert response.status_code == 201
    call = response.json()
    assert call["result"] == "meeting_set"
    assert call["meeting_id"] == meeting_id
    assert company_status(db, company_id) == "meeting_set"


def test_call_meeting_set_without_meeting(client, db):
    company_id = create_company(client, "100000000001")

    response = create_call(client, company_id, "meeting_set")

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
    assert count_calls(db) == 0


def test_call_meeting_set_unknown_meeting(client, db):
    company_id = create_company(client, "100000000001")
    unknown_meeting_id = 999

    response = create_call(client, company_id, "meeting_set", unknown_meeting_id)

    assert response.status_code == 422
    assert response.json()["error"] == "meeting_not_found"
    assert count_calls(db) == 0


def test_call_meeting_of_other_company(client, db):
    company_id = create_company(client, "100000000001")
    other_company_id = create_company(client, "100000000002")
    other_company_meeting_id = create_meeting(client, other_company_id, FRIDAY_10_00).json()["id"]

    response = create_call(client, company_id, "meeting_set", other_company_meeting_id)

    assert response.status_code == 422
    assert response.json()["error"] == "meeting_other_company"
    assert count_calls(db) == 0


def test_call_updates_company_status(client, db):
    company_id = create_company(client, "100000000001")

    create_call(client, company_id, "no_answer")
    assert company_status(db, company_id) == "no_answer"

    create_call(client, company_id, "refused")
    assert company_status(db, company_id) == "refused"
