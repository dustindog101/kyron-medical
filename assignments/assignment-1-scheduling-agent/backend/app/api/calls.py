import datetime
import uuid
import os
import json
import time
import urllib.request
from dateutil import parser as dt_parser
from flask import Blueprint, request, jsonify
from app.database import SessionLocal
from app.models import CallLog, Patient, Appointment, Slot, Doctor
from app.protocols import route_patient, normalize_body_part, normalize_issue_type

calls_bp = Blueprint("calls", __name__, url_prefix="/api/calls")

VOGENT_API_KEY = os.environ.get("VOGENT_API_KEY", "vogent_XGkutFBzQym2HXnlGQDcNo09j8H0cDJW")
VOGENT_WORKSPACE_ID = os.environ.get("VOGENT_WORKSPACE_ID", "6604a92d-1489-44dd-a38b-f14d978230cb")
_last_sync_time = 0

def safe_int(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.startswith("{{"):
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None

def _transcript_to_text(val):
    """Coerce a Vogent transcript (string, list of segments, or None) to plain text.

    Vogent sends ``includeTranscript`` payloads as a LIST of segment dicts,
    while older templates render ``{{call.full_transcript}}`` as a literal
    string. Both shapes (and None) are handled here so callers never crash
    on ``.startswith``.
    """
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        lines = []
        for item in val:
            if not isinstance(item, dict):
                continue
            role = str(item.get("speaker") or item.get("role") or "").lower()
            spk = "Agent" if role in ("ai", "agent", "assistant") else "Caller"
            txt = item.get("text") or item.get("message") or item.get("content") or ""
            if txt:
                lines.append(f"{spk}: {txt}")
        return "\n".join(lines) if lines else None
    return str(val)


def _is_unresolved_template(val):
    """True for literal ``{{...}}`` template strings Vogent failed to resolve."""
    return isinstance(val, str) and (
        val.strip().startswith("{{") or "call.sid" in val or "call.full_transcript" in val
    )


def _maybe_hangup_dial(call_sid, status):
    """Release the line when the flow reaches its terminal telemetry node.

    Vogent does not auto-hangup after a terminal function node, so completed
    calls sat open until the human hung up (every dial on record ended
    USER_/COUNTERPARTY_HANGUP). Never hang up REDIRECTED calls — the transfer
    leg is still live when telemetry fires. Best-effort: telemetry must never
    fail because the hangup did.
    """
    if status not in ("SCHEDULED", "ABANDONED", "FAILED"):
        return
    if not call_sid or _is_unresolved_template(str(call_sid)):
        return
    if not VOGENT_API_KEY:
        return
    try:
        from flask import current_app, has_app_context
        if has_app_context() and current_app.config.get("TESTING"):
            return
    except Exception:
        pass
    try:
        req = urllib.request.Request(
            f"https://api.vogent.ai/api/dials/{call_sid}/hangup",
            headers={"Authorization": f"Bearer {VOGENT_API_KEY}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3):
            pass
    except Exception as e:
        print(f"Warning: Vogent hangup skipped for {call_sid}: {e}")


def _transfer_was_executed(tr_text, system_result_type):
    """True only when the coordinator handoff actually happened.

    The decline path now *offers* the coordinator by name ("Should I
    connect you with our intake coordinator now?") and callers can say no
    (dial 6dd3217a: declined, goodbye, hangup) — the old substring check
    on "intake coordinator" mislabeled those ABANDONED calls REDIRECTED.
    Execution evidence is the transfer announcement/filler lines or the
    platform TRANSFERRED result, never a mere mention.
    """
    if (system_result_type or "") in ("TRANSFER", "TRANSFERRED"):
        return True
    lowered = (tr_text or "").lower()
    return any(
        phrase in lowered
        for phrase in (
            "transferring you to our",
            "while i transfer you",
            "please hold the line for just a moment",
        )
    )


def _infer_sync_status(tr_text, system_result_type, has_appointment, duration):
    """Outcome for a dial-synced row when the flow never reported one."""
    if has_appointment:
        return "SCHEDULED"
    if _transfer_was_executed(tr_text, system_result_type):
        return "REDIRECTED"
    if system_result_type in ("USER_HANGUP", "COUNTERPARTY_HANGUP") or (duration or 0) > 0:
        return "ABANDONED"
    return "FAILED"


def _infer_clinical_from_transcript(clean_lines):
    """Infer (body_part, issue_type) from the caller's own words.

    Scans Caller lines only — Agent greetings contain traps like
    "Welcome *back*" which naive substring matching reads as Spine.
    Returns (None, None) when nothing is recognizable: callers must never
    be assigned a fabricated "Knee / Sports Medicine" label.
    """
    bp = it = None
    for line in clean_lines:
        if not line.startswith("Caller:"):
            continue
        said = line[len("Caller:"):].strip()
        if not bp:
            bp = normalize_body_part(said)
        if not it:
            it = normalize_issue_type(said)
        if bp and it:
            break
    return bp, it

def _is_placeholder_sync_phone(phone):
    digits = "".join(filter(str.isdigit, str(phone or "")))
    return (
        not digits
        or digits in ("5550100000", "0000000000", "15550100000")
        or digits.endswith("5550100000")
    )


def resolve_sync_patient(sync_db, phone, pname, is_new):
    """Phone-first patient resolution for Vogent dial sync.

    The dial transcript name is an STT guess ("Alex Peck" for chart holder
    "Alex Tuck"), so resolving by name first minted a duplicate dashboard
    chart (id 17) for an existing patient (id 16, same phone). The phone
    CLI is the stronger identity: it wins whenever it matches a chart,
    and the chart keeps its canonical name. Name lookup is the fallback
    only when no usable phone matched.
    """
    if phone and not _is_placeholder_sync_phone(phone):
        digits = "".join(filter(str.isdigit, str(phone)))
        key = digits[-10:] if len(digits) >= 7 else str(phone)
        by_phone = sync_db.query(Patient).filter(Patient.phone.like(f"%{key}%")).first()
        if by_phone:
            return by_phone, False
    if pname and pname != "Caller":
        by_name = sync_db.query(Patient).filter(Patient.name.ilike(pname)).first()
        if by_name:
            return by_name, False
        created = Patient(name=pname, phone=phone, is_new_patient=is_new)
        sync_db.add(created)
        sync_db.flush()
        return created, True
    if phone:
        by_phone = sync_db.query(Patient).filter(Patient.phone == phone).first()
        if by_phone:
            return by_phone, False
    created = Patient(name=pname or "Caller", phone=phone or "+15550100000", is_new_patient=is_new)
    sync_db.add(created)
    sync_db.flush()
    return created, True


def _post_commit_followups(call_sid, status):
    """Release the line and refresh dial sync without blocking the webhook.

    Post-confirmation dead air (dial-sync GraphQL + hangup round-trips ran
    inline) made callers hang up before telemetry completed — every booked
    dial on record is missing node_end_call. Both follow-ups are
    best-effort and deferred to a daemon thread so the webhook answers at
    once; TESTING skips them to keep tests hermetic.
    """
    try:
        from flask import current_app, has_app_context
        if has_app_context() and current_app.config.get("TESTING"):
            return
    except Exception:
        pass
    import threading

    def _run():
        try:
            _maybe_hangup_dial(call_sid, status)
        except Exception:
            pass
        try:
            sync_vogent_dials(force=True)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def sync_vogent_dials(db=None, force=False):
    try:
        from flask import current_app
        if current_app and current_app.config.get("TESTING"):
            return
    except Exception:
        pass

    global _last_sync_time
    now = time.time()
    if not force and (now - _last_sync_time) < 2.0:
        return
    _last_sync_time = now

    if not VOGENT_API_KEY or not VOGENT_WORKSPACE_ID:
        return

    query = """
    query GetDials($workspaceId: ID!) {
      workspace(id: $workspaceId) {
        dials(offset: 0, limit: 30) {
          numDials
          dials {
            id
            status
            createdAt
            completedAt
            callTimeSeconds
            systemResultType
            toNumber
            fromPhoneNumber {
              number
            }
            aiResult
            transcript {
              text {
                role
                text
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"workspaceId": VOGENT_WORKSPACE_ID}}).encode()
    req = urllib.request.Request(
        "https://api.vogent.ai/query",
        data=payload,
        headers={"Authorization": f"Bearer {VOGENT_API_KEY}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            resp_data = json.loads(resp.read().decode())
            dials = resp_data.get("data", {}).get("workspace", {}).get("dials", {}).get("dials", [])
    except Exception as e:
        print(f"Warning: Vogent dial sync skipped: {e}")
        return

    sync_db = SessionLocal()
    try:
        for d in dials:
            dur = d.get("callTimeSeconds", 0)
            raw_lines = (d.get("transcript") or {}).get("text", [])
            if dur == 0 and not raw_lines:
                continue

            clean_lines = []
            for l in raw_lines:
                role = (l.get("role") or "").upper()
                txt = (l.get("text") or "").strip()
                if not txt or role == "NODE_TRANSITION":
                    continue
                spk = "Agent" if role == "AI" else "Caller"
                clean_lines.append(f"{spk}: {txt}")

            if not clean_lines:
                continue

            tr_text = "\n".join(clean_lines)
            ai_res = d.get("aiResult") or {}

            # 1. Resolve Patient
            _collect = ai_res.get("node_collect_new_patient") or {}
            _created = ai_res.get("node_create_patient") or {}
            pname = _collect.get("answer") or (_created.get("patient") or {}).get("name")
            if not pname:
                for cl in clean_lines:
                    if cl.startswith("Caller:") and len(cl) > 8 and "hello" not in cl.lower() and "patient" not in cl.lower():
                        pname = cl.replace("Caller:", "").strip().rstrip(".")
                        break
            pname = pname or "Caller"

            phone = (d.get("fromPhoneNumber") or {}).get("number") or (_created.get("patient") or {}).get("phone") or "+15550100000"
            # Leg direction varies (inbound vs outbound): either side that is
            # not one of our own workspace numbers is the remote party.
            try:
                from app.api.patients import _own_workspace_numbers
                _own = _own_workspace_numbers()
                for _cand in (
                    (d.get("fromPhoneNumber") or {}).get("number"),
                    d.get("toNumber"),
                    (_created.get("patient") or {}).get("phone"),
                ):
                    if _cand and _cand not in _own:
                        phone = _cand
                        break
            except Exception:
                pass
            _ask_body = ai_res.get("node_ask_body_part") or {}
            _ask_issue = ai_res.get("node_ask_issue_type") or {}
            bp = _ask_body.get("answer")
            it = _ask_issue.get("answer")
            if not bp or not it:
                _inf_bp, _inf_it = _infer_clinical_from_transcript(clean_lines)
                bp = bp or _inf_bp
                it = it or _inf_it
            # Honest unknowns stay None — never stamp a default "Knee /
            # Sports Medicine" onto a caller's chart. Summaries phrase
            # around it; stored detected_* columns are nullable.
            bp_provided = bool(bp)
            it_provided = bool(it)

            is_new = True
            _greet = ai_res.get("node_greeting") or {}
            greeting_ans = _greet.get("answer")
            if greeting_ans and "returning" in str(greeting_ans).lower():
                is_new = False

            patient, _ = resolve_sync_patient(sync_db, phone, pname, is_new)

            try:
                created_dt = dt_parser.parse(d.get("createdAt"))
            except Exception:
                created_dt = datetime.datetime.now(datetime.timezone.utc)

            # 2. Resolve Appointment & Status. NOTE: Vogent's enum value is
            # "TRANSFERRED" (see Get Dial docs) — the old "TRANSFER" check
            # never matched, so transferred calls fell into ABANDONED below.
            appt_info = (ai_res.get("node_book_appointment") or {}).get("appointment")
            appt = None
            if appt_info:
                status = "SCHEDULED"
                doc_name = appt_info.get("doctor_name", "Specialist")
                loc_name = appt_info.get("location_name", "Main Campus")
                fmt_time = appt_info.get("formatted_time", "")
                _concern = f"{bp} ({it})" if (bp and it) else (bp or it or "an unspecified concern")
                summary = f"Confirmed appointment with {doc_name} for {_concern} at {loc_name} on {fmt_time}."

                appt = sync_db.query(Appointment).filter(Appointment.patient_id == patient.id, Appointment.status == "SCHEDULED").first()
                if not appt:
                    doc = sync_db.query(Doctor).filter(Doctor.name == doc_name).first()
                    slot = None
                    if doc:
                        try:
                            appt_time_dt = dt_parser.parse(appt_info.get("appointment_time"))
                            slot = sync_db.query(Slot).filter(Slot.doctor_id == doc.id, Slot.start_time == appt_time_dt).first()
                        except Exception:
                            pass
                        if not slot:
                            slot = sync_db.query(Slot).filter(Slot.doctor_id == doc.id, Slot.is_booked == False).order_by(Slot.start_time).first()
                    if not slot:
                        slot = sync_db.query(Slot).filter(Slot.is_booked == False).order_by(Slot.start_time).first()

                    if slot:
                        already_appt = sync_db.query(Appointment).filter(Appointment.slot_id == slot.id).first()
                        if not already_appt:
                            slot.is_booked = True
                            appt = Appointment(
                                patient_id=patient.id,
                                doctor_id=slot.doctor_id,
                                slot_id=slot.id,
                                location_code=slot.location_code,
                                # Columns are NOT NULL: "Unknown" marks the
                                # gap honestly instead of inventing Knee /
                                # Sports Medicine. In practice this path is
                                # nearly dead — real bookings already exist
                                # (created by /book) and link above.
                                body_part=bp or "Unknown",
                                issue_type=it or "Unknown",
                                notes=appt_info.get("notes") or "",
                                status="SCHEDULED",
                                created_at=created_dt,
                            )
                            sync_db.add(appt)
                            try:
                                sync_db.flush()
                            except Exception:
                                sync_db.rollback()
                                appt = None
            status = _infer_sync_status(tr_text, d.get("systemResultType"), bool(appt_info), dur)
            if status == "SCHEDULED":
                _concern = f"{bp} ({it})" if (bp and it) else (bp or it or "an unspecified concern")
                summary = f"Confirmed appointment with {doc_name} for {_concern} at {loc_name} on {fmt_time}."
            elif status == "REDIRECTED":
                _concern = f"{bp} ({it})" if (bp and it) else (bp or it or "an unspecified concern")
                summary = f"Caller inquiring about {_concern} redirected to patient intake coordinator."
            elif status == "ABANDONED":
                summary = "Caller disconnected before completing appointment scheduling."
            else:
                _concern = f"{bp} ({it})" if (bp and it) else (bp or it or "an unspecified concern")
                summary = f"Inbound call regarding {_concern} could not be completed."

            # 3. Create or update CallLog. The flow's own webhook status is
            # authoritative: never overwrite a webhook-sourced row's status
            # with a transcript heuristic (e.g. "intake coordinator" ->
            # REDIRECTED wrongly overrode an ABANDONED flow outcome in dial 7).
            existing_call = sync_db.query(CallLog).filter(CallLog.call_sid == d.get("id")).first()
            if existing_call:
                if existing_call.transcript_source != "Vogent Telephony Webhook":
                    existing_call.status = status
                    existing_call.transcript_source = "Vogent Telephony Audio Sync"
                # Structural invariant: a linked booking means SCHEDULED, no
                # matter what any heuristic inferred (a platform "completed"
                # event once flipped a real booking to FAILED).
                if existing_call.appointment_id or appt:
                    existing_call.status = "SCHEDULED"
                if tr_text and len(tr_text) > len(existing_call.transcript or ""):
                    existing_call.transcript = tr_text
                existing_call.summary = summary
                existing_call.duration_seconds = dur
                # Only overwrite clinical labels when the dial actually
                # provided them — otherwise a sync pass would stamp the
                # "Knee"/"Sports Medicine" fallbacks over real webhook values.
                if bp_provided:
                    existing_call.detected_body_part = bp
                if it_provided:
                    existing_call.detected_issue_type = it
                if patient:
                    existing_call.patient_id = patient.id
                if appt:
                    existing_call.appointment_id = appt.id
            else:
                new_call = CallLog(
                    call_sid=d.get("id"),
                    caller_phone=phone,
                    patient_id=patient.id if patient else None,
                    appointment_id=appt.id if appt else None,
                    status=status,
                    transcript=tr_text,
                    transcript_source="Vogent Telephony Audio Sync",
                    summary=summary,
                    detected_body_part=bp,
                    detected_issue_type=it,
                    duration_seconds=dur,
                    created_at=created_dt,
                )
                sync_db.add(new_call)

        sync_db.commit()
    except Exception as e:
        sync_db.rollback()
        print(f"Error committing synced dials: {e}")
    finally:
        sync_db.close()

@calls_bp.route("/sync", methods=["POST", "GET"])
def sync_calls_endpoint():
    """
    Explicit endpoint to force synchronization of calls from Vogent.
    """
    db = SessionLocal()
    try:
        sync_vogent_dials(db, force=True)
        total = db.query(CallLog).count()
        return jsonify({
            "success": True,
            "message": f"Successfully synced calls from Vogent. Total calls: {total}",
        }), 200
    finally:
        db.close()

@calls_bp.route("/webhook", methods=["POST"])
def call_webhook():
    """
    Webhook endpoint invoked by Vogent when a call ends.
    Logs call metadata, full transcript, status, and linked appointment.
    """
    raw_data = request.get_json(silent=True) or {}
    params = raw_data.get("params") if isinstance(raw_data.get("params"), dict) else {}
    data = {**raw_data, **params}
    # Platform event payloads (dial.created etc.) are not flow telemetry:
    # they must never trigger a hangup, only the flow's own end-of-call
    # report may release the line.
    is_platform_event = isinstance(data.get("payload"), dict)

    # Platform event payloads (dial.created/updated/...) carry no clinical
    # data and must never create rows or flip outcomes: one such event
    # overwrote a real SCHEDULED booking with FAILED ("completed" is a dial
    # lifecycle status, not a call outcome). Acknowledge and ignore.
    if is_platform_event:
        return jsonify({
            "success": True,
            "message": "Platform event acknowledged; no call data to log.",
        }), 200

    # Flow telemetry shape: {"params": {...}, "dial_id": "..."} (+ legacy flat).
    caller_phone = data.get("caller_phone") or ""
    transcript = _transcript_to_text(data.get("transcript"))
    call_sid = data.get("call_sid") or data.get("dial_id")
    status = data.get("status") or "FAILED"
    if not isinstance(status, str):
        status = "FAILED"

    # Sanitize literal template strings from Vogent
    if call_sid and (str(call_sid).startswith("{{") or "call.sid" in str(call_sid)):
        call_sid = raw_data.get("dial_id") or data.get("dial_id")

    if not call_sid or str(call_sid).startswith("{{"):
        call_sid = f"VOG-{uuid.uuid4().hex[:12].upper()}"

    # Check for raw transcript from includeTranscript (Vogent sends a LIST of segments)
    raw_transcript = raw_data.get("transcript")
    coerced = _transcript_to_text(raw_transcript)
    if coerced:
        transcript = coerced
    elif _is_unresolved_template(transcript):
        transcript = None

    if not isinstance(status, str) or _is_unresolved_template(status):
        status = "FAILED"
    else:
        status = str(status).upper()
    if status not in ["SCHEDULED", "REDIRECTED", "ABANDONED", "FAILED"]:
        status = "FAILED"

    patient_id = safe_int(data.get("patient_id"))
    appointment_id = safe_int(data.get("appointment_id"))
    duration_sec = safe_int(data.get("duration_seconds")) or 90

    db = SessionLocal()
    try:
        # Resolve the caller's real phone: fall back to the identified patient's
        # phone when Vogent sends a placeholder or an unresolved template.
        if not caller_phone or _is_unresolved_template(caller_phone):
            caller_phone = ""
        _phone_digits = "".join(filter(str.isdigit, caller_phone))
        _is_placeholder = (
            not _phone_digits
            or _phone_digits in ("5550100000", "0000000000", "15550100000")
            or _phone_digits.endswith("5550100000")
        )

        # Check if an existing call log exists for this call_sid or appointment_id
        existing = None
        if call_sid and not _is_unresolved_template(str(call_sid)):
            existing = db.query(CallLog).filter(CallLog.call_sid == call_sid).first()
        if not existing and appointment_id:
            existing = db.query(CallLog).filter(CallLog.appointment_id == appointment_id).first()

        if _is_placeholder and patient_id:
            _pat = db.query(Patient).filter(Patient.id == patient_id).first()
            if _pat and _pat.phone:
                caller_phone = _pat.phone
                _is_placeholder = False
        if _is_placeholder:
            # Last resort before the placeholder: the live call's own CLI.
            from app.api.patients import resolve_cli_phone
            _cli = resolve_cli_phone(raw_data.get("dial_id") or data.get("dial_id"))
            if _cli:
                caller_phone = _cli
                _is_placeholder = False
        if not caller_phone:
            caller_phone = "+15550100000"

        if existing:
            if status:
                existing.status = status
            if transcript and not _is_unresolved_template(transcript):
                existing.transcript = transcript
                existing.transcript_source = "Vogent Telephony Webhook"
            if appointment_id:
                existing.appointment_id = appointment_id
            summary_val = data.get("summary")
            if summary_val and not _is_unresolved_template(str(summary_val)):
                existing.summary = summary_val
            if duration_sec:
                existing.duration_seconds = duration_sec
            db.commit()
            if not is_platform_event:
                _post_commit_followups(existing.call_sid, existing.status)
            return jsonify({
                "success": True,
                "call_id": existing.id,
                "call_sid": existing.call_sid,
                "message": "Call log updated successfully.",
            }), 201

        # Create new record if no existing record found. When no transcript
        # was captured (dropped/empty calls), store an EMPTY transcript —
        # never a fabricated placeholder conversation. The dashboard renders
        # empty transcripts as "No transcript recorded yet."
        if not transcript or _is_unresolved_template(transcript):
            transcript = ""

        summary_val = data.get("summary")
        if _is_unresolved_template(str(summary_val or "")):
            summary_val = None
        if not transcript and not summary_val:
            summary_val = "Call connected but no conversation was captured."
        bp_val = data.get("detected_body_part")
        if _is_unresolved_template(str(bp_val or "")):
            bp_val = None
        it_val = data.get("detected_issue_type")
        if _is_unresolved_template(str(it_val or "")):
            it_val = None

        log = CallLog(
            call_sid=call_sid,
            caller_phone=caller_phone,
            patient_id=patient_id,
            appointment_id=appointment_id,
            status=status,
            transcript=transcript,
            transcript_source="Vogent Telephony Webhook",
            summary=summary_val or "Kyron Medical Scheduling Call",
            detected_body_part=bp_val,
            detected_issue_type=it_val,
            duration_seconds=duration_sec,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        saved_call_id = log.id
        saved_call_sid = log.call_sid

        # Line release + dial sync run in background so the caller never
        # sits in post-confirmation silence (see _post_commit_followups).
        if not is_platform_event:
            _post_commit_followups(saved_call_sid, status)
        return jsonify({
            "success": True,
            "call_id": saved_call_id,
            "call_sid": saved_call_sid,
            "message": "Call log saved successfully.",
        }), 201
    finally:
        db.close()

@calls_bp.route("", methods=["GET"])
def get_calls():
    """
    List calls for the Call Review dashboard with filtering by status.
    Automatically syncs latest calls from Vogent GraphQL before querying.
    """
    status_filter = request.args.get("status")
    limit = request.args.get("limit", 50, type=int)

    db = SessionLocal()
    try:
        sync_vogent_dials(db, force=False)
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
    preferred_location = data.get("preferred_location")

    # Normalize clinical inputs so stored records stay canonical
    from app.protocols import normalize_body_part, normalize_issue_type
    body_part = normalize_body_part(body_part) or body_part
    issue_type = normalize_issue_type(issue_type) or issue_type

    db = SessionLocal()
    try:
        # 1. Lookup or create patient
        clean_phone = "".join(filter(str.isdigit, caller_phone or ""))
        phone_key = clean_phone[-10:] if len(clean_phone) >= 7 else (caller_phone or "")
        patient = db.query(Patient).filter(Patient.phone.like(f"%{phone_key}%")).first()
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
            preferred_location_code=preferred_location,
        )

        appt_id = None
        selected_slot = None
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
                try:
                    db.commit()
                except Exception:
                    # Lost a booking race (slot taken concurrently): report a
                    # clean FAILED simulation instead of a 500.
                    db.rollback()
                    slot = None
                    status = "FAILED"
                else:
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
            f"Caller: I need an appointment for my {(body_part or 'concern').lower()}, specifically for a {(issue_type or 'consultation').lower()}.\n"
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
            transcript_source="Direct Simulation",
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
