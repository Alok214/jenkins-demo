import pytest
from app.main import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_home(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "running"

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "UP"

def test_calc_add(client):
    res = client.get("/calc/add?a=5&b=3")
    assert res.status_code == 200
    assert res.get_json()["result"] == 8

def test_calc_divide(client):
    res = client.get("/calc/divide?a=10&b=2")
    assert res.status_code == 200
    assert res.get_json()["result"] == 5

def test_calc_divide_zero(client):
    res = client.get("/calc/divide?a=10&b=0")
    assert res.status_code == 400
