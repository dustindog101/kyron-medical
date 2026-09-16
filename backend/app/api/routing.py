from flask import Blueprint, request, jsonify
from app.database import SessionLocal
from app.protocols import (
    route_patient,
    clean_preference_text,
    infer_preferences_from_text,
    normalize_location_code,
)

routing_bp = Blueprint("routing", __name__, url_prefix="/api/routing")

@routing_bp.route("/match", methods=["POST"])
def match_physician():
    """
    Main webhook endpoint called by Vogent during the phone call.
    Matches the patient's complaint against the physician protocol rules.
    Returns the recommended doctor, speech script, and open slots.
    """
    raw_data = request.get_json(silent=True) or {}
    data = raw_data.get("params") if isinstance(raw_data.get("params"), dict) else raw_data

    body_part = data.get("body_part")
    if isinstance(body_part, str) and body_part.strip().startswith("{{"):
        body_part = None
    issue_type = data.get("issue_type")
    if isinstance(issue_type, str) and issue_type.strip().startswith("{{"):
        issue_type = None
    is_new_patient_raw = data.get("is_new_patient", True)
    if isinstance(is_new_patient_raw, str):
        if is_new_patient_raw.strip().startswith("{{"):
            is_new_patient = True
        else:
            is_new_patient = is_new_patient_raw.strip().lower() in ("true", "1", "yes", "new", "new patient")
    else:
        is_new_patient = bool(is_new_patient_raw)

    preferred_location = clean_preference_text(data.get("preferred_location"))
    preferred_doctor = clean_preference_text(data.get("preferred_doctor"))

    if not body_part or not issue_type:
        return jsonify({
            "success": False,
            "status_code": "MISSING_INPUTS",
            "agent_speech": "I need a bit more detail about your symptoms. Could you describe which area of your body hurts and what happened?",
            "message": "body_part and issue_type are required",
            "matched_doctor": None,
            "available_slots": [],
            "alternative_doctors": []
        }), 200

    db = SessionLocal()
    try:
        # The flow funnels whole freeform answers into single fields: a doctor
        # name may arrive inside the issue-type answer ("Spine follow-up with
        # doctor Patel") and a location inside any of them. Scan all three.
        inferred_loc, inferred_doc = infer_preferences_from_text(
            db, preferred_location, preferred_doctor, body_part, issue_type
        )
        if not preferred_location:
            preferred_location = inferred_loc
        else:
            preferred_location = normalize_location_code(preferred_location) or inferred_loc
        if not preferred_doctor:
            preferred_doctor = inferred_doc

        result = route_patient(
            db=db,
            body_part_raw=body_part,
            issue_type_raw=issue_type,
            is_new_patient=is_new_patient,
            preferred_location_code=preferred_location,
            preferred_doctor_name=preferred_doctor,
        )
        return jsonify(result.to_dict()), 200
    finally:
        db.close()
