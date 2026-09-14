"""
Physician Protocol Matching and Routing Engine

This module implements the clinical routing rules defined in the Physician Protocols.
It deterministically matches patients to physicians based on:
1. Body part (Knee, Hip, Shoulder, Hand/Wrist, Foot/Ankle, Spine)
2. Issue type (Fracture, Joint Replacement, Sports Medicine, General)
3. New vs. Returning patient status (per-doctor restriction)
4. Location preferences (MAIN, NORTH, WEST)
5. Slot availability and fallback routing across overlapping physicians
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.models import Doctor, DoctorProtocol, Slot, Location

# Canonical definitions
VALID_LOCATIONS = {
    "MAIN": "Main Campus",
    "NORTH": "North Clinic",
    "WEST": "Westside Office",
}

VALID_BODY_PARTS = [
    "Knee",
    "Hip",
    "Shoulder",
    "Hand/Wrist",
    "Foot/Ankle",
    "Spine",
]

VALID_ISSUE_TYPES = [
    "Fracture",
    "Joint Replacement",
    "Sports Medicine",
    "General",
]

# Clinical synonyms mapping to ensure resilient voice caller parsing
SYNONYM_BODY_PARTS = {
    "knee": "Knee",
    "knees": "Knee",
    "patella": "Knee",
    "hip": "Hip",
    "hips": "Hip",
    "pelvis": "Hip",
    "shoulder": "Shoulder",
    "shoulders": "Shoulder",
    "rotator cuff": "Shoulder",
    "hand": "Hand/Wrist",
    "wrist": "Hand/Wrist",
    "hands": "Hand/Wrist",
    "wrists": "Hand/Wrist",
    "finger": "Hand/Wrist",
    "fingers": "Hand/Wrist",
    "carpal tunnel": "Hand/Wrist",
    "foot": "Foot/Ankle",
    "feet": "Foot/Ankle",
    "ankle": "Foot/Ankle",
    "ankles": "Foot/Ankle",
    "achilles": "Foot/Ankle",
    "toe": "Foot/Ankle",
    "spine": "Spine",
    "back": "Spine",
    "lower back": "Spine",
    "neck": "Spine",
    "lumbar": "Spine",
    "cervical": "Spine",
}

SYNONYM_ISSUE_TYPES = {
    "fracture": "Fracture",
    "broken": "Fracture",
    "break": "Fracture",
    "crack": "Fracture",
    "stress fracture": "Fracture",
    "joint replacement": "Joint Replacement",
    "replacement": "Joint Replacement",
    "arthroplasty": "Joint Replacement",
    "knee replacement": "Joint Replacement",
    "hip replacement": "Joint Replacement",
    "sports medicine": "Sports Medicine",
    "sports": "Sports Medicine",
    "sports injury": "Sports Medicine",
    "sprain": "Sports Medicine",
    "strain": "Sports Medicine",
    "torn ligament": "Sports Medicine",
    "acl": "Sports Medicine",
    "meniscus": "Sports Medicine",
    "runner's knee": "Sports Medicine",
    "general": "General",
    "pain": "General",
    "ache": "General",
    "consult": "General",
    "general consult": "General",
    "consultation": "General",
    "evaluation": "General",
    "arthritis": "General",
    "follow-up": "General",
    "follow up": "General",
}

def normalize_body_part(val: str) -> Optional[str]:
    if not val:
        return None
    val_clean = val.strip().lower()
    for syn, canonical in SYNONYM_BODY_PARTS.items():
        if syn in val_clean:
            return canonical
    return None

def normalize_issue_type(val: str) -> Optional[str]:
    if not val:
        return None
    val_clean = val.strip().lower()
    # Check compound terms first
    if "joint replacement" in val_clean or "replacement" in val_clean:
        return "Joint Replacement"
    if "sports" in val_clean or "acl" in val_clean or "sprain" in val_clean:
        return "Sports Medicine"
    if "fracture" in val_clean or "broken" in val_clean or "break" in val_clean:
        return "Fracture"
    if "general" in val_clean or "pain" in val_clean or "consult" in val_clean or "ache" in val_clean:
        return "General"
    return None

class RoutingResult:
    def __init__(
        self,
        success: bool,
        status_code: str,
        message: str,
        agent_speech: str,
        matched_doctor: Optional[Doctor] = None,
        available_slots: Optional[List[Slot]] = None,
        redirected_from_doctor: Optional[str] = None,
        redirect_reason: Optional[str] = None,
        alternative_doctors: Optional[List[Doctor]] = None,
    ):
        self.success = success
        self.status_code = status_code  # MATCH_FOUND, REDIRECTED_NEW_PATIENT, REDIRECTED_ISSUE, NO_SLOTS_FALLBACK, NO_MATCH
        self.message = message
        self.agent_speech = agent_speech
        self.matched_doctor = matched_doctor
        self.available_slots = available_slots or []
        self.redirected_from_doctor = redirected_from_doctor
        self.redirect_reason = redirect_reason
        self.alternative_doctors = alternative_doctors or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status_code": self.status_code,
            "message": self.message,
            "agent_speech": self.agent_speech,
            "matched_doctor": self.matched_doctor.to_dict() if self.matched_doctor else None,
            "available_slots": [s.to_dict() for s in self.available_slots],
            "redirected_from_doctor": self.redirected_from_doctor,
            "redirect_reason": self.redirect_reason,
            "alternative_doctors": [d.to_dict() for d in self.alternative_doctors],
        }

def route_patient(
    db: Session,
    body_part_raw: str,
    issue_type_raw: str,
    is_new_patient: bool,
    preferred_location_code: Optional[str] = None,
    preferred_doctor_name: Optional[str] = None,
    max_slots: int = 4,
) -> RoutingResult:
    """
    Core deterministic routing algorithm matching the Physician Protocol Specification.
    """
    body_part = normalize_body_part(body_part_raw) or body_part_raw
    issue_type = normalize_issue_type(issue_type_raw) or issue_type_raw

    if body_part not in VALID_BODY_PARTS:
        return RoutingResult(
            success=False,
            status_code="INVALID_BODY_PART",
            message=f"Body part '{body_part_raw}' is not supported.",
            agent_speech=f"I'm sorry, our clinic currently specializes in Knee, Hip, Shoulder, Hand and Wrist, Foot and Ankle, and Spine. Could you tell me if your injury involves one of these areas?",
        )

    if issue_type not in VALID_ISSUE_TYPES:
        return RoutingResult(
            success=False,
            status_code="INVALID_ISSUE_TYPE",
            message=f"Issue type '{issue_type_raw}' is not supported.",
            agent_speech=f"Could you specify what kind of visit you need? For example, is this for a recent fracture, a sports injury, a joint replacement evaluation, or a general consultation?",
        )

    # 1. Check if caller specifically asked for a preferred doctor
    redirected_doctor_name = None
    redirect_reason = None

    if preferred_doctor_name:
        requested_doc = db.query(Doctor).filter(Doctor.name.ilike(f"%{preferred_doctor_name.strip()}%")).first()
        if requested_doc:
            # Check if requested doctor handles this body part and issue type
            protocol = db.query(DoctorProtocol).filter(
                DoctorProtocol.doctor_id == requested_doc.id,
                DoctorProtocol.body_part == body_part,
                DoctorProtocol.accepted_type == issue_type,
            ).first()

            if not protocol:
                redirected_doctor_name = requested_doc.name
                # Check if doctor handles this body part for other reasons
                other_types = [
                    p.accepted_type
                    for p in db.query(DoctorProtocol).filter(
                        DoctorProtocol.doctor_id == requested_doc.id,
                        DoctorProtocol.body_part == body_part,
                    ).all()
                ]
                if other_types:
                    redirect_reason = f"{requested_doc.name} treats {body_part}, but only for {', '.join(other_types)}, not {issue_type}."
                else:
                    redirect_reason = f"{requested_doc.name} does not treat {body_part}."

            elif is_new_patient and not requested_doc.accepts_new_patients:
                redirected_doctor_name = requested_doc.name
                redirect_reason = f"{requested_doc.name} is currently only accepting returning patients for follow-ups and is closed to new patients."

    # 2. Query all doctors matching (body_part, issue_type)
    matching_protocols = db.query(DoctorProtocol).filter(
        DoctorProtocol.body_part == body_part,
        DoctorProtocol.accepted_type == issue_type,
    ).all()

    if not matching_protocols:
        return RoutingResult(
            success=False,
            status_code="NO_MATCH",
            message=f"No physician configured for {body_part} with issue type {issue_type}.",
            agent_speech=f"I checked our directory, but none of our orthopedic physicians currently handle {issue_type.lower()} appointments for {body_part.lower()}. Let me connect you with a care coordinator who can assist you further.",
        )

    eligible_doctor_ids = [p.doctor_id for p in matching_protocols]
    all_matching_docs = db.query(Doctor).filter(Doctor.id.in_(eligible_doctor_ids)).all()

    # 3. Filter by New Patient eligibility
    eligible_docs = []
    ineligible_new_patient_docs = []
    for doc in all_matching_docs:
        if is_new_patient and not doc.accepts_new_patients:
            ineligible_new_patient_docs.append(doc)
        else:
            eligible_docs.append(doc)

    if not eligible_docs:
        # All doctors who handle this issue are closed to new patients!
        ineligible_names = ", ".join([d.name for d in ineligible_new_patient_docs])
        return RoutingResult(
            success=False,
            status_code="ALL_DOCTORS_CLOSED_NEW_PATIENTS",
            message=f"Physicians treating {body_part} ({issue_type}) are closed to new patients: {ineligible_names}",
            agent_speech=f"Our specialists for {body_part} {issue_type} ({ineligible_names}) are currently closed to new patients and only seeing returning patients. Please hold while I transfer you to patient intake.",
            alternative_doctors=ineligible_new_patient_docs,
        )

    # 4. Sort eligible doctors:
    # Priority A: Matches preferred doctor (if valid)
    # Priority B: Matches preferred location
    # Priority C: Has available slots
    def score_doc(doc: Doctor) -> int:
        score = 0
        if preferred_doctor_name and preferred_doctor_name.lower() in doc.name.lower():
            score += 100
        if preferred_location_code and any(loc.code == preferred_location_code for loc in doc.locations):
            score += 50
        return score

    eligible_docs.sort(key=score_doc, reverse=True)

    # 5. Check slot availability with fallback across eligible doctors
    selected_doc = None
    selected_slots = []
    fallback_occurred = False
    original_top_doc = eligible_docs[0]

    for doc in eligible_docs:
        # Query open slots
        slot_query = db.query(Slot).filter(
            Slot.doctor_id == doc.id,
            Slot.is_booked == False,
        )
        if preferred_location_code:
            # Prefer slots at the preferred location if possible
            loc_slots = slot_query.filter(Slot.location_code == preferred_location_code).order_by(Slot.start_time).limit(max_slots).all()
            if loc_slots:
                selected_doc = doc
                selected_slots = loc_slots
                break

        # Fallback to any location for this doctor
        any_slots = slot_query.order_by(Slot.start_time).limit(max_slots).all()
        if any_slots:
            selected_doc = doc
            selected_slots = any_slots
            break

    # If first choice had no slots, but another did:
    if selected_doc and selected_doc.id != original_top_doc.id:
        fallback_occurred = True

    if not selected_doc or not selected_slots:
        # Eligible doctors found, but none have open slots in database
        selected_doc = original_top_doc
        return RoutingResult(
            success=False,
            status_code="NO_SLOTS_AVAILABLE",
            message=f"Physician {selected_doc.name} matches, but no open appointment slots were found.",
            agent_speech=f"{selected_doc.name} specializes in {body_part} {issue_type}, but unfortunately has no open appointments in the schedule right now. Would you like me to add you to the cancellation waitlist?",
            matched_doctor=selected_doc,
            alternative_docs=[d for d in eligible_docs if d.id != selected_doc.id],
        )

    # 6. Generate human-like, natural agent speech tailored to the clinical context
    doc_locations_str = " and ".join([loc.name for loc in selected_doc.locations])
    slot_options = [s.start_time.strftime("%A at %I:%M %p") for s in selected_slots[:2]]
    slot_options_str = " or ".join(slot_options)

    if redirected_doctor_name:
        status_code = "REDIRECTED_SUCCESS"
        agent_speech = (
            f"Regarding {redirected_doctor_name}: {redirect_reason} "
            f"However, I can schedule you with {selected_doc.name}, who specializes in {body_part} {issue_type} at our {selected_slots[0].location.name}. "
            f"The earliest openings are {slot_options_str}. Would either of those work for you?"
        )
    elif fallback_occurred:
        status_code = "FALLBACK_SUCCESS"
        agent_speech = (
            f"{original_top_doc.name} has no immediate openings, but {selected_doc.name} also specializes in {body_part} {issue_type} at our {selected_slots[0].location.name}. "
            f"I have openings on {slot_options_str}. Would you like one of those?"
        )
    else:
        status_code = "MATCH_FOUND"
        agent_speech = (
            f"I have matched you with {selected_doc.name} for your {body_part} {issue_type.lower()} at our {selected_slots[0].location.name}. "
            f"I have available times on {slot_options_str}. Would one of those work for you?"
        )

    return RoutingResult(
        success=True,
        status_code=status_code,
        message=f"Successfully routed to {selected_doc.name} at {selected_slots[0].location.name}",
        agent_speech=agent_speech,
        matched_doctor=selected_doc,
        available_slots=selected_slots,
        redirected_from_doctor=redirected_doctor_name,
        redirect_reason=redirect_reason,
        alternative_doctors=[d for d in eligible_docs if d.id != selected_doc.id],
    )
