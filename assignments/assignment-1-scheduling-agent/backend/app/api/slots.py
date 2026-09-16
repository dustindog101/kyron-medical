from flask import Blueprint, request, jsonify
from app.database import SessionLocal
from app.models import Slot

slots_bp = Blueprint("slots", __name__, url_prefix="/api/slots")

def _safe_int(val, default=None):
    if val is None:
        return default
    s = str(val).strip()
    if not s or s.startswith("{{"):
        return default
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return default

@slots_bp.route("", methods=["GET", "POST"])
def get_slots():
    """
    Retrieve open appointment slots, filterable by doctor or location.
    Accepts GET query params and POST JSON body — Vogent
    API functions only issue POST requests, wrapped as {"params": {...}}.
    """
    if request.method == "POST":
        raw = request.get_json(silent=True) or {}
        body = raw.get("params") if isinstance(raw.get("params"), dict) else raw
        doctor_id = _safe_int(body.get("doctor_id") if body.get("doctor_id") is not None else request.args.get("doctor_id"))
        location_code = body.get("location_code") or request.args.get("location_code")
        if isinstance(location_code, str) and location_code.strip().startswith("{{"):
            location_code = None
        is_booked = body.get("is_booked", False)
        if isinstance(is_booked, str):
            is_booked = is_booked.lower() == "true"
        limit = body.get("limit", request.args.get("limit", 10))
    else:
        doctor_id = request.args.get("doctor_id", type=int)
        location_code = request.args.get("location_code")
        is_booked = request.args.get("is_booked", "false").lower() == "true"
        limit = request.args.get("limit", 10)

    limit = _safe_int(limit, 10)
    try:
        limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        limit = 10

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
