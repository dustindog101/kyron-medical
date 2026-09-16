# AI Medical Scheduling Agent — Voice Triage, Booking & Call Review

> **DRAFT — under review, not yet the submission README.** A voice-based scheduling agent for a medical facility: patients call in, a Vogent voice agent triages them against real physician protocols, a Flask backend matches them to the right doctor and books a live slot, and a call-review dashboard captures every call for audit. **Live and deployed — not a localhost demo.**

**Live deployment:** `https://54-90-91-169.sslip.io` (dashboard + API, AWS EC2 via Docker + Caddy + auto-TLS)
**Draft dashboard (React):** `https://54-90-91-169.sslip.io/draft/` · **Legacy dashboard:** `/legacy/`
**Inbound test line:** +1 (301) 560-1855 (Vogent number, live scheduling flow v5.6)
**Video walkthrough:** *(link coming — Loom/Drive)*

---

## What it does — end to end in one call

A patient dials the test line. The voice agent asks if they're new or returning, takes their name, asks about the body part and the nature of the visit, then calls the backend's routing engine — which checks 12 physicians, 3 locations, and protocol constraints — offers real open slots, books the caller's pick, speaks a confirmation, and logs the full transcript plus booking status to the dashboard. When no doctor fits (closed panel, wrong specialty), the agent explains why in plain language and redirects instead of failing.

Real call from the live line, as it appears on the dashboard today:

> **Caller:** new patient, knee sports injury, no location preference
> **Agent:** *"I have matched you with Dr. Maria Chen for your knee sports medicine at our Main Campus. I have available times on Wednesday at 4 PM or Thursday at 10 AM…"*
> **Caller:** *"The first one."* → booked, confirmed, dashboard row `SCHEDULED` with appointment card.

---

## Architecture

```text
 Patient phone call
       │
       ▼
 Vogent voice agent (flow v5.6 — 26 nodes, 7 API functions)
   │  triangulates: identity → body part → issue type → preference
   │  every data step is a backend call; the flow keeps no clinical logic
   ▼
 Flask REST API + deterministic protocol engine (app/protocols.py)
   │  patient lookup/creation · protocol match + live slots · booking
   │  call telemetry webhook · Vogent dial sync · simulation runner
   ▼
 SQLite + SQLAlchemy (Patient · Doctor · Slot · Appointment · CallLog)
       │
       ▼
 Call-review dashboard (React draft at /draft/, vanilla legacy at /legacy/)
   metrics · filterable call history · transcript inspector · patients,
   providers & schedule views · one-click call simulator
```

The founding decision: **the backend is the source of truth and the voice flow is a thin client.** Vogent only resolves `{{node.id.field}}` references — array indexing arrives as literal text — so the booking endpoint re-runs the identical deterministic routing engine instead of trusting slot IDs from the call. One extra query per booking; offered and booked slots can never disagree.

---

## What was built

**1. Physician-protocol routing engine** (`backend/app/protocols.py`) — the clinical brain, pure rules over 12 doctors, 3 locations (`MAIN`, `NORTH`, `WEST`), 4 issue types:
- Per-doctor, per-body-part matching — a doctor matches only exact (body part, issue type) protocol pairs, never "treats knees" generally.
- `General` is general-only — fracture/sports/joint-replacement callers are never routed to a `General` entry.
- Closed-panel handling — Patel, O'Brien, Reed don't take new patients; the engine says so out loud and redirects (new hip joint-replacement asking for Patel → Chen).
- Slot-aware fallback — top match full? Falls through overlapping doctors (Knee: Chen → Vasquez → Walsh) mid-call.
- Synonym-tolerant normalization — "follow-up" → General, "sprain/ACL" → Sports, "broken" → Fracture, "back/neck" → Spine.
- Every match returns `agent_speech` the voice agent speaks **verbatim** — redirect explanations stay empathetic and consistent.

**2. Flask REST backend** (`backend/app/api/`) — POST-only Vogent functions with `{"params": {...}}` wrappers, defensive coercion throughout (string booleans/IDs, list-vs-string transcripts, `{{template}}` literals): patient lookup/creation with duplicate-safe dedupe, routing match, slot listing, booking with double-booking guards and quoted-time matching ("Thursday at 11" books the 11:00, not the 10:00), end-of-call webhook, dial-sync reconciliation, and a one-click `/calls/simulate` scenario runner.

**3. Call-review dashboard** — the React draft adds Calls (live counters, filters, speaker-bubble transcripts, appointment banners, transcript-provenance badges), Patients, Providers (12 physicians + locations), and Schedule views, with polling that preserves the reviewer's selection and a simulator modal featuring one-click evaluation presets: the Patel closed-panel trap, a knee-fracture match, and a spine follow-up. The zero-dependency vanilla dashboard remains live at `/legacy/` — same backend, no build step, single-container deploy.

**4. Vogent conversational flow v5.6** — 26 nodes, 7 linked functions, `INBOUND_OUTBOUND` opening: decline-first slot gate with accept-language safety net and echo-confirm recovery, clarified-issue loop with human escape, string (`new`/`returning`) identity gates, network caller ID instead of transcribed numbers, spoken filler during booking, confirmations as question nodes, and booking/telemetry restricted to variable shapes proven on real dials.

**5. Tests** — 21+ pytest cases: routing edge cases, new-vs-returning rules, redirections, double-booking protection, missing-input and template-literal rejection, Vogent payload shapes, second-slot time matching, follow-up normalization. Green in under a second.

---

## What broke on real calls — and what changed because of it

This wasn't built against mocks. Every item below is a real dial traced via Vogent node transitions, fixed, and re-verified with a second round of test calls:

| Real dial | Symptom | Root cause | Fix |
| :--- | :--- | :--- | :--- |
| Knee caller accepts "Thursday, 10 AM" | Routed to decline node; agent **hallucinated "…is now booked"**; nothing booked; dashboard said REDIRECTED | Slot-choice classifier missed time-repeat replies; `{{…slots.0.id}}` arrived literal; transcript-substring heuristic overwrote the flow's ABANDONED | Decline-first + echo-confirm gates; backend time-matches quoted replies; flow-reported outcomes are authoritative, sync only fills gaps |
| Returning spine follow-up for Patel | Lookup said `found:true`, flow took the new-patient path; double chart speech; caller hung up | Boolean gate failed on **two separate live dials** | Replaced with explicit `new`/`returning` string gates end to end — booleans never cross the voice boundary |
| "10:00 AM" confirmations | TTS spoke **"one thousand"**; agent never hung up; same slot offered twice; mid-triage doctor mention ignored | `:00` read literally; Vogent leaves terminal function nodes open; parallel location slots shared timestamps | Spoken times ("10 AM") everywhere voiced; backend releases the line after telemetry; distinct-time offers with location qualifiers |
| Your live test call (v5.3) | Booking succeeded but confirmation never spoke; dead air; chart stored **our own Vogent number** | No filler during the multi-second booking call; `fromPhoneNumber` is always the workspace number; a platform event flipped the booking to FAILED | "Booking that for you now" filler; CLI resolved via dial query excluding own numbers; platform events acknowledged without touching rows |
| Booking audit | Booked rows carried **fabricated "realistic" transcripts** | Booking synthesized conversation text that overwrote real telemetry | Removed entirely — booking only links `appointment_id`; telemetry owns transcripts |
| Dashboard review | Calls labeled Knee / Sports Medicine with no evidence | Sync defaulted unknown clinical labels | Removed — unknowns stay `NULL`/`"Unknown"`; inference reads caller lines only (agent greetings like "Welcome *back*" excluded) |

The through-line: **HTTP 200 with `success:false` plus speakable `agent_speech` — never an HTTP error.** An error page is what the voice agent hallucinated fake confirmations over. Every failure mode returns words the agent can say.

---

## Key tradeoffs (judgment calls)

1. **Backend owns truth, flow owns conversation.** Duplicated routing at booking costs one query; it buys an invariant (offered = booked) that no prompt engineering could.
2. **Flow-reported outcomes beat inferred ones.** Transcript-substring status guessing once flipped a real ABANDONED to REDIRECTED. Heuristics fill gaps only.
3. **Honest unknowns over inflated metrics.** Unresolvable outcomes default to `FAILED`, never `SCHEDULED` — conversion rate (live: ~31% across real telephony) is real.
4. **Placeholder telephony identity, flagged openly.** The flow exposes no reliable caller-CLI variable, so new charts carry a placeholder and dedupe by name, upgraded to network CLI via dial query where resolvable. Chart-identity, not line-identity — acceptable for the trial, listed below as follow-up work.
5. **Boring reliability over clever NLU.** Yes/no echo-confirm plus backend time-matching replaced label-mapping because label-mapping was the observed failure mode.

## Deliberately skipped — and why

- **Reschedule/cancel voice paths** — ~90% of inbound volume is first-time triage + booking; the `Appointment`↔`Slot` constraint makes these additive later. Protocol correctness first.
- **SMS/Twilio confirmations** — confirmations are structured API data (`confirmation_speech` + dashboard banner); carrier binding is deployment config, not trial signal.
- **API authN/Z** — private demo host, unlisted domain, no real PHI in the demo dataset; per-clinic auth ships with real patient data.
- **Known risks left visible, not hidden:** Vogent key ships as code fallback instead of a managed secret; diagnostics use `print`, not structured logging; webhook duration defaults to 90s until dial sync replaces it.

## With more time

Managed secrets + webhook signing → real caller-CLI passthrough → reschedule/cancel paths on the existing slot engine → physician vacation/shift overrides UI → insurance eligibility (270/271) inside `routing/match` → EHR adapters (Epic on FHIR, AthenaHealth) behind the `Slot`/`Appointment` boundary → cancellation waitlist fills.

---

## Run it

```bash
docker compose up -d --build   # dashboard :5000, API /health, protocols /api/protocols/summary
# or local:  cd backend && pip install -r requirements.txt && python app/seed.py && python wsgi.py
PYTHONPATH=. pytest -v         # 21+ tests, <1s
```

## Code map

`backend/app/protocols.py` routing brain · `backend/app/models.py` schemas · `backend/app/api/` HTTP transport · `backend/tests/` suite · `frontend-draft/src/` React dashboard (Calls · Patients · Providers · Schedule · Simulator) · `frontend/` legacy dashboard · `vogent/` flow blueprint + contracts · `work-trial/deploy_vogent_flow_v12.py` live v5.6 deployer
