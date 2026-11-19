def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_validation_error_format(client):
    r = client.post("/companies", json={"name": "ТОО Ромашка", "bin": "123", "phone": "+77011234567"})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validation_error"
    assert "bin" in body["message"]


def test_invalid_json(client):
    broken_json = '{"name": "ТОО Ромашка", "bin": {{company.id}}}'

    response = client.post("/companies", content=broken_json, headers={"Content-Type": "application/json"})

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_json"
