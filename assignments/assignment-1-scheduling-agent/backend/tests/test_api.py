import pytest
from app import create_app
from app.seed import seed_database
from app.database import SessionLocal
from app.models import Slot

@pytest.fixture(scope="module")
def test_client():
    seed_database()
    flask_app = create_app({"TESTING": True})
    with flask_app.test_client() as client:
        yield client

def test_health_check(test_client):
    res = test_client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"

def test_patient_lookup_existing(test_client):
    res = test_client.get("/api/patients/lookup?phone=4155550111")
    assert res.status_code == 200
    data = res.get_json()
    assert data["found"] is True
    assert data["patient"]["name"] == "Alice Johnson"
    assert data["is_new_patient"] is False

def test_patient_lookup_new(test_client):
    res = test_client.get("/api/patients/lookup?phone=9998887777")
    assert res.status_code == 200
    data = res.get_json()
    assert data["found"] is False
    assert data["is_new_patient"] is True

def test_create_patient(test_client):
    res = test_client.post("/api/patients", json={
        "name": "Jordan Peterson",
        "phone": "+14155559988",
        "date_of_birth": "1990-01-01",
        "is_new_patient": True,
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["patient"]["name"] == "Jordan Peterson"

def test_routing_match_endpoint(test_client):
    res = test_client.post("/api/routing/match", json={
        "body_part": "Knee",
        "issue_type": "Sports Medicine",
        "is_new_patient": True,
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "matched_doctor" in data
    assert len(data["available_slots"]) > 0
    assert "agent_speech" in data

def test_appointment_booking(test_client):
    db = SessionLocal()
    try:
        slot = db.query(Slot).filter(Slot.is_booked == False).first()
        slot_id = slot.id
    finally:
        db.close()

    res = test_client.post("/api/appointments/book", json={
        "patient_id": 1,
        "slot_id": slot_id,
        "body_part": "Knee",
        "issue_type": "Sports Medicine",
        "notes": "Left knee meniscus tear",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "confirmation_speech" in data

    # Verify double booking fails
    res_duplicate = test_client.post("/api/appointments/book", json={
        "patient_id": 2,
        "slot_id": slot_id,
        "body_part": "Knee",
        "issue_type": "Sports Medicine",
    })
    assert res_duplicate.status_code == 409

def test_call_webhook_and_list(test_client):
    res = test_client.post("/api/calls/webhook", json={
        "call_sid": "TEST-CALL-1234",
        "caller_phone": "+14155550222",
        "patient_id": 1,
        "status": "SCHEDULED",
        "transcript": "Agent: How can I help?\nCaller: Need appointment.",
        "summary": "Patient booked test appointment.",
        "detected_body_part": "Knee",
        "detected_issue_type": "Fracture",
        "duration_seconds": 60,
    })
    assert res.status_code == 201

    # Fetch calls list
    list_res = test_client.get("/api/calls")
    assert list_res.status_code == 200
    data = list_res.get_json()
    assert data["metrics"]["total_calls"] >= 4
    assert len(data["calls"]) >= 4

def test_simulate_call(test_client):
    res = test_client.post("/api/calls/simulate", json={
        "caller_name": "Maya Lin",
        "caller_phone": "+14155554321",
        "body_part": "Shoulder",
        "issue_type": "Sports Medicine",
        "is_new_patient": True,
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["status"] == "SCHEDULED"
    assert "Maya Lin" in data["call"]["transcript"]
