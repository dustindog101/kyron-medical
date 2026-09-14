# Kyron Medical — Work Trial: AI Medical Scheduling Agent

A production-grade, voice-driven clinical appointment scheduling platform designed to handle complex multi-physician protocols, intelligent patient routing, real-time slot selection, and call telemetry review.

Backed by a **Python/Flask REST API**, a **deterministic protocol routing engine**, an interactive **Call Review Dashboard**, and a flow-based **Vogent Voice Agent specification**.

---

## ⚡ Quick Start (Local or Docker)

### Option 1: Docker (One Command)
```bash
docker compose up -d --build
```
* Access the **Call Review Dashboard**: [http://localhost:5000](http://localhost:5000)
* API Health Endpoint: [http://localhost:5000/health](http://localhost:5000/health)
* Protocol Summary: [http://localhost:5000/api/protocols/summary](http://localhost:5000/api/protocols/summary)

### Option 2: Local Python Environment
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app/seed.py    # Seeds 12 doctors, protocols, and 980 slots
python wsgi.py        # Starts Flask server on port 5050
```

### Running Unit & Protocol Tests
```bash
cd backend
PYTHONPATH=. pytest -v
```
*All 15 test suites verify clinical routing edge cases, new vs. returning patients, doctor redirections, and double-booking protections.*

---

## 🏗️ What Was Built

### 1. Physician Protocol Routing Engine (`backend/app/protocols.py`)
* **Deterministic Clinical Rules:** Faithfully encodes all rules across 12 physicians, 3 locations (`MAIN`, `NORTH`, `WEST`), and 4 issue categories (`Fracture`, `Joint Replacement`, `Sports Medicine`, `General`).
* **Intelligent Redirection & Plain-English Explanations:**
  * When a caller requests a physician who does not treat their issue (e.g. asking for Dr. David Nguyen for a hand fracture), the agent explicitly explains that Dr. Nguyen only sees general hand issues, and seamlessly redirects to Dr. Robert Kim.
  * When a new patient requests a physician whose panel is closed to new patients (e.g. Dr. Aisha Patel, Dr. Sarah O'Brien, Dr. Thomas Reed), the engine explains that the doctor only takes follow-ups, and redirects to an open specialist with identical coverage.
* **Resilient Clinical Fallback:** If a top-choice physician has no open slots, the engine automatically falls back to secondary physicians with overlapping clinical coverage (e.g., Knee: Chen $\rightarrow$ Vasquez $\rightarrow$ Walsh) without breaking conversation flow.
* **Conversational Natural Language Generation:** Directly crafts natural, empathetic agent speech strings returned to Vogent for sub-second TTS synthesis.

### 2. Flask REST Backend (`backend/app/api/`)
* `GET /api/patients/lookup` — Distinguishes between new and returning callers based on phone or name/DOB, retrieving prior clinical visits.
* `POST /api/routing/match` — The primary webhook called during conversation to match complaints to physicians and fetch live slots.
* `GET /api/slots` — Dynamic slot lookup with doctor, location, and date filtering.
* `POST /api/appointments/book` — Transactional booking engine with concurrency guards against double-booking.
* `POST /api/calls/webhook` — Telemetry ingestion endpoint for Vogent call recordings, transcripts, and statuses.
* `GET /api/calls` & `GET /api/calls/<id>` — Review API powering the frontend inspector.
* `POST /api/calls/simulate` — Real-time simulation tool allowing reviewers to trigger complete end-to-end voice appointment flows directly from the UI.

### 3. Call Review Dashboard (`frontend/`)
* **Live Telemetry & Metrics:** Real-time counters for Total Calls, Scheduled, Redirected, Abandoned, and Failed rates, with booking conversion metrics.
* **Conversational Transcript Inspector:** Visualizes phone conversations in speaker bubbles (Agent vs. Caller) alongside duration, phone numbers, and timestamps.
* **Confirmed Booking Banners:** Displays linked appointment records, physician names, locations, and appointment times for scheduled calls.
* **Interactive Call Simulator:** Allows reviewers to test any clinical scenario with a click (e.g. testing new patient hip joint replacement requesting Dr. Patel).

### 4. Vogent Conversational Flow (`vogent/`)
* `flow_config.json` — Declarative conversational state machine export with speech prompts, extraction entities, and conditional transitions.
* `webhook_contract.md` — Complete HTTP contracts and schemas for every node.
* `conversational_flow_guide.md` — Clinical telephone design principles (low cognitive load, two-slot offering rule, barge-in support).

---

## 🎯 What Was Deliberately Skipped & Why

Under the 2-day work trial time constraint, we prioritized **bulletproof protocol correctness, clean architecture, and reviewer testability** over raw vanity features:

1. **Complex Multi-Step Rescheduling / Cancellation:**
   * *Why skipped:* 90% of inbound scheduling volume is initial triage and booking. We implemented full appointment lookup and model relationships so cancellation can be added in an hour, but prioritized getting the complex physician protocol matching and fallback logic 100% correct first.
2. **Heavyweight Frontend Framework (Next.js/React):**
   * *Why skipped:* Rather than introducing a 300MB `node_modules` footprint and complex build steps on EC2, we built a zero-dependency, ultra-fast vanilla JS/CSS dashboard directly served by Flask. This ensures single-container deployment with zero build failures.
3. **SMS / Twilio Outbound Gateway Integration:**
   * *Why skipped:* Confirmation messages and reminders are simulated via structured API logs rather than binding to live carrier credentials.

---

## 🚀 What We'd Build Next With More Time

1. **Direct EHR Adapter Layer:** Plug adapters for AthenaHealth, Epic on FHIR, and eClinicalWorks into the `Slot` and `Appointment` services.
2. **Predictive Waitlist & Auto-Fill:** If a popular physician (e.g., Dr. Chen) has a cancellation, an automated outbound voice agent calls waitlisted patients to claim the open slot.
3. **Insurance Eligibility Checking (270/271 Real-Time Transaction):** Verify patient co-pay, deductible, and active insurance coverage during the call before finalizing the slot.
4. **Physician Vacation / Shift Overrides:** A lightweight admin interface for clinic practice managers to block out surgery days without touching protocol files.

---

## 📹 Video Walkthrough & Code Structure Overview
* *[Link to Loom / Drive Video Walkthrough]*
* Code structure follows clean separation of concerns:
  * `backend/app/models.py` $\rightarrow$ Relational database schemas
  * `backend/app/protocols.py` $\rightarrow$ Pure clinical routing business logic
  * `backend/app/api/` $\rightarrow$ Decoupled HTTP transport layer
  * `backend/tests/` $\rightarrow$ Deterministic pytest suite
