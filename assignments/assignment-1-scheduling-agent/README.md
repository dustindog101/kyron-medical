# Kyron Medical — Work Trial: AI Medical Scheduling Agent

A voice-driven clinical appointment scheduling platform: a flow-based **Vogent voice agent** triages callers (new vs. returning, body part, issue type), a deterministic **physician-protocol routing engine** matches them to the right doctor and live slots, a **Flask REST API** backs every step of the call, and a **call-review dashboard** shows transcripts, booking status, and confirmed appointments.

Live deployment: `https://54-90-91-169.sslip.io` (dashboard + API) on AWS EC2 via Docker. Inbound test line: **+1 (301) 560-1855** (Vogent number linked to the Medical Scheduler Agent, v5.6 flow).

---

## ⚡ Quick Start (Local or Docker)

### Option 1: Docker (One Command)
```bash
docker compose up -d --build
```
* **Call Review Dashboard**: [http://localhost:5000](http://localhost:5000)
* API Health: [http://localhost:5000/health](http://localhost:5000/health)
* Protocol Summary: [http://localhost:5000/api/protocols/summary](http://localhost:5000/api/protocols/summary)

### Option 2: Local Python Environment
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app/seed.py    # Seeds 12 doctors, protocols, and ~980 slots
python wsgi.py        # Starts Flask server on port 5050
```

### Running Unit & Protocol Tests
```bash
cd backend
PYTHONPATH=. pytest -v
```
21 tests covering clinical routing edge cases, new vs. returning patients, doctor redirections, double-booking protection (asserting the speakable-failure contract), missing-input and template-literal rejection, Vogent payload shapes (nested `params`, string booleans/ids, list transcripts), second-slot time matching, and follow-up normalization.

---

## 🏗️ What Was Built

### 1. Physician Protocol Routing Engine (`backend/app/protocols.py`)
Deterministic rules over 12 physicians, 3 locations (`MAIN`, `NORTH`, `WEST`), and 4 issue types (`Fracture`, `Joint Replacement`, `Sports Medicine`, `General`):
* **Per-doctor, per-body-part matching** — a doctor is matched only for the exact (body part, issue type) pairs in their protocol, never just "treats knees."
* **`General` is general-only** — fracture/joint-replacement/sports callers are never routed to a `General` entry for that body part.
* **New-patient panels** — closed-panel doctors (Patel, O'Brien, Reed) explain themselves in plain language and redirect to an open peer (e.g. new Hip Joint Replacement asking for Patel → Chen).
* **Slot-aware fallback** — if the top match has no open slots, the engine falls through overlapping doctors (e.g. Knee: Chen → Vasquez → Walsh) without breaking the call.
* **Synonym-tolerant normalization** — "follow-up" → General, "sprain/ACL" → Sports Medicine, "broken" → Fracture, "back/neck" → Spine — so freeform voice answers resolve to canonical protocol terms.
* Every match returns `agent_speech` the voice agent speaks **verbatim**, so redirect explanations stay empathetic and consistent.

### 2. Flask REST Backend (`backend/app/api/`)
All Vogent API functions are POST-only and send `{"params": {...}}` wrappers with string-typed values — every endpoint unwraps and coerces defensively:

| Endpoint | Purpose |
| :--- | :--- |
| `POST /api/patients/lookup` | Phone-first lookup (placeholder numbers ignored), name/`ilike` fallback, DOB tiebreak. Returns `found`, `is_new_patient`, chart, prior visits. |
| `POST /api/patients` | Duplicate-safe creation (placeholder numbers dedupe by name). Returns existing record with `duplicate: true`. |
| `POST /api/routing/match` | Protocol match + live slots + verbatim speech. Cleans `"No."`/`"null"`/template placeholders; infers location/doctor mentions from freeform text. |
| `GET/POST /api/slots` | Open-slot listing by doctor/location. |
| `POST /api/appointments/book` | Re-runs the routing engine when no usable `slot_id` arrives, matches the caller's quoted time ("Thursday at 11" books the 11, not the 10), guards double-booking. Missing inputs, unknown charts, taken slots, and empty schedules all return **HTTP 200 with `success:false` plus speakable `agent_speech`/`confirmation_speech`** — never an HTTP error (an error page is what the voice agent hallucinated fake confirmations over). Links the booking to the dial's call log; **never fabricates transcripts**. |
| `POST /api/calls/webhook` | End-of-call telemetry. Accepts string **or list** transcripts, drops unresolved `{{...}}` templates instead of crashing, resolves placeholder phones from the chart, defaults unknown outcomes to `FAILED`. |
| `GET /api/calls`, `GET /api/calls/<id>` | Dashboard review API with status metrics. |
| `POST /api/calls/sync` | Reconciles Vogent dial history (GraphQL) into the dashboard. Flow-reported outcomes are authoritative — sync never overwrites them. **Clinical labels are never defaulted**: body part / issue type come from dial answers, else are inferred from the caller's own transcript lines (agent greetings excluded — "Welcome *back*" is not a spine injury), else stay `NULL`. |
| `POST /api/calls/simulate` | One-click end-to-end scenario runner (name, phone, status, body part, issue type, doctor, location). |

### 3. Call Review Dashboard (`frontend/`, zero-dependency vanilla JS served by Flask)
Live counters (Total / Scheduled / Redirected / Abandoned / Failed + conversion), filterable call history, per-call inspector with speaker-bubble transcripts, confirmed-appointment banner, clinical summary, and a transcript-source badge that states each outcome's provenance (flow-reported vs. synced-inferred vs. simulated). Auto-refresh preserves the reviewer's current selection; the simulator covers location as well as doctor requests.

### 4. Vogent Conversational Flow (v5.6, live default)
`work-trial/deploy_vogent_flow_v12.py` deploys **"Kyron Clinical Scheduling Flow v5.6 (Speaking Identity & Confirmation)"** — 26 nodes, 7 linked functions, `INBOUND_OUTBOUND` opening so dashboard phone tests greet the same as inbound callers. Beyond the happy path it contains: a decline-first slot gate with an accept-language safety net and an echo-confirm recovery node; a clarified-issue recovery loop with a human-escape to the coordinator; explicit handling for every routing status code; string (`new`/`returning`) identity gates instead of boolean comparisons; network caller ID instead of transcribed phone numbers; spoken filler during booking; confirmations as question nodes (templates inside freeform prompts arrived unresolved and spoke nothing on three live dials); and booking/telemetry inputs restricted to variable shapes proven to resolve on real dials.

---

## 🔬 Debugged Against Real Dials (what broke, why, what changed)

Two live dials were traced end-to-end via `GET /dials/{id}` node transitions (plus a second round after v5.0):

| Dial | Symptom | Root cause | Fix |
| :--- | :--- | :--- | :--- |
| John Black (Knee, accepted "Thursday, 10 AM") | Routed to decline node; agent hallucinated "…is now booked"; nothing booked; dashboard said REDIRECTED | Slot-choice classifier missed the time-repeat reply; `{{…available_slots.0.id}}` array syntax arrived as a literal (booking 500s); sync's "intake coordinator" substring heuristic overwrote the flow's ABANDONED | Decline-first + accept-language + echo-confirm gates; backend time-matches quoted replies; sync no longer overwrites flow outcomes |
| Alice Johnson (returning, "Spine follow-up, Dr. Patel") | `found:true` lookup routed to new-patient path; double chart speech; hung up during re-interrogation | Boolean gate failed on two separate dials — replaced with a `patient_status` string gate (`returning`/`new` returned explicitly by the API); globals ride the string since boolean interpolation also arrived unresolved; follow-up → General |
| v5.0 test calls (Emmanuel, Alice) | "10:00 AM" spoken as "one thousand"; agent never hung up (every dial ended in user hangup); same time offered twice; doctor named mid-triage ignored | TTS reads `:00` literally; Vogent leaves terminal function nodes open; parallel location slots shared timestamps; doctor inference scanned only the preferences field | Spoken times ("10 AM") everywhere voiced; backend hangs up non-transfer dials after telemetry; distinct-time offers with location qualifiers; word-boundary doctor scan over all freeform answers |
| v5.3 live test (your call) | Booking succeeded but confirmation never spoke; caller hung up in dead air; caller-ID resolver stored our own Vogent number on charts; a platform event flipped the booking to FAILED | No filler speech during the multi-second booking call; `fromPhoneNumber` is always the workspace number (never the caller); dial lifecycle status ("completed") overwrote the call outcome | "Booking that for you now" filler; CLI excludes own workspace numbers; platform events acknowledged without touching rows; booked rows structurally pinned to SCHEDULED |

---

## 🎯 Key Decisions & Tradeoffs

1. **Backend is the source of truth, the flow is a thin client.** Vogent documents only `{{node.id.field}}` references — array indexing doesn't resolve — so the flow passes raw caller answers and the booking endpoint re-runs the identical deterministic engine. Cost: one extra routing query per booking; benefit: offered and booked slots can never disagree.
2. **Flow-reported outcomes win over inferred ones.** Transcript-substring status guessing once flipped a real ABANDONED to REDIRECTED; sync now only fills gaps.
3. **Booking owns appointments, telemetry owns transcripts.** An earlier version had booking fabricate a "realistic" transcript that overwrote actual conversations — removed; it only links `appointment_id`.
4. **Honest unknowns.** Unresolvable outcomes default to `FAILED` (not SCHEDULED) so conversion metrics are never inflated; unresolved templates are dropped, never persisted. The old sync defaults of `"Knee"` / `"Sports Medicine"` were removed entirely — unknown clinical labels stay `NULL` (or the literal `"Unknown"` on NOT NULL booking columns) rather than inventing a diagnosis on a caller's chart. Related: chart creation without a name is a `400`, and booking to an unresolvable chart fails loudly with spoken recovery instead of silently attaching to the most recent patient.
5. **Placeholder telephony identity.** The flow has no reliable caller-CLI variable, so new charts carry `+15550100000` and dedupe by name. Caller identity is therefore chart-identity, not line-identity — acceptable for the trial, flagged below as follow-up work.
6. **Network caller ID over transcription (v5.2).** Every function call carries a `dial_id` wrapper, so the backend exchanges it for the real caller CLI via Vogent's dial query (cached per dial, 2.5s cap, silent fallback) instead of trusting transcribed "phone numbers". Lookup tries CLI first, spoken name second; new charts store the real CLI so repeat callers are recognized with no questions. Identity confirmation ("Is this X?") stays, because shared phones exist.
6. **Single-question slot echo-confirm instead of NLU over labels.** Mapping "Thursday, 10 AM" onto internal `first_option` labels is the observed failure mode; a direct yes/no echo plus backend time-matching is boring and reliable.
7. **Known risks left visible:** the Vogent API key ships as a code fallback (`calls.py`) instead of a managed secret; diagnostics use `print` rather than structured logging; webhook duration defaults to 90s until dial sync replaces it with the real value. All three are in the roadmap, none affect call behavior.

## 🎯 What Was Deliberately Skipped & Why

1. **Reschedule / cancellation endpoints** — ~90% of inbound volume is first-time triage + booking; the `Appointment`↔`Slot` unique constraint and lookup models make these a small additive change, so protocol correctness came first.
2. **Framework frontend (React/Next.js)** — a zero-dependency dashboard keeps single-container EC2 deployment failure-proof; no build step, no 300MB `node_modules`.
3. **SMS/Twilio confirmations** — confirmations are structured API data (`confirmation_speech` + dashboard banner) rather than live carrier calls; binding real credentials is deployment config, not trial signal.
4. **AuthN/Z on the API** — the trial backend is a private demo host behind an unlisted domain; per-clinic auth (and the secret-manager fix above) belongs with real PHI, which this demo dataset does not contain.

## 🚀 What We'd Do Next With More Time

1. Managed secrets + request signing for Vogent webhooks; structured JSON logging with dial-id correlation.
2. Real caller-CLI passthrough (Vogent telephony variable) to replace placeholder-number identity.
3. Reschedule/cancel voice paths reusing the existing slot engine.
4. Physician vacation/shift overrides UI (block surgery days without code changes).
5. Insurance eligibility (270/271) pre-check inside `routing/match`.
6. EHR adapters (Epic on FHIR, AthenaHealth) behind the current `Slot`/`Appointment` boundary.

## 📹 Video Walkthrough
*Link to Loom / Drive walkthrough to be added — the dashboard's Simulate button reproduces every scenario in the demo live.*

## 🗂️ Code Map
* `backend/app/models.py` → relational schemas · `backend/app/protocols.py` → pure routing logic + TTS-safe speech formatting · `backend/app/api/` → HTTP transport · `backend/tests/` → pytest suite (32 tests) · `frontend/` → dashboard · `vogent/` → flow blueprint + contracts · `work-trial/deploy_vogent_flow_v12.py` → live v5.6 flow deployer
