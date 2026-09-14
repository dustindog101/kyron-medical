from flask import Blueprint, request, jsonify
from app.database import SessionLocal
from app.models import Patient

patients_bp = Blueprint("patients", __name__, url_prefix="/api/patients")

@patients_bp.route("/lookup", methods=["GET"])
def lookup_patient():
    """
    Lookup a patient by phone number, or by name and DOB.
    Returns whether the caller is a new or returning patient.
    """
    phone = request.args.get("phone")
    name = request.args.get("name")
    dob = request.args.get("dob")

    if not phone and not name:
        return jsonify({"error": "Either phone or name query parameter is required"}), 400

    db = SessionLocal()
    try:
        query = db.query(Patient)
        if phone:
            # Clean non-digit characters for robust lookup
            clean_phone = "".join(filter(str.isdigit, phone))
            # Match ends with last 10 digits
            query = query.filter(Patient.phone.like(f"%{clean_phone[-10:]}%"))
        elif name:
            query = query.filter(Patient.name.ilike(f"%{name.strip()}%"))
            if dob:
                query = query.filter(Patient.date_of_birth == dob.strip())

        patient = query.first()

        if patient:
            prior_appointments = [
                {
                    "doctor_name": appt.doctor.name,
                    "location_name": appt.location.name,
                    "body_part": appt.body_part,
                    "issue_type": appt.issue_type,
                    "status": appt.status,
                    "date": appt.created_at.strftime("%B %d, %Y") if appt.created_at else None,
                }
                for appt in patient.appointments
            ]

            return jsonify({
                "found": True,
                "is_new_patient": False if len(prior_appointments) > 0 else patient.is_new_patient,
                "patient": patient.to_dict(),
                "prior_appointments": prior_appointments,
                "message": f"Welcome back, {patient.name}. We found your existing patient chart.",
            }), 200
        else:
            return jsonify({
                "found": False,
                "is_new_patient": True,
                "patient": None,
                "message": "No existing record found for this caller. Triage as a new patient.",
            }), 200
    finally:
        db.close()

@patients_bp.route("", methods=["POST"])
def create_patient():
    """
    Create a new patient record.
    """
    data = request.get_json() or {}
    name = data.get("name")
    phone = data.get("phone")
    dob = data.get("date_of_birth")

    if not name or not phone:
        return jsonify({"error": "name and phone are required fields"}), 400

    db = SessionLocal()
    try:
        patient = Patient(
            name=name.strip(),
            phone=phone.strip(),
            date_of_birth=dob.strip() if dob else None,
            is_new_patient=data.get("is_new_patient", True),
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return jsonify({
            "success": True,
            "patient": patient.to_dict(),
            "message": "Patient created successfully.",
        }), 201
    finally:
        db.close()
