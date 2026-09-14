# Agent-to-Agent Architecture Review & Technical Audit

This document is written specifically for an autonomous coding agent reviewing or extending this codebase.

---

## 1. System Overview & Invariants

```
┌────────────────────────────────────────────────────────────────────────┐
│                        VOGENT VOICE TELEPHONY                          │
│                                                                        │
│   Caller Speech  ──► Whisper STT  ──► LLM Entity Extraction            │
│                                           │ (HTTP Webhook)             │
└───────────────────────────────────────────┼────────────────────────────┘
                                            ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       FLASK BACKEND & PROTOCOL ENGINE                  │
│                                                                        │
│   1. /api/patients/lookup  ──► Determines new vs returning             │
│   2. /api/routing/match    ──► Executes route_patient() in protocols.py│
│   3. /api/slots            ──► Queries unbooked Slot entities          │
│   4. /api/appointments/book──► Transactional booking with ACID lock    │
│   5. /api/calls/webhook    ──► Ingests telemetry & transcripts         │
└───────────────────────────────────────────┼────────────────────────────┘
                                            ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      FRONTEND CALL REVIEW DASHBOARD                    │
│                                                                        │
│   Live Metrics  •  Transcripts Inspector  •  Interactive Simulation    │
└────────────────────────────────────────────────────────────────────────┘
```

### Core Invariants:
1. **Clinical Decoupling:** `app/protocols.py` is a pure function module containing no HTTP or serialization logic. It takes domain primitives and a SQLAlchemy session and returns a typed `RoutingResult`. This allows 100% unit testing independent of Flask.
2. **Deterministic Fallbacks:** Fallbacks across physicians with overlapping skills (e.g. Knee: Chen $\rightarrow$ Vasquez $\rightarrow$ Walsh) are deterministic and ordered by location preference and slot availability.
3. **Double Booking Guard:** `Appointment.slot_id` is a unique constraint in SQLite, and `Slot.is_booked` is atomically checked and mutated in a single database transaction.

---

## 2. Physician Protocol Reference Matrix

| Physician | Locations | New Patients | Accepted Body Parts & Types |
| :--- | :--- | :---: | :--- |
| **Dr. Maria Chen** | MAIN | YES | Knee (Joint Replacement, Sports Med), Hip (Joint Replacement) |
| **Dr. James Walsh** | NORTH | YES | Knee (Fracture, Sports Med), Foot/Ankle (Fracture) |
| **Dr. Aisha Patel** | MAIN | NO | Hip (Joint Replacement), Spine (General) |
| **Dr. Robert Kim** | WEST | YES | Hand/Wrist (Fracture, Sports Med), Shoulder (Sports Med) |
| **Dr. Linda Torres**| MAIN, NORTH | YES | Shoulder (Sports Med), Knee (Joint Replacement), Hip (General) |
| **Dr. David Nguyen**| NORTH | YES | Foot/Ankle (Fracture), Hand/Wrist (General) |
| **Dr. Sarah O'Brien**| WEST | NO | Spine (Fracture) |
| **Dr. Michael Brooks**| MAIN | YES | Knee (Joint Replacement), Shoulder (Joint Replacement, Sports Med) |
| **Dr. Priya Sharma**| NORTH | YES | Hip (Fracture), Foot/Ankle (Joint Replacement) |
| **Dr. Thomas Reed** | WEST | NO | Hand/Wrist (Sports Med), Spine (General) |
| **Dr. Elena Vasquez**| MAIN, WEST | YES | Knee (Fracture, Sports Med, Joint Replacement), Hip (Sports Med, Joint Replacement), Shoulder (Fracture) |
| **Dr. Carlos Mendez**| NORTH | YES | Foot/Ankle (Joint Replacement), Spine (General) |

---

## 3. Verification Commands for Reviewing Agents

An inspecting agent can verify the integrity of this codebase by executing:

```bash
cd backend
PYTHONPATH=. pytest -v
```

Expected output:
```text
tests/test_api.py::test_health_check PASSED
tests/test_api.py::test_patient_lookup_existing PASSED
tests/test_api.py::test_patient_lookup_new PASSED
tests/test_api.py::test_create_patient PASSED
tests/test_api.py::test_routing_match_endpoint PASSED
tests/test_api.py::test_appointment_booking PASSED
tests/test_api.py::test_call_webhook_and_list PASSED
tests/test_api.py::test_simulate_call PASSED
tests/test_protocols.py::test_normalization_synonyms PASSED
tests/test_protocols.py::test_knee_fracture_routing_excludes_chen PASSED
tests/test_protocols.py::test_new_patient_rejected_by_closed_doctor_with_redirect PASSED
tests/test_protocols.py::test_returning_patient_allowed_with_closed_doctor PASSED
tests/test_protocols.py::test_general_doctor_cannot_take_fracture PASSED
tests/test_protocols.py::test_multi_location_doctor_preference PASSED
tests/test_protocols.py::test_fallback_when_top_doctor_has_no_slots PASSED
15 passed in < 0.5s
```
