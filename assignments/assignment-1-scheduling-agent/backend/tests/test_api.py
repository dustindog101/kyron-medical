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

    # Verify double booking fails loudly but speakably: HTTP 200 (so the
    # voice flow can utter the recovery) with success:false + speech.
    res_duplicate = test_client.post("/api/appointments/book", json={
        "patient_id": 2,
        "slot_id": slot_id,
        "body_part": "Knee",
        "issue_type": "Sports Medicine",
    })
    assert res_duplicate.status_code == 200
    dup_data = res_duplicate.get_json()
    assert dup_data["success"] is False
    assert "confirmation_speech" in dup_data

def test_book_rejects_missing_clinical_inputs(test_client):
    res = test_client.post("/api/appointments/book", json={
        "patient_id": 1,
        "body_part": "{{node.node_ask_body_part.answer}}",
        "issue_type": "",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is False
    assert "confirmation_speech" in data

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
    assert data["metrics"]["total_calls"] >= 1
    assert len(data["calls"]) >= 1

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

def test_follow_up_normalizes_to_general(test_client):
    from app.protocols import normalize_issue_type
    assert normalize_issue_type("Spine follow-up") == "General"
    assert normalize_issue_type("follow up with doctor") == "General"
    res = test_client.post("/api/routing/match", json={
        "body_part": "Spine follow-up with doctor Aisha Patel",
        "issue_type": "Spine follow-up",
        "is_new_patient": False,
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["matched_doctor"]["name"] == "Dr. Aisha Patel"

def test_call_webhook_accepts_list_transcript_and_templates(test_client):
    # Vogent includeTranscript sends a LIST; unresolved {{...}} templates
    # must not 500 (dial 7 log_call crash).
    res = test_client.post("/api/calls/webhook", json={
        "dial_id": "test-dial-list-1",
        "params": {
            "call_sid": "{{call.sid}}",
            "caller_phone": "+15550100000",
            "patient_id": "{{global.patient_id}}",
            "appointment_id": "{{global.appointment_id}}",
            "status": "ABANDONED",
            "transcript": [
                {"speaker": "HUMAN", "text": "Hello?"},
                {"speaker": "AI", "text": "Are you new or returning?"},
            ],
            "summary": "Kyron Medical Scheduling Call",
            "detected_body_part": "Knee",
            "detected_issue_type": "Sports Medicine",
            "duration_seconds": "{{call.duration}}",
        },
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True

def test_slots_accepts_vogent_params_wrapper(test_client):
    res = test_client.post("/api/slots", json={
        "dial_id": "test-dial-slots-1",
        "params": {"doctor_id": "1", "location_code": "MAIN", "limit": "3"},
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] >= 1

def test_book_second_choice_by_time_mention(test_client):
    route = test_client.post("/api/routing/match", json={
        "body_part": "Knee",
        "issue_type": "Sports Medicine",
        "is_new_patient": True,
    }).get_json()
    assert route["success"] is True
    slots = route["available_slots"]
    assert len(slots) >= 2
    first_id, second_id = slots[0]["id"], slots[1]["id"]
    # Mention the second slot's hour explicitly ("Thursday, 11 AM" style)
    import datetime
    second_hour = datetime.datetime.fromisoformat(slots[1]["start_time"]).hour
    hour12 = second_hour % 12 or 12
    pat = test_client.post("/api/patients", json={
        "name": "Second Choice Probe", "phone": "+14155550099",
    }).get_json()["patient"]
    res = test_client.post("/api/appointments/book", json={
        "patient_id": pat["id"],
        "body_part": "Knee",
        "issue_type": "Sports Medicine",
        "notes": f"Thursday at {hour12} works",
    })
    assert res.status_code == 201
    booked = res.get_json()["appointment"]
    assert booked["slot_id"] == second_id
    assert booked["slot_id"] != first_id

def test_vogent_payload_formats(test_client):
    # 1. Test routing_match with Vogent nested params and string boolean
    res = test_client.post("/api/routing/match", json={
        "dial_id": "test-vog-dial-1",
        "params": {
            "body_part": "Knee",
            "issue_type": "Sports Medicine",
            "is_new_patient": "true",
            "preferred_doctor": "Main campus",
            "preferred_location": "",
        }
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["matched_doctor"]["name"] == "Dr. Maria Chen"
    assert len(data["available_slots"]) > 0

    # 2. Test create_patient with Vogent nested params
    res_pat = test_client.post("/api/patients", json={
        "dial_id": "test-vog-dial-1",
        "params": {
            "name": "Alex Rivera",
            "phone": "+15550100000",
            "date_of_birth": "",
            "is_new_patient": "true",
        }
    })
    assert res_pat.status_code in (200, 201)
    pat_data = res_pat.get_json()
    patient_id = pat_data["patient"]["id"]
    assert patient_id is not None

    # 3. Test book_appointment with Vogent nested params, string IDs, and second option
    slot_id = data["available_slots"][0]["id"]
    res_book = test_client.post("/api/appointments/book", json={
        "dial_id": "test-vog-dial-1",
        "params": {
            "patient_id": str(patient_id),
            "slot_id": str(slot_id),
            "body_part": "Knee",
            "issue_type": "Sports Medicine",
            "notes": "The second one please",
        }
    })
    assert res_book.status_code == 201
    book_data = res_book.get_json()
    assert book_data["success"] is True
    assert "confirmation_speech" in book_data

    # 4. Test call_webhook with Vogent nested params
    res_call = test_client.post("/api/calls/webhook", json={
        "dial_id": "test-vog-dial-1",
        "params": {
            "caller_phone": "+15550100000",
            "patient_id": str(patient_id),
            "appointment_id": str(book_data["appointment"]["id"]),
            "status": "SCHEDULED",
            "transcript": "Caller: I need an appointment.\nAgent: Booked!",
            "summary": "Knee sports medicine booked.",
            "detected_body_part": "Knee",
            "detected_issue_type": "Sports Medicine",
        }
    })
    assert res_call.status_code == 201
    assert res_call.get_json()["success"] is True

def test_patient_status_strings_drive_voice_gates(test_client):
    # The flow branches on string equality (booleans misroute in Vogent),
    # so lookup/create must always return patient_status new|returning.
    found = test_client.get("/api/patients/lookup?phone=4155550111").get_json()
    assert found["patient_status"] == "returning"
    missing = test_client.get("/api/patients/lookup?phone=9998887777").get_json()
    assert missing["patient_status"] == "new"
    assert missing["found"] is False

def test_speak_time_is_tts_safe(test_client):
    import datetime
    from app.protocols import speak_time
    assert speak_time(datetime.datetime(2026, 9, 16, 10, 0)) == "10 AM"
    assert speak_time(datetime.datetime(2026, 9, 16, 13, 0)) == "1 PM"
    assert speak_time(datetime.datetime(2026, 9, 16, 9, 30)) == "9:30 AM"
    assert ":" not in speak_time(datetime.datetime(2026, 9, 16, 11, 0)).replace("AM", "").replace("PM", "")

def test_doctor_mention_inside_issue_text_redirects(test_client):
    # "Spine follow-up with doctor Patel" arrives as the issue answer; the
    # router must still credit the Patel request (redirect speech), not drop it.
    res = test_client.post("/api/routing/match", json={
        "body_part": "Hip",
        "issue_type": "Spine follow-up with doctor Patel",
        "is_new_patient": "returning",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["redirected_from_doctor"] == "Dr. Aisha Patel"
    assert "Patel" in data["agent_speech"]

def test_no_need_substring_matched_as_reed(test_client):
    # Word-boundary guard: "I need..." must not infer Dr. Thomas Reed.
    from app.database import SessionLocal
    from app.protocols import infer_preferences_from_text
    db = SessionLocal()
    try:
        loc, doc = infer_preferences_from_text(db, "I need a doctor soon")
        assert doc is None
        loc2, doc2 = infer_preferences_from_text(db, "doctor Patel please")
        assert doc2 == "Dr. Aisha Patel"
    finally:
        db.close()

def test_confirmation_speech_uses_spoken_time(test_client):
    from app.database import SessionLocal
    from app.models import Slot
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
        "issue_type": "Fracture",
    })
    assert res.status_code == 201
    speech = res.get_json()["confirmation_speech"]
    assert ":00" not in speech

def test_lookup_reports_phone_source(test_client):
    res = test_client.post("/api/patients/lookup", json={
        "phone": "+14155550111", "name": "+14155550111",
    })
    data = res.get_json()
    assert data["found"] is True
    assert data["phone_source"] == "provided"

def test_cli_resolve_skipped_without_dial_or_in_tests():
    from app.api.patients import resolve_cli_phone
    assert resolve_cli_phone(None) is None
    assert resolve_cli_phone("{{node.x}}") is None
    # TESTING config + no network in unit tests: always None, never raises.
    assert resolve_cli_phone("00000000-0000-0000-0000-000000000000") is None

def test_create_without_phone_still_works(test_client):
    res = test_client.post("/api/patients", json={"name": "CLI Less Caller"})
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    # Cleanup so the seed-data assertions elsewhere stay deterministic.
    from app.database import SessionLocal
    from app.models import Patient
    db = SessionLocal()
    try:
        db.query(Patient).filter(Patient.name == "CLI Less Caller").delete()
        db.commit()
    finally:
        db.close()

def test_platform_events_create_no_rows_and_flip_nothing(test_client):
    # Vogent dial lifecycle events ("completed" etc.) hitting the telemetry
    # endpoint must not fabricate FAILED rows (observed) or touch outcomes.
    before = test_client.get("/api/calls").get_json()["metrics"]["total_calls"]
    res = test_client.post("/api/calls/webhook", json={
        "event": "dial.updated",
        "payload": {"dial_id": "no-such-dial", "status": "completed"},
    })
    assert res.status_code == 200
    after = test_client.get("/api/calls").get_json()["metrics"]["total_calls"]
    assert after == before

def test_own_numbers_empty_in_tests():
    from app.api.patients import _own_workspace_numbers
    assert _own_workspace_numbers() == set()

def test_sync_status_declined_coordinator_offer_is_abandoned():
    # Dial 6dd3217a: agent OFFERED the coordinator, caller said "not yet",
    # heard goodbye, hung up. A mere mention must not read as a transfer.
    from app.api.calls import _infer_sync_status
    tr = ("Agent: Should I connect you with our intake coordinator now?\n"
          "Caller: Not yet. Hello?\n"
          "Agent: Thank you for calling Kyron Medical. Have a wonderful day!")
    assert _infer_sync_status(tr, "USER_HANGUP", False, 315) == "ABANDONED"

def test_sync_status_executed_transfer_is_redirected():
    from app.api.calls import _infer_sync_status
    tr = ("Agent: Please hold the line for just a moment while I transfer you "
          "to our patient intake coordinator.\nAgent: Transferring you to our "
          "patient intake coordinator now.")
    assert _infer_sync_status(tr, "TRANSFERRED", False, 124) == "REDIRECTED"
    # Platform result alone suffices even with a thin transcript.
    assert _infer_sync_status("", "TRANSFERRED", False, 0) == "REDIRECTED"
    assert _infer_sync_status("Agent: hi", "USER_HANGUP", True, 10) == "SCHEDULED"
    assert _infer_sync_status("", None, False, 0) == "FAILED"

def test_providers_list_success(test_client):
    res = test_client.post("/api/providers/list", json={
        "body_part": "Knee",
        "issue_type": "Sports Medicine",
        "is_new_patient": True,
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["status_code"] == "PROVIDERS_FOUND"
    names = [p["name"] for p in data["providers"]]
    assert "Dr. Maria Chen" in names
    assert "agent_speech" in data and "Dr. Maria Chen" in data["agent_speech"]

def test_providers_list_spine_sports_new_offers_mendez(test_client):
    # Spine + Sports Medicine has zero protocols: new callers must hear the
    # Spine General alternative open to new patients (Mendez), never a bare
    # transfer — and new-patient-closed doctors must stay excluded.
    res = test_client.post("/api/providers/list", json={
        "body_part": "Spine",
        "issue_type": "Sports Medicine",
        "is_new_patient": True,
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is False
    assert data["status_code"] == "NO_MATCH"
    alt_names = [d["name"] for d in data["alternative_doctors"]]
    assert "Dr. Carlos Mendez" in alt_names
    assert "Dr. Aisha Patel" not in alt_names
    assert "Mendez" in data["agent_speech"]

def test_providers_list_spine_sports_returning_hears_all(test_client):
    res = test_client.post("/api/providers/list", json={
        "body_part": "Spine",
        "issue_type": "Sports Medicine",
        "is_new_patient": False,
    })
    data = res.get_json()
    assert data["status_code"] == "NO_MATCH"
    alt_names = [d["name"] for d in data["alternative_doctors"]]
    assert "Dr. Aisha Patel" in alt_names
    assert "Dr. Sarah O'Brien" in alt_names
    assert "Dr. Carlos Mendez" in alt_names

def test_routing_no_match_offers_alternatives(test_client):
    # Booking path must agree with providers/list: same NO_MATCH + named
    # alternatives (Mendez for new Spine/Sports callers).
    res = test_client.post("/api/routing/match", json={
        "body_part": "Spine",
        "issue_type": "Sports Medicine",
        "is_new_patient": True,
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is False
    assert data["status_code"] == "NO_MATCH"
    assert len(data["alternative_doctors"]) >= 1
    assert "Mendez" in data["agent_speech"]

def test_lookup_chart_means_returning(test_client):
    # Seeded David Miller has a chart but zero appointments and a stale
    # is_new row flag: lookup must still triage "returning" so the flow
    # skips re-collection and duplicate creation.
    res = test_client.get("/api/patients/lookup?phone=4155550222")
    assert res.status_code == 200
    data = res.get_json()
    assert data["found"] is True
    assert data["patient_status"] == "returning"
    assert data["is_new_patient"] is False

def test_informational_preference_question_ignored(test_client):
    # "Which physicians do you have?" funneled as preferred_doctor must not
    # poison routing: it is dropped, matching proceeds normally.
    from app.protocols import clean_preference_text
    assert clean_preference_text("Which physicians do you have?") is None
    assert clean_preference_text("What doctors are available?") is None
    assert clean_preference_text("Dr. Patel") == "Dr. Patel"
    assert clean_preference_text("has_preference") is None
    assert clean_preference_text("wants_physician_list") is None
    res = test_client.post("/api/routing/match", json={
        "body_part": "Knee",
        "issue_type": "Sports Medicine",
        "is_new_patient": True,
        "preferred_doctor": "Which physicians do you have?",
    })
    data = res.get_json()
    assert data["success"] is True
    assert data["redirected_from_doctor"] is None

def test_resolve_sync_patient_phone_first(test_client):
    # STT name variant ("Peck") must not mint a duplicate chart when the
    # phone already identifies the patient ("Tuck").
    from app.database import SessionLocal
    from app.models import Patient
    from app.api.calls import resolve_sync_patient
    db = SessionLocal()
    try:
        probe = Patient(name="Sync Probe Tuck", phone="+14155557799", is_new_patient=True)
        db.add(probe)
        db.commit()
        found, created = resolve_sync_patient(db, "+14155557799", "Sync Probe Peck", True)
        assert created is False
        assert found.id == probe.id
        assert found.name == "Sync Probe Tuck"
        assert db.query(Patient).filter(Patient.phone == "+14155557799").count() == 1
    finally:
        db.query(Patient).filter(Patient.phone == "+14155557799").delete()
        db.commit()
        db.close()
