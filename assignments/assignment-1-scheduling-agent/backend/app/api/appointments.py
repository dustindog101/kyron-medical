import datetime
from flask import Blueprint, request, jsonify
from app.database import SessionLocal
from app.models import Appointment, Slot, Patient, Doctor

appointments_bp = Blueprint("appointments", __name__, url_prefix="/api/appointments")

@appointments_bp.route("/book", methods=["POST"])
def book_appointment():
    """
    Finalize and book a patient appointment into an available slot.
    """
    data = request.get_json() or {}
    patient_id = data.get("patient_id")
    slot_id = data.get("slot_id")
    body_part = data.get("body_part")
    issue_type = data.get("issue_type")
    notes = data.get("notes")

    if not patient_id or not slot_id:
        return jsonify({"error": "patient_id and slot_id are required"}), 400

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return jsonify({"error": f"Patient with ID {patient_id} not found"}), 404

        slot = db.query(Slot).filter(Slot.id == slot_id).first()
        if not slot:
            return jsonify({"error": f"Slot with ID {slot_id} not found"}), 404

        if slot.is_booked:
            return jsonify({
                "error": "This slot was just booked by another patient. Please select another slot."
            }), 409

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
        db.commit()
        db.refresh(appt)

        doctor_name = slot.doctor.name
        location_name = slot.location.name
        formatted_time = slot.start_time.strftime("%A, %B %d at %I:%M %p")

        confirmation_speech = (
            f"You are all set! Your appointment with {doctor_name} is confirmed for {formatted_time} "
            f"at our {location_name}. We have sent a confirmation text with directions to your phone number. "
            f"Thank you for calling Kyron Medical, and take care!"
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
