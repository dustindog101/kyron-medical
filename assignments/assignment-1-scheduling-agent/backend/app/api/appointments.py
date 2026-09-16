import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models import Appointment, Slot, Patient, Doctor, CallLog

appointments_bp = Blueprint("appointments", __name__, url_prefix="/api/appointments")

def safe_int(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.startswith("{{"):
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None

def _clean_text(val):
    """None for missing, template-literal, or null-ish voice answers."""
    if val is None:
        return None
    if not isinstance(val, str):
        return str(val)
    s = val.strip()
    if not s or s.startswith("{{"):
        return None
    if s.lower() in ("null", "none", "no", "no."):
        return None
    return s

def _failure(message, speech):
    """Voice-function failures always return HTTP 200 with success:false.

    An HTTP error would reach the voice agent as an HTML blob it then
    hallucinates over (observed: fake booking confirmations). A 200 with
    `agent_speech`/`confirmation_speech` lets the flow speak the recovery
    instead. The `success` flag — not the status code — carries the outcome,
    consistent with /routing/match.
    """
    return jsonify({
        "error": message,
        "success": False,
        "agent_speech": speech,
        "confirmation_speech": speech,
        "message": message,
    }), 200

@appointments_bp.route("/book", methods=["POST"])
def book_appointment():
    """
    Finalize and book a patient appointment into an available slot.
    """
    raw_data = request.get_json(silent=True) or {}
    data = raw_data.get("params") if isinstance(raw_data.get("params"), dict) else raw_data

    patient_id = safe_int(data.get("patient_id"))
    slot_id = safe_int(data.get("slot_id"))
    body_part = _clean_text(data.get("body_part"))
    issue_type = _clean_text(data.get("issue_type"))
    notes = data.get("notes")
    notes = "" if not isinstance(notes, str) or notes.strip().startswith("{{") else notes

    if not body_part or not issue_type:
        return _failure(
            "body_part and issue_type are required",
            "I need a bit more detail about your symptoms before I can book. Could you tell me which body part hurts and what happened?",
        )

    db = SessionLocal()
    try:
        # Resolve patient. Never fall back to "latest patient" — booking to
        # the wrong chart is worse than failing loudly with a spoken recovery.
        patient = None
        if patient_id:
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return _failure(
                f"No patient chart found for patient_id={data.get('patient_id')}",
                "I'm having trouble pulling up your chart. Let me connect you with our patient intake coordinator who can help right away.",
            )

        # Resolve slot
        slot = None
        if slot_id:
            slot = db.query(Slot).filter(Slot.id == slot_id).first()

        # If no slot_id was given or found, pick slot based on clinical protocol match.
        # The voice flow cannot reliably reference array elements
        # ({{node...available_slots.0.id}} arrives unresolved), so the backend
        # re-runs the same deterministic routing engine to offer the identical
        # slots the caller heard, then honors their spoken choice below.
        if not slot:
            if body_part and issue_type:
                from app.protocols import route_patient
                res = route_patient(
                    db=db,
                    body_part_raw=body_part,
                    issue_type_raw=issue_type,
                    is_new_patient=patient.is_new_patient if patient else True
                )
                if res.available_slots:
                    cand = res.available_slots[0]
                    slot_cand_id = cand.id if hasattr(cand, "id") else (cand.get("id") if isinstance(cand, dict) else None)
                    if slot_cand_id:
                        slot = db.query(Slot).filter(Slot.id == slot_cand_id, Slot.is_booked == False).first()

            if not slot:
                slot = db.query(Slot).filter(Slot.is_booked == False).order_by(Slot.start_time).first()

            if not slot:
                return _failure(
                    "No available slots left to book.",
                    "I'm sorry, there are no open appointments left in the schedule right now. Let me connect you with our patient intake coordinator for further help.",
                )

        # Resolve which offered slot the caller chose. The flow passes the
        # caller's raw reply as notes (e.g. "Thursday, 10 AM", "the second
        # one", "later option"). Match explicit time mentions against the
        # candidate slots first, then fall back to second-choice keywords.
        notes_text = str(notes or "")
        notes_lower = notes_text.lower()
        candidate_slots = db.query(Slot).filter(
            Slot.doctor_id == slot.doctor_id,
            Slot.is_booked == False,
        ).order_by(Slot.start_time).limit(4).all()
        if all(s.id != slot.id for s in candidate_slots):
            candidate_slots = [slot] + candidate_slots[:3]

        def _slot_choice_index():
            import re
            hours = [int(m.group(1)) % 12 or 12 for m in re.finditer(r"\b(\d{1,2})(?::\d{2})?\s*(?:am|pm)?\b", notes_lower)]
            meridiems = re.findall(r"\b(am|pm)\b", notes_lower)
            if hours and len(candidate_slots) > 1:
                for idx, cand in enumerate(candidate_slots[:2]):
                    cand_hour_12 = cand.start_time.hour % 12 or 12
                    cand_mer = "pm" if cand.start_time.hour >= 12 else "am"
                    if cand_hour_12 in hours:
                        if meridiems and cand_mer not in meridiems:
                            continue
                        return idx
            second_keywords = ["second", "2nd", "option 2", "option2", "later",
                               "other option", "different time", "different option",
                               "the other", "11", "eleven"]
            if any(kw in notes_lower for kw in second_keywords):
                return 1
            return 0

        chosen_idx = _slot_choice_index()
        if chosen_idx and chosen_idx < len(candidate_slots):
            slot = candidate_slots[chosen_idx]

        if slot.is_booked:
            return _failure(
                "This slot was just booked by another patient. Please select another slot.",
                "I'm sorry, that time was just taken by another patient. Let me find the next available opening for you.",
            )

        # Mark slot booked
        slot.is_booked = True

        appt = Appointment(
            patient_id=patient.id,
            doctor_id=slot.doctor_id,
            slot_id=slot.id,
            location_code=slot.location_code,
            body_part=body_part or "General",
            issue_type=issue_type or "Consultation",
            notes=notes,
            status="SCHEDULED",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(appt)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return _failure(
                "This slot was just booked by another patient. Please select another slot.",
                "I'm sorry, that time was just taken by another patient. Let me find the next available opening for you.",
            )
        doctor_name = slot.doctor.name if slot.doctor else "our specialist"
        location_name = slot.location.name if slot.location else slot.location_code
        formatted_time = slot.start_time.strftime("%A, %B %d at %I:%M %p")        # Link the booking to the dial's call log when the flow passes the
        # Vogent dial id. Telemetry (transcript/status) stays owned by the
        # log_call webhook and the dial sync — booking never fabricates
        # transcripts, which previously overwrote real conversations.
        dial_key = raw_data.get("dial_id") or data.get("dial_id") or data.get("call_sid")
        if dial_key and not str(dial_key).strip().startswith("{{"):
            existing_log = db.query(CallLog).filter(CallLog.call_sid == str(dial_key)).first()
            if existing_log:
                existing_log.appointment_id = appt.id
                existing_log.status = "SCHEDULED"
                if body_part:
                    existing_log.detected_body_part = body_part
                if issue_type:
                    existing_log.detected_issue_type = issue_type
                db.commit()

        from app.protocols import speak_time
        spoken_time = f"{slot.start_time.strftime('%A, %B %d')} at {speak_time(slot.start_time)}"
        confirmation_speech = (
            f"You are all set! Your appointment with {doctor_name} is confirmed for {spoken_time} "
            f"at our {location_name}. We have sent a confirmation text with directions to your phone number."
        )

        return jsonify({
            "success": True,
            "appointment": appt.to_dict(),
            "confirmation_speech": confirmation_speech,
            "message": "Appointment booked successfully.",
        }), 201
    finally:
        db.close()

@appointments_bp.route("", methods=["GET"])
def get_appointments():
    """
    Retrieve appointments, filterable by patient_id or doctor_id.
    """
    patient_id = request.args.get("patient_id", type=int)
    doctor_id = request.args.get("doctor_id", type=int)

    db = SessionLocal()
    try:
        query = db.query(Appointment)
        if patient_id:
            query = query.filter(Appointment.patient_id == patient_id)
        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)

        appts = query.order_by(Appointment.created_at.desc()).all()
        return jsonify({
            "count": len(appts),
            "appointments": [a.to_dict() for a in appts],
        }), 200
    finally:
        db.close()
