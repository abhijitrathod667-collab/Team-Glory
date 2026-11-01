import time
import pytest
from fastapi.testclient import TestClient
from app import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(main.ai_service, "configured", lambda: False)  # never call Gemini in tests
    main.REPORTS[:] = [dict(r, ts=time.time() - r["age"] * 60) for r in main.SEED_REPORTS]


def test_state_matches_demo():
    d = client.get("/api/state?rain=70").json()
    assert d["banner"]["level"] == "Critical" and d["kpi"]["affected"] == 5 and len(d["reports"]) == 3

def test_rain_is_clamped():
    assert client.get("/api/state?rain=999").json()["rain"] == 160

def test_route_and_errors():
    assert client.get("/api/route?src=kheri&dst=nadi&rain=70").json()["safe"]["km"] == 185
    assert client.get("/api/route?src=kheri&dst=kheri").status_code == 400
    assert client.get("/api/route?src=kheri&dst=zzz").status_code == 404

def test_one_more_blocked_report_cuts_nadi_sagar():  # one Blocked report is already seeded
    r = client.post("/api/reports", json={"road": "nadi-sagar", "text": "पत्थर गिर रहे हैं"}).json()
    assert r["status"] == "Blocked" and r["verified"] is True
    roads = {x["k"]: x["status"] for x in client.get("/api/state?rain=70").json()["roads"]}
    assert roads["nadi-sagar"] == "Cut"

def test_validation():
    assert client.post("/api/reports", json={"road": "x", "text": "hello"}).status_code == 400
    assert client.post("/api/help", json={"type": "Food", "village": "nadi", "people": 0}).status_code == 400
    assert client.post("/api/help", json={"type": "Food", "village": "nadi", "people": 5}).json()["sent"] is False


def test_report_without_road_finds_it_from_text():
    r = client.post("/api/reports", json={"road": "", "text": "Nadi Pur aur Sagar Gaon ke beech pathar gir rahe hain"}).json()
    assert r["road"] == "nadi-sagar" and r["status"] == "Blocked"

def test_report_with_no_road_anywhere_is_rejected():
    assert client.post("/api/reports", json={"road": "", "text": "pathar gir rahe hain"}).status_code == 400

def test_brief_and_alert_work_without_ai():
    b = client.get("/api/brief?rain=70").json()
    assert b["source"] == "template" and b["en"] and b["hi"]
    a = client.get("/api/alert?village=nadi&rain=70").json()
    assert a["source"] == "template" and a["hi"]
    assert client.get("/api/alert?village=zzz").status_code == 404


def test_advice_works_without_ai():
    a = client.post("/api/advice", json={"village": "nadi", "problem": "dawa khatam ho gayi aur road band hai", "rain": 70}).json()
    assert a["source"] == "template" and len(a["en"]) == len(a["hi"]) >= 2 and "112" in a["en"][-1] and a["impact_en"] and a["impact_hi"]
    assert client.post("/api/advice", json={"village": "zzz", "problem": "help me"}).status_code == 400
    assert client.post("/api/advice", json={"village": "nadi", "problem": "x"}).status_code == 400


def test_rain_defaults_to_forecast():
    d = client.get("/api/state").json()
    assert d["rain"] == d["forecast_mm"] == 70 and d["what_if"] is False
    w = client.get("/api/state?rain=120").json()
    assert w["rain"] == 120 and w["what_if"] is True

