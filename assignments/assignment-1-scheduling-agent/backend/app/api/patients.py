from flask import Blueprint, request, jsonify
from app.database import SessionLocal
from app.models import Patient
import json as _json
import os as _os
import time as _time
import urllib.request as _urlopen_request

patients_bp = Blueprint("patients", __name__, url_prefix="/api/patients")

_VOGENT_API_KEY = _os.environ.get("VOGENT_API_KEY", "vogent_XGkutFBzQym2HXnlGQDcNo09j8H0cDJW")
_VOGENT_WORKSPACE_ID = _os.environ.get("VOGENT_WORKSPACE_ID", "6604a92d-1489-44dd-a38b-f14d978230cb")
_CLI_CACHE = {}
_CLI_TTL_SECONDS = 600
_OWN_NUMBERS_CACHE = {"numbers": set(), "at": 0.0}
_OWN_NUMBERS_TTL_SECONDS = 3600


def _own_workspace_numbers():
    """E.164 numbers owned by this workspace (cached 1h, TESTING skips).

    Vogent legs always carry a workspace number on one side
    (fromPhoneNumber), so it must never be mistaken for the caller.
    """
    now = _time.time()
    if now - _OWN_NUMBERS_CACHE["at"] < _OWN_NUMBERS_TTL_SECONDS:
        return _OWN_NUMBERS_CACHE["numbers"]
    numbers = set()
    try:
        from flask import current_app, has_app_context
        if has_app_context() and current_app.config.get("TESTING"):
            return numbers
    except Exception:
        pass
    if not _VOGENT_API_KEY:
        return numbers
    try:
        req = _urlopen_request.Request(
            "https://api.vogent.ai/api/phone_numbers?limit=100",
            headers={"Authorization": f"Bearer {_VOGENT_API_KEY}"},
            method="GET",
        )
        with _urlopen_request.urlopen(req, timeout=4) as resp:
            for entry in _json.loads(resp.read().decode()).get("data", []):
                if entry.get("number"):
                    numbers.add(entry["number"])
    except Exception as e:
        print(f"Warning: own-numbers fetch skipped: {e}")
    _OWN_NUMBERS_CACHE["numbers"] = numbers
    _OWN_NUMBERS_CACHE["at"] = now
    return numbers


def _is_placeholder_phone(phone):
    digits = "".join(filter(str.isdigit, str(phone or "")))
    return (
        not digits
        or digits in ("5550100000", "0000000000", "15550100000")
        or digits.endswith("5550100000")
    )


def resolve_cli_phone(dial_id):
    """Return the remote party's real phone number for a Vogent dial, or None.

    Every function call arrives with a dial_id wrapper. The network already
    knows the other side's number, so asking callers to read it out is only a
    fallback. Either leg side that is NOT one of our own workspace numbers is
    the remote party (outbound legs: toNumber; inbound: whichever side isn't
    ours). Results are cached per dial so lookup + create + telemetry on one
    call cost a single GraphQL roundtrip. Never raises; TESTING skips.
    """
    if not dial_id or not isinstance(dial_id, str) or dial_id.startswith("{{"):
        return None
    now = _time.time()
    hit = _CLI_CACHE.get(dial_id)
    if hit and now - hit[1] < _CLI_TTL_SECONDS:
        return hit[0]
    try:
        from flask import current_app, has_app_context
        if has_app_context() and current_app.config.get("TESTING"):
            return None
    except Exception:
        pass
    if not _VOGENT_API_KEY or not _VOGENT_WORKSPACE_ID:
        return None
    query = """
    query GetDials($workspaceId: ID!) {
      workspace(id: $workspaceId) {
        dials(offset: 0, limit: 30) {
          dials { id toNumber fromPhoneNumber { number } }
        }
      }
    }
    """
    try:
        payload = _json.dumps({"query": query, "variables": {"workspaceId": _VOGENT_WORKSPACE_ID}}).encode()
        req = _urlopen_request.Request(
            "https://api.vogent.ai/query",
            data=payload,
            headers={"Authorization": f"Bearer {_VOGENT_API_KEY}", "Content-Type": "application/json"},
            method="POST",
        )
        with _urlopen_request.urlopen(req, timeout=2.5) as resp:
            dials = _json.loads(resp.read().decode()).get("data", {}).get("workspace", {}).get("dials", {}).get("dials", [])
        dial = next((d for d in dials if d.get("id") == dial_id), None)
        if not dial:
            return None
        own = _own_workspace_numbers()
        candidates = [
            (dial.get("fromPhoneNumber") or {}).get("number"),
            dial.get("toNumber"),
        ]
        for number in candidates:
            if number and number not in own and not _is_placeholder_phone(number):
                _CLI_CACHE[dial_id] = (number, now)
                return number
    except Exception as e:
        print(f"Warning: CLI resolve skipped for {dial_id}: {e}")
    return None

@patients_bp.route("/lookup", methods=["GET", "POST"])
def lookup_patient():
    """
    Lookup a patient by phone number, or by name and DOB.
    Accepts both GET query params and POST JSON body (for Vogent API functions).
    Returns whether the caller is a new or returning patient.
    """
    raw_data = request.get_json(silent=True) or {}
    data = raw_data.get("params") if isinstance(raw_data.get("params"), dict) else raw_data

    if request.method == "POST":
        phone = data.get("phone") or request.args.get("phone")
        name = data.get("name") or request.args.get("name")
        dob = data.get("dob") or data.get("date_of_birth") or request.args.get("dob")
    else:
        phone = request.args.get("phone")
        name = request.args.get("name")
        dob = request.args.get("dob") or request.args.get("date_of_birth")

    # Prefer the network caller CLI over anything spoken: the dial_id wrapper
    # identifies the live call, and the CLI needs no transcription. The spoken
    # name remains as fallback (and as the identity-confirm source).
    dial_id = raw_data.get("dial_id") or data.get("dial_id")
    phone_source = "provided"
    if not phone or _is_placeholder_phone(phone):
        cli = resolve_cli_phone(dial_id)
        if cli:
            phone = cli
            phone_source = "cli"

    if not phone and not name:
        return jsonify({
            "found": False,
            "is_new_patient": True,
            "patient_status": "new",
            "patient": {"id": 0, "name": "", "phone": ""},
            "prior_appointments": [],
            "message": "No identifying phone or name provided. Triage as a new patient.",
        }), 200

    db = SessionLocal()
    try:
        query = db.query(Patient)

        def _escape_like(s):
            return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

        clean_phone = "".join(filter(str.isdigit, str(phone))) if phone else ""
        is_placeholder = _is_placeholder_phone(phone)

        if clean_phone and not is_placeholder and len(clean_phone) >= 7:
            query = query.filter(Patient.phone.like(f"%{clean_phone[-10:]}%"))
        elif name:
            clean_name = str(name).strip().rstrip(".,!?")
            query = query.filter(Patient.name.ilike(f"%{_escape_like(clean_name)}%", escape="\\"))
            if dob:
                query = query.filter(Patient.date_of_birth == str(dob).strip())
        else:
            return jsonify({
                "found": False,
                "is_new_patient": True,
                "patient_status": "new",
                "patient": {"id": 0, "name": "", "phone": ""},
                "prior_appointments": [],
                "message": "Web caller without distinct phone or name. Triage as a new patient.",
            }), 200

        patient = query.first()

        if patient:
            prior_appointments = [
                {
                    "doctor_name": appt.doctor.name if appt.doctor else "Unknown",
                    "location_name": appt.location.name if appt.location else (appt.location_code or "Main Campus"),
                    "body_part": appt.body_part,
                    "issue_type": appt.issue_type,
                    "status": appt.status,
                    "date": appt.created_at.strftime("%B %d, %Y") if appt.created_at else None,
                }
                for appt in patient.appointments
            ]

            # A chart on file means a returning caller — even with zero
            # prior appointments and a stale is_new_patient row flag (live
            # dial: Alex Tuck's chart existed but triaged "new", so the
            # flow re-asked for a name and created a duplicate chart).
            # New-vs-returning routing eligibility keys off this gate.
            return jsonify({
                "found": True,
                "is_new_patient": False,
                "patient_status": "returning",
                "phone_source": phone_source,
                "patient": patient.to_dict(),
                "prior_appointments": prior_appointments,
                "message": f"Welcome back, {patient.name}. We found your existing patient chart.",
            }), 200
        else:
            return jsonify({
                "found": False,
                "is_new_patient": True,
                "patient_status": "new",
                "phone_source": phone_source,
                "patient": {"id": 0, "name": "", "phone": ""},
                "prior_appointments": [],
                "message": "No existing record found for this caller. Triage as a new patient.",
            }), 200
    finally:
        db.close()

@patients_bp.route("", methods=["POST"])
def create_patient():
    """
    Create a new patient record.
    """
    raw_data = request.get_json(silent=True) or {}
    data = raw_data.get("params") if isinstance(raw_data.get("params"), dict) else raw_data

    name_raw = data.get("name")
    name = name_raw.strip().rstrip(".,!?") if isinstance(name_raw, str) else ""
    if not name or name.startswith("{{"):
        return jsonify({
            "success": False,
            "patient": None,
            "message": "A caller name is required to create a chart.",
            "duplicate": False,
        }), 400
    phone = str(data.get("phone") or "+15550100000").strip()
    if _is_placeholder_phone(phone):
        # A new caller on their own mobile should own their real CLI on the
        # chart (future calls then recognize them with no questions). The
        # flow passes no phone here, so resolve it from the live dial.
        cli = resolve_cli_phone(raw_data.get("dial_id") or data.get("dial_id"))
        if cli:
            phone = cli
    dob = data.get("date_of_birth") or data.get("dob")
    is_new_raw = data.get("is_new_patient", True)
    if isinstance(is_new_raw, str):
        is_new_patient = is_new_raw.strip().lower() in ("true", "1", "yes", "new")
    else:
        is_new_patient = bool(is_new_raw)

    db = SessionLocal()
    try:
        clean_phone = "".join(filter(str.isdigit, str(phone)))
        is_placeholder = clean_phone in ("5550100000", "0000000000", "15550100000") or clean_phone.endswith("5550100000")

        if not is_placeholder and len(clean_phone) >= 7:
            existing = db.query(Patient).filter(
                Patient.phone.like(f"%{clean_phone[-10:]}%")
            ).first()
        else:
            existing = db.query(Patient).filter(
                Patient.name.ilike(name)
            ).first()

        if existing:
            return jsonify({
                "success": True,
                "patient": existing.to_dict(),
                "patient_status": "returning" if not existing.is_new_patient else "new",
                "message": "Patient already exists — returning existing record.",
                "duplicate": True,
            }), 200

        patient = Patient(
            name=name,
            phone=phone,
            date_of_birth=str(dob).strip() if dob and not str(dob).strip().startswith("{{") else None,
            is_new_patient=is_new_patient,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return jsonify({
            "success": True,
            "patient": patient.to_dict(),
            "patient_status": "returning" if not patient.is_new_patient else "new",
            "message": "Patient created successfully.",
            "duplicate": False,
        }), 201
    finally:
        db.close()
