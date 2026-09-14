from flask import Blueprint, request, jsonify
from app.database import SessionLocal
from app.models import Slot

slots_bp = Blueprint("slots", __name__, url_prefix="/api/slots")

@slots_bp.route("", methods=["GET"])
def get_slots():
    """
    Retrieve open appointment slots, filterable by doctor or location.
    """
    doctor_id = request.args.get("doctor_id", type=int)
    location_code = request.args.get("location_code")
    is_booked = request.args.get("is_booked", "false").lower() == "true"
    limit = request.args.get("limit", 10, type=int)

    db = SessionLocal()
    try:
        query = db.query(Slot).filter(Slot.is_booked == is_booked)

        if doctor_id:
            query = query.filter(Slot.doctor_id == doctor_id)
        if location_code:
            query = query.filter(Slot.location_code == location_code.upper())

        slots = query.order_by(Slot.start_time).limit(limit).all()
        return jsonify({
            "count": len(slots),
            "slots": [s.to_dict() for s in slots]
        }), 200
    finally:
        db.close()
