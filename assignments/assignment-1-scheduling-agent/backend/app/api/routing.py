from flask import Blueprint, request, jsonify
from app.database import SessionLocal
from app.protocols import route_patient

routing_bp = Blueprint("routing", __name__, url_prefix="/api/routing")

@routing_bp.route("/match", methods=["POST"])
def match_physician():
    """
    Main webhook endpoint called by Vogent during the phone call.
    Matches the patient's complaint against the physician protocol rules.
    Returns the recommended doctor, speech script, and open slots.
    """
    data = request.get_json() or {}
    body_part = data.get("body_part")
    issue_type = data.get("issue_type")
    is_new_patient = data.get("is_new_patient", True)
    preferred_location = data.get("preferred_location")
    preferred_doctor = data.get("preferred_doctor")

    if not body_part or not issue_type:
        return jsonify({
            "error": "body_part and issue_type are required",
            "example": {
                "body_part": "Knee",
                "issue_type": "Sports Medicine",
                "is_new_patient": True,
                "preferred_location": "MAIN",
                "preferred_doctor": "Dr. Maria Chen",
            }
        }), 400

    db = SessionLocal()
    try:
        result = route_patient(
            db=db,
            body_part_raw=body_part,
            issue_type_raw=issue_type,
            is_new_patient=is_new_patient,
            preferred_location_code=preferred_location,
            preferred_doctor_name=preferred_doctor,
        )
        return jsonify(result.to_dict()), 200 if result.success else 422
    finally:
        db.close()
