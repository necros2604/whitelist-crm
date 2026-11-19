COMPANY = {"name": "ТОО Алматы Трейд Компани", "bin": "170340021554", "phone": "+77011234567"}


def create_company(client, **fields):
    return client.post("/companies", json={**COMPANY, **fields})


def test_create_company(client, db):
    r = create_company(client)

    assert r.status_code == 201
    body = r.json()
    assert body["id"] > 0
    assert body["name"] == COMPANY["name"]
    assert body["bin"] == COMPANY["bin"]
    assert body["phone"] == COMPANY["phone"]
    assert body["status"] == "new"
    assert body["created_at"]

    row = db.execute("SELECT * FROM companies WHERE id = %s", (body["id"],)).fetchone()
    assert row["name"] == COMPANY["name"]
    assert row["bin"] == COMPANY["bin"]
    assert row["phone"] == COMPANY["phone"]
    assert row["status"] == "new"


def test_create_company_duplicate_bin(client, db):
    assert create_company(client).status_code == 201

    r = create_company(client, name="Другая компания")

    assert r.status_code == 409
    assert r.json()["error"] == "bin_exists"
    assert db.execute("SELECT count(*) AS n FROM companies").fetchone()["n"] == 1


def test_list_companies_pagination(client):
    for i in range(3):
        create_company(client, name=f"Компания {i}", bin=f"10000000000{i}")

    first = client.get("/companies", params={"limit": 2}).json()
    second = client.get("/companies", params={"limit": 2, "offset": 2}).json()

    assert first["total"] == 3
    assert [c["name"] for c in first["items"]] == ["Компания 0", "Компания 1"]
    assert second["total"] == 3
    assert [c["name"] for c in second["items"]] == ["Компания 2"]


def test_list_companies_filter_by_status(client, db):
    create_company(client, name="Отказала", bin="100000000001")
    create_company(client, name="Новая", bin="100000000002")
    # звонков пока нет, поэтому статус меняем напрямую в БД
    db.execute("UPDATE companies SET status = 'refused' WHERE bin = '100000000001'")

    r = client.get("/companies", params={"status": "refused"})

    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert [c["name"] for c in r.json()["items"]] == ["Отказала"]
