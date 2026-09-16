import pytest
from app.database import SessionLocal, init_db
from app.seed import seed_database
from app.protocols import route_patient, normalize_body_part, normalize_issue_type

@pytest.fixture(scope="module")
def db_session():
    seed_database()
    session = SessionLocal()
    yield session
    session.close()

def test_normalization_synonyms():
    # Body part synonyms
    assert normalize_body_part("right knee") == "Knee"
    assert normalize_body_part("swollen ankle") == "Foot/Ankle"
    assert normalize_body_part("lower back pain") == "Spine"
    assert normalize_body_part("broken wrist") == "Hand/Wrist"
    assert normalize_body_part("rotator cuff") == "Shoulder"

    # Issue type synonyms
    assert normalize_issue_type("torn acl") == "Sports Medicine"
    assert normalize_issue_type("compound fracture") == "Fracture"
    assert normalize_issue_type("hip replacement surgery") == "Joint Replacement"
    assert normalize_issue_type("general consultation") == "General"

def test_knee_fracture_routing_excludes_chen(db_session):
    """
    Dr. Maria Chen treats Knee Joint Replacement & Sports Medicine, but NOT fractures.
    Dr. James Walsh and Dr. Elena Vasquez treat Knee Fractures.
    """
    res = route_patient(
        db=db_session,
        body_part_raw="Knee",
        issue_type_raw="Fracture",
        is_new_patient=True,
    )
    assert res.success is True
    assert res.matched_doctor.name in ["Dr. James Walsh", "Dr. Elena Vasquez"]
    assert res.matched_doctor.name != "Dr. Maria Chen"

def test_new_patient_rejected_by_closed_doctor_with_redirect(db_session):
    """
    Dr. Aisha Patel treats Hip Joint Replacement, but is NOT accepting new patients.
    New patient requesting Dr. Patel should be redirected to Dr. Maria Chen or Dr. Elena Vasquez.
    """
    res = route_patient(
        db=db_session,
        body_part_raw="Hip",
        issue_type_raw="Joint Replacement",
        is_new_patient=True,
        preferred_doctor_name="Aisha Patel",
    )
    assert res.success is True
    assert res.redirected_from_doctor == "Dr. Aisha Patel"
    assert "only accepting returning patients" in res.redirect_reason
    assert res.matched_doctor.name in ["Dr. Maria Chen", "Dr. Elena Vasquez", "Dr. Linda Torres"]

def test_returning_patient_allowed_with_closed_doctor(db_session):
    """
    Returning patient requesting Dr. Aisha Patel for Spine General SHOULD be accepted.
    """
    res = route_patient(
        db=db_session,
        body_part_raw="Spine",
        issue_type_raw="General",
        is_new_patient=False,
        preferred_doctor_name="Aisha Patel",
    )
    assert res.success is True
    assert res.matched_doctor.name == "Dr. Aisha Patel"
    assert res.redirected_from_doctor is None

def test_general_doctor_cannot_take_fracture(db_session):
    """
    Dr. David Nguyen treats Hand/Wrist General, but NOT Fracture.
    A patient asking for Dr. Nguyen for a wrist fracture should be redirected to Dr. Robert Kim.
    """
    res = route_patient(
        db=db_session,
        body_part_raw="Hand/Wrist",
        issue_type_raw="Fracture",
        is_new_patient=True,
        preferred_doctor_name="David Nguyen",
    )
    assert res.success is True
    assert res.redirected_from_doctor == "Dr. David Nguyen"
    assert res.matched_doctor.name == "Dr. Robert Kim"

def test_multi_location_doctor_preference(db_session):
    """
    Dr. Elena Vasquez is at MAIN and WEST.
    When caller prefers WEST, slots at WEST should be returned.
    """
    res = route_patient(
        db=db_session,
        body_part_raw="Knee",
        issue_type_raw="Sports Medicine",
        is_new_patient=True,
        preferred_doctor_name="Elena Vasquez",
        preferred_location_code="WEST",
    )
    assert res.success is True
    assert res.matched_doctor.name == "Dr. Elena Vasquez"
    assert len(res.available_slots) > 0
    assert res.available_slots[0].location_code == "WEST"

def test_fallback_when_top_doctor_has_no_slots(db_session):
    """
    Dr. Maria Chen is seeded with day-1 slots booked.
    Routing for Knee Joint Replacement should return valid slots, falling back if necessary.
    """
    res = route_patient(
        db=db_session,
        body_part_raw="Knee",
        issue_type_raw="Joint Replacement",
        is_new_patient=True,
    )
    assert res.success is True
    assert len(res.available_slots) > 0

def test_no_slots_returns_graceful_failure_not_crash(db_session):
    """Regression: NO_SLOTS_AVAILABLE must return a result, not raise TypeError."""
    from app.models import Slot, DoctorProtocol
    protos = db_session.query(DoctorProtocol).filter(
        DoctorProtocol.body_part == "Foot/Ankle",
        DoctorProtocol.accepted_type == "Joint Replacement",
    ).all()
    ids = [p.doctor_id for p in protos]
    assert len(ids) > 0
    db_session.query(Slot).filter(Slot.doctor_id.in_(ids)).update(
        {Slot.is_booked: True}, synchronize_session=False
    )
    db_session.commit()
    try:
        res = route_patient(
            db=db_session,
            body_part_raw="Foot/Ankle",
            issue_type_raw="Joint Replacement",
            is_new_patient=True,
        )
        assert res.success is False
        assert res.status_code == "NO_SLOTS_AVAILABLE"
        assert res.matched_doctor is not None
        res.to_dict()
    finally:
        db_session.query(Slot).filter(Slot.doctor_id.in_(ids)).update(
            {Slot.is_booked: False}, synchronize_session=False
        )
        db_session.commit()
