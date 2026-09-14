import datetime
import uuid
from flask import Blueprint, request, jsonify
from app.database import SessionLocal
from app.models import CallLog, Patient, Appointment, Slot, Doctor
from app.protocols import route_patient

calls_bp = Blueprint("calls", __name__, url_prefix="/api/calls")

@calls_bp.route("/webhook", methods=["POST"])
def call_webhook():
    """
    Webhook endpoint invoked by Vogent when a call ends.
    Logs call metadata, full transcript, status, and linked appointment.
    """
    data = request.get_json() or {}
    caller_phone = data.get("caller_phone")
    transcript = data.get("transcript")

    if not caller_phone or not transcript:
        return jsonify({"error": "caller_phone and transcript are required"}), 400

    call_sid = data.get("call_sid") or f"VOG-{uuid.uuid4().hex[:12].upper()}"
    status = (data.get("status") or "FAILED").upper()
    if status not in ["SCHEDULED", "REDIRECTED", "ABANDONED", "FAILED"]:
        status = "FAILED"

    db = SessionLocal()
    try:
        log = CallLog(
            call_sid=call_sid,
            caller_phone=caller_phone,
            patient_id=data.get("patient_id"),
            appointment_id=data.get("appointment_id"),
            status=status,
            transcript=transcript,
            summary=data.get("summary"),
            detected_body_part=data.get("detected_body_part"),
            detected_issue_type=data.get("detected_issue_type"),
            duration_seconds=data.get("duration_seconds", 0),
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        return jsonify({
            "success": True,
            "call_id": log.id,
            "call_sid": log.call_sid,
            "message": "Call log saved successfully.",
        }), 201
    finally:
        db.close()

@calls_bp.route("", methods=["GET"])
def get_calls():
    """
    List calls for the Call Review dashboard with filtering by status.
    """
    status_filter = request.args.get("status")
    limit = request.args.get("limit", 50, type=int)

    db = SessionLocal()
    try:
        query = db.query(CallLog).order_by(CallLog.created_at.desc())
        if status_filter and status_filter.upper() != "ALL":
            query = query.filter(CallLog.status == status_filter.upper())

        calls = query.limit(limit).all()

        # Compute summary statistics
        total = db.query(CallLog).count()
        scheduled_count = db.query(CallLog).filter(CallLog.status == "SCHEDULED").count()
        redirected_count = db.query(CallLog).filter(CallLog.status == "REDIRECTED").count()
        abandoned_count = db.query(CallLog).filter(CallLog.status == "ABANDONED").count()
        failed_count = db.query(CallLog).filter(CallLog.status == "FAILED").count()

        return jsonify({
            "metrics": {
                "total_calls": total,
                "scheduled": scheduled_count,
                "redirected": redirected_count,
                "abandoned": abandoned_count,
                "failed": failed_count,
                "conversion_rate": f"{(scheduled_count / total * 100):.1f}%" if total > 0 else "0.0%",
            },
            "calls": [c.to_dict() for c in calls],
        }), 200
    finally:
        db.close()

@calls_bp.route("/<int:call_id>", methods=["GET"])
def get_call_detail(call_id: int):
    """
    Retrieve full call transcript and booking details by ID.
    """
    db = SessionLocal()
    try:
        call = db.query(CallLog).filter(CallLog.id == call_id).first()
        if not call:
            return jsonify({"error": f"Call with ID {call_id} not found"}), 404
        return jsonify(call.to_dict()), 200
    finally:
        db.close()

@calls_bp.route("/simulate", methods=["POST"])
def simulate_call():
    """
    Interactive test simulation endpoint.
    Simulates a call end-to-end to easily demonstrate to evaluators in the dashboard.
    """
    data = request.get_json() or {}
    caller_name = data.get("caller_name", "Alex Rivera")
    caller_phone = data.get("caller_phone", "+14155557788")
    body_part = data.get("body_part", "Knee")
    issue_type = data.get("issue_type", "Sports Medicine")
    is_new_patient = data.get("is_new_patient", True)
    preferred_doctor = data.get("preferred_doctor")

    db = SessionLocal()
    try:
        # 1. Lookup or create patient
        patient = db.query(Patient).filter(Patient.phone.like(f"%{caller_phone[-10:]}%")).first()
        if not patient:
            patient = Patient(
                name=caller_name,
                phone=caller_phone,
                is_new_patient=is_new_patient,
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)

        # 2. Run protocol routing
        route_res = route_patient(
            db=db,
            body_part_raw=body_part,
            issue_type_raw=issue_type,
            is_new_patient=is_new_patient,
            preferred_doctor_name=preferred_doctor,
        )

        appt_id = None
        status = "FAILED"
        if route_res.success and route_res.available_slots:
            # Book first slot
            selected_slot = route_res.available_slots[0]
            # Verify slot is not booked
            slot = db.query(Slot).filter(Slot.id == selected_slot.id, Slot.is_booked == False).first()
            if slot:
                slot.is_booked = True
                appt = Appointment(
                    patient_id=patient.id,
                    doctor_id=slot.doctor_id,
                    slot_id=slot.id,
                    location_code=slot.location_code,
                    body_part=body_part,
                    issue_type=issue_type,
                    status="SCHEDULED",
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                )
                db.add(appt)
                db.commit()
                db.refresh(appt)
                appt_id = appt.id
                status = "SCHEDULED"
            else:
                status = "FAILED"
        elif "REDIRECTED" in route_res.status_code or "CLOSED" in route_res.status_code:
            status = "REDIRECTED"

        # 3. Synthesize realistic transcript
        time_str = selected_slot.start_time.strftime('%A, %B %d at %I:%M %p') if (route_res.success and route_res.available_slots) else "unspecified time"
        doc_name = route_res.matched_doctor.name if route_res.matched_doctor else "Specialist"
        loc_name = selected_slot.location.name if (route_res.success and route_res.available_slots) else "Clinic"

        transcript = (
            f"Agent: Thank you for calling Kyron Medical Scheduling. Are you a new or returning patient?\n"
            f"Caller: Hi, I'm calling about an appointment. My name is {caller_name}, and I'm a {'new' if is_new_patient else 'returning'} patient.\n"
            f"Agent: Welcome {caller_name}. What symptoms or injury are you looking to be seen for today?\n"
            f"Caller: I need an appointment for my {body_part.lower()}, specifically for a {issue_type.lower()}.\n"
            f"Agent: {route_res.agent_speech}\n"
            f"Caller: That sounds perfect, let's book that.\n"
            f"Agent: Fantastic. Your appointment with {doc_name} at {loc_name} is confirmed for {time_str}. A confirmation text has been sent to {caller_phone}. Have a great day!"
        )

        log = CallLog(
            call_sid=f"SIM-{uuid.uuid4().hex[:8].upper()}",
            caller_phone=caller_phone,
            patient_id=patient.id,
            appointment_id=appt_id,
            status=status,
            transcript=transcript,
            summary=f"Simulated call for {caller_name}: {body_part} ({issue_type}) -> {doc_name} ({status})",
            detected_body_part=body_part,
            detected_issue_type=issue_type,
            duration_seconds=95,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        return jsonify({
            "success": True,
            "call_id": log.id,
            "status": status,
            "call": log.to_dict(),
        }), 201
    finally:
        db.close()
