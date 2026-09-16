"""Doctor/specialty lookup for informational caller questions.

PDF work-trial invitation (Flask backend section): "Anything else you find
you need to support the flow cleanly (e.g. doctor/specialty lookup ...)".

This endpoint answers "Which physicians do you have?" / "Which clinics can
I go to?" AFTER triage (body_part + issue_type known) without booking
anything. It reuses the same normalization, preference-inference, and
per-doctor/per-body-part eligibility rules as the booking path
(`route_patient`), so the spoken list can never disagree with what
`/routing/match` would offer.

Voice transport contract (matches every other endpoint):
- Accepts Vogent's {"params": {...}} wrapper and flat JSON.
- Never returns an HTTP error for a voice-level failure: always HTTP 200
  with success:false plus speakable agent_speech (an HTML error page is
  what the agent once hallucinated fake confirmations over).
- Drops unresolved {{...}} templates and null-ish placeholders instead of
  persisting them.
"""

from flask import Blueprint, request, jsonify
from sqlalchemy import func
from app.database import SessionLocal
from app.models import Doctor, DoctorProtocol, Slot
from app.protocols import (
    VALID_BODY_PARTS,
    VALID_ISSUE_TYPES,
    VALID_LOCATIONS,
    clean_preference_text,
    infer_preferences_from_text,
    normalize_body_part,
    normalize_issue_type,
    normalize_location_code,
)

providers_bp = Blueprint("providers", __name__, url_prefix="/api/providers")


def _coerce_is_new(raw):
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("{{"):
            return True
        return s.lower() in ("true", "1", "yes", "new", "new patient")
    if raw is None:
        return True
    return bool(raw)


def _clean_field(val):
    if val is None:
        return None
    if not isinstance(val, str):
        return str(val)
    s = val.strip()
    if not s or s.startswith("{{"):
        return None
    if s.lower().rstrip(".") in ("null", "none", "no", "n/a", "na", "no preference"):
        return None
    return s.rstrip(".").strip() or None


def _doctor_payload(doc, open_slot_count):
    return {
        "id": doc.id,
        "name": doc.name,
        "accepts_new_patients": doc.accepts_new_patients,
        "locations": [loc.to_dict() for loc in doc.locations],
        "open_slot_count": open_slot_count,
    }


def _speech_for(doctors_with_counts, body_part, issue_type, location_code=None):
    """Verbatim-ready enumeration. TTS-safe: names + clinic names only."""
    parts = []
    for doc, count in doctors_with_counts:
        loc_names = " and ".join(loc.name for loc in doc.locations)
        if location_code:
            loc_names = next(
                (loc.name for loc in doc.locations if loc.code == location_code),
                loc_names,
            )
        avail = "with open appointments" if count else "currently fully booked"
        parts.append(f"{doc.name} at our {loc_names} ({avail})")
    loc_hint = ""
    if location_code and location_code in VALID_LOCATIONS:
        loc_hint = f" near {VALID_LOCATIONS[location_code]}"
    return (
        f"For {body_part.lower()} {issue_type.lower()}{loc_hint}, "
        f"you can see: {'; '.join(parts)}."
    )


@providers_bp.route("/list", methods=["GET", "POST"])
def list_providers():
    if request.method == "POST":
        raw = request.get_json(silent=True) or {}
        data = raw.get("params") if isinstance(raw.get("params"), dict) else raw
    else:
        data = request.args.to_dict()

    body_raw = _clean_field(data.get("body_part"))
    issue_raw = _clean_field(data.get("issue_type"))
    is_new = _coerce_is_new(data.get("is_new_patient", True))
    loc_raw = clean_preference_text(data.get("preferred_location") or data.get("location_code"))
    doc_raw = clean_preference_text(data.get("preferred_doctor"))

    if not body_raw or not issue_raw:
        return jsonify({
            "success": False,
            "status_code": "MISSING_INPUTS",
            "agent_speech": (
                "To list the right specialists I need to know which area of "
                "your body hurts and what kind of visit you need — for "
                "example, knee pain from a sports injury."
            ),
            "message": "body_part and issue_type are required",
            "providers": [],
            "alternative_doctors": [],
        }), 200

    db = SessionLocal()
    try:
        inferred_loc, inferred_doc = infer_preferences_from_text(
            db, loc_raw, doc_raw, body_raw, issue_raw
        )
        location_code = normalize_location_code(loc_raw) or inferred_loc
        if location_code not in VALID_LOCATIONS:
            location_code = None

        body_part = normalize_body_part(body_raw) or body_raw
        issue_type = normalize_issue_type(issue_raw) or issue_raw

        if body_part not in VALID_BODY_PARTS:
            return jsonify({
                "success": False,
                "status_code": "INVALID_BODY_PART",
                "agent_speech": (
                    "Our clinic specializes in Knee, Hip, Shoulder, Hand and "
                    "Wrist, Foot and Ankle, and Spine. Could you tell me if "
                    "your injury involves one of these areas?"
                ),
                "message": f"Body part '{body_raw}' is not supported.",
                "providers": [],
                "alternative_doctors": [],
            }), 200

        if issue_type not in VALID_ISSUE_TYPES:
            return jsonify({
                "success": False,
                "status_code": "INVALID_ISSUE_TYPE",
                "agent_speech": (
                    "Could you specify what kind of visit you need? For "
                    "example, is this for a recent fracture, a sports injury, "
                    "a joint replacement evaluation, or a general consultation?"
                ),
                "message": f"Issue type '{issue_raw}' is not supported.",
                "providers": [],
                "alternative_doctors": [],
            }), 200

        protocols = db.query(DoctorProtocol).filter(
            DoctorProtocol.body_part == body_part,
            DoctorProtocol.accepted_type == issue_type,
        ).all()

        if not protocols:
            # Same-body-part alternatives (different issue types) so the
            # agent redirects to an appropriate alternative per the PDF
            # instead of blind-transferring. e.g. Spine + Sports Medicine
            # -> Spine General (Patel/Reed/Mendez) + Spine Fracture (O'Brien).
            alt_protocols = db.query(DoctorProtocol).filter(
                DoctorProtocol.body_part == body_part
            ).all()
            alt_docs = {}
            for p in alt_protocols:
                doc = db.query(Doctor).filter(Doctor.id == p.doctor_id).first()
                if not doc or doc.id in alt_docs:
                    continue
                if is_new and not doc.accepts_new_patients:
                    continue
                alt_docs[doc.id] = (doc, p.accepted_type)
            if not alt_docs:
                return jsonify({
                    "success": False,
                    "status_code": "NO_MATCH",
                    "agent_speech": (
                        f"I checked our directory, but none of our physicians "
                        f"currently handle {issue_type.lower()} appointments "
                        f"for {body_part.lower()}. Let me connect you with a "
                        f"care coordinator who can assist you further."
                    ),
                    "message": f"No physician configured for {body_part} / {issue_type}.",
                    "providers": [],
                    "alternative_doctors": [],
                }), 200
            alt_list = sorted(alt_docs.values(), key=lambda t: t[0].name)
            alt_speech = "; ".join(
                f"{doc.name} for {acc.lower()} at "
                f"{' and '.join(loc.name for loc in doc.locations)}"
                for doc, acc in alt_list
            )
            return jsonify({
                "success": False,
                "status_code": "NO_MATCH",
                "agent_speech": (
                    f"None of our physicians handle {issue_type.lower()} for "
                    f"{body_part.lower()}, but for {body_part.lower()} you "
                    f"can see: {alt_speech}."
                ),
                "message": f"No physician configured for {body_part} / {issue_type}; alternatives offered.",
                "providers": [],
                "alternative_doctors": [
                    {"id": d.id, "name": d.name,
                     "locations": [loc.to_dict() for loc in d.locations],
                     "accepts_new_patients": d.accepts_new_patients,
                     "accepted_type": acc}
                    for d, acc in alt_list
                ],
            }), 200

        doctor_ids = [p.doctor_id for p in protocols]
        docs = db.query(Doctor).filter(Doctor.id.in_(doctor_ids)).all()
        eligible = [d for d in docs if not (is_new and not d.accepts_new_patients)]
        if not eligible:
            names = ", ".join(sorted(d.name for d in docs))
            return jsonify({
                "success": False,
                "status_code": "ALL_DOCTORS_CLOSED_NEW_PATIENTS",
                "agent_speech": (
                    f"Our specialists for {body_part.lower()} "
                    f"{issue_type.lower()} ({names}) are currently closed to "
                    f"new patients and only seeing returning patients. Please "
                    f"hold while I transfer you to patient intake."
                ),
                "message": f"All {body_part}/{issue_type} physicians closed to new patients.",
                "providers": [],
                "alternative_doctors": [
                    {"id": d.id, "name": d.name,
                     "locations": [loc.to_dict() for loc in d.locations],
                     "accepts_new_patients": d.accepts_new_patients}
                    for d in docs
                ],
            }), 200

        def _sort_key(doc):
            score = 0
            if doc_raw and doc_raw.lower() in doc.name.lower():
                score += 100
            if location_code and any(loc.code == location_code for loc in doc.locations):
                score += 50
            return (-score, doc.name)

        eligible.sort(key=_sort_key)

        counts = dict(
            db.query(Slot.doctor_id, func.count(Slot.id))
            .filter(Slot.is_booked == False)  # noqa: E712
            .filter(Slot.doctor_id.in_([d.id for d in eligible]))
            .group_by(Slot.doctor_id)
            .all()
        )
        with_counts = [(d, counts.get(d.id, 0)) for d in eligible]
        # Prefer doctors with real availability, keep name order as tiebreak.
        with_counts.sort(key=lambda t: (-t[1], t[0].name))

        if location_code:
            with_counts = [
                t for t in with_counts
                if any(loc.code == location_code for loc in t[0].locations)
            ] or with_counts

        return jsonify({
            "success": True,
            "status_code": "PROVIDERS_FOUND",
            "agent_speech": _speech_for(with_counts, body_part, issue_type, location_code),
            "message": f"Found {len(with_counts)} physicians for {body_part}/{issue_type}.",
            "providers": [_doctor_payload(d, c) for d, c in with_counts],
            "alternative_doctors": [],
        }), 200
    finally:
        db.close()
