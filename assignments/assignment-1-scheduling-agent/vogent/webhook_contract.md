# Vogent Voice Agent Webhook & Tool Contracts

This document outlines the API endpoints that the **Vogent** flow-based voice agent calls during a phone conversation.

Base URL in Production: `http://<EC2-IP>:5000` (or `https://<DOMAIN>`)

---

## 1. Patient Lookup & Triage

* **Endpoint:** `GET /api/patients/lookup`
* **Purpose:** Determine if caller is an existing patient or new patient.
* **When called:** After greeting, when caller provides their phone number or full name.

### Request
```http
GET /api/patients/lookup?phone=+14155550111
```

### Response (Existing Patient Found)
```json
{
  "found": true,
  "is_new_patient": false,
  "message": "Welcome back, Alice Johnson. We found your existing patient chart.",
  "patient": {
    "id": 1,
    "name": "Alice Johnson",
    "phone": "+14155550111",
    "is_new_patient": false
  },
  "prior_appointments": [
    {
      "doctor_name": "Dr. Aisha Patel",
      "location_name": "Main Campus",
      "body_part": "Spine",
      "issue_type": "General",
      "status": "COMPLETED",
      "date": "July 30, 2026"
    }
  ]
}
```

### Response (New Patient)
```json
{
  "found": false,
  "is_new_patient": true,
  "patient": null,
  "message": "No existing record found for this caller. Triage as a new patient."
}
```

---

## 2. Physician Protocol & Slot Match

* **Endpoint:** `POST /api/routing/match`
* **Purpose:** Primary routing engine matching patient injury/complaint against doctor protocols.
* **When called:** When caller states reason for visit (body part + issue type).

### Request
```json
{
  "body_part": "Knee",
  "issue_type": "Fracture",
  "is_new_patient": true,
  "preferred_location": "NORTH",
  "preferred_doctor": null
}
```

### Response (Successful Match)
```json
{
  "success": true,
  "status_code": "MATCH_FOUND",
  "message": "Successfully routed to Dr. James Walsh at North Clinic",
  "agent_speech": "I have matched you with Dr. James Walsh for your Knee fracture at our North Clinic. I have available times on Tuesday at 09:00 AM or Tuesday at 10:00 AM. Would one of those work for you?",
  "matched_doctor": {
    "id": 2,
    "name": "Dr. James Walsh",
    "accepts_new_patients": true,
    "locations": [{"code": "NORTH", "name": "North Clinic"}]
  },
  "available_slots": [
    {
      "id": 15,
      "doctor_name": "Dr. James Walsh",
      "location_code": "NORTH",
      "location_name": "North Clinic",
      "formatted_time": "Tuesday, September 15 at 09:00 AM",
      "start_time": "2026-09-15T09:00:00"
    }
  ],
  "redirected_from_doctor": null,
  "redirect_reason": null
}
```

### Response (Redirection - e.g. New Patient asks for Dr. Aisha Patel)
```json
{
  "success": true,
  "status_code": "REDIRECTED_SUCCESS",
  "message": "Successfully routed to Dr. Maria Chen at Main Campus",
  "agent_speech": "Regarding Dr. Aisha Patel: Dr. Aisha Patel is currently only accepting returning patients for follow-ups and is closed to new patients. However, I can schedule you with Dr. Maria Chen, who specializes in Hip Joint Replacement at our Main Campus. The earliest openings are Tuesday at 10:00 AM or Tuesday at 11:00 AM. Would either of those work for you?",
  "matched_doctor": {
    "id": 1,
    "name": "Dr. Maria Chen",
    "accepts_new_patients": true
  },
  "redirected_from_doctor": "Dr. Aisha Patel",
  "redirect_reason": "Dr. Aisha Patel is currently only accepting returning patients for follow-ups and is closed to new patients."
}
```

---

## 3. Appointment Booking

* **Endpoint:** `POST /api/appointments/book`
* **Purpose:** Locks the slot and confirms the appointment.
* **When called:** When caller accepts one of the offered time slots.

### Request
```json
{
  "patient_id": 1,
  "slot_id": 15,
  "body_part": "Knee",
  "issue_type": "Fracture",
  "notes": "Patient fell from ladder; suspected hairline knee fracture"
}
```

### Response
```json
{
  "success": true,
  "confirmation_speech": "You are all set! Your appointment with Dr. James Walsh is confirmed for Tuesday, September 15 at 09:00 AM at our North Clinic. We have sent a confirmation text with directions to your phone number. Thank you for calling Kyron Medical, and take care!",
  "appointment": {
    "id": 5,
    "doctor_name": "Dr. James Walsh",
    "location_name": "North Clinic",
    "formatted_time": "Tuesday, September 15 at 09:00 AM",
    "status": "SCHEDULED"
  }
}
```

---

## 4. Call Completion Webhook

* **Endpoint:** `POST /api/calls/webhook`
* **Purpose:** Ingests the full call transcript, audio metadata, and outcome for dashboard review.
* **When called:** Triggered on call termination / hangup.

### Request
```json
{
  "call_sid": "VOG-982341",
  "caller_phone": "+14155550222",
  "patient_id": 1,
  "appointment_id": 5,
  "status": "SCHEDULED",
  "transcript": "Agent: Thank you for calling...\nCaller: Hi...",
  "summary": "Patient booked Knee Fracture with Dr. Walsh.",
  "detected_body_part": "Knee",
  "detected_issue_type": "Fracture",
  "duration_seconds": 124
}
```
