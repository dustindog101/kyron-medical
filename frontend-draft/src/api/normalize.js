// ==========================================================================
// Defensive normalizers: real backend payloads differ from the old mock
// shapes in clinicalData.js, and both must render without crashing.
//
// Backend realities handled here:
//   - call.transcript is a NEWLINE STRING ("Agent: ...\nCaller: ..."), the
//     mock used [{speaker, text}]. Either shape (or null / "{{...}}"
//     template leftovers) normalizes to [{speaker, text}].
//   - Clinical labels live in detected_body_part / detected_issue_type and
//     may be null (backend never invents a diagnosis). No `soap` object —
//     a SOAP-like dossier is derived from summary + appointment.
//   - Status enum is SCHEDULED | REDIRECTED | ABANDONED | FAILED
//     (the mock's TRIAGE never occurs live; still rendered if present).
//   - Doctor protocols use `accepted_type` (mock used `type`); doctors carry
//     no specialty / next_slot / intake_criteria — those are derived.
//   - There is NO patient-list endpoint: the directory is aggregated from
//     calls + appointments client-side.
// ==========================================================================

const isTemplate = (v) =>
  typeof v === 'string' && (v.trim().startsWith('{{') || v.includes('call.sid'));

// ---------------------------------------------------------------------------
// Transcripts
// ---------------------------------------------------------------------------

const AGENT_RE = /^(Agent|AI|Assistant|Kyron AI|\[AI\]|\[Agent\]):\s*/i;
const CALLER_RE = /^(Caller|Human|User|Patient|\[HUMAN\]|\[Caller\]):\s*/i;

function lineToTurn(rawLine) {
  const line = String(rawLine ?? '').trim();
  if (!line || isTemplate(line)) return null;
  if (AGENT_RE.test(line)) return { speaker: 'Kyron AI', text: line.replace(AGENT_RE, '').trim() || line };
  if (CALLER_RE.test(line)) return { speaker: 'Patient', text: line.replace(CALLER_RE, '').trim() || line };
  return { speaker: 'System', text: line };
}

/** Accepts string | array | null -> [{speaker, text}] (possibly empty). */
export function parseTranscript(raw) {
  if (raw == null) return [];
  if (Array.isArray(raw)) {
    const out = [];
    for (const item of raw) {
      if (item == null) continue;
      if (typeof item === 'string') {
        const turn = lineToTurn(item);
        if (turn) out.push(turn);
      } else if (typeof item === 'object') {
        const role = String(item.speaker ?? item.role ?? '').toLowerCase();
        const speaker = /ai|agent|assistant/.test(role) ? 'Kyron AI' : /caller|human|user|patient/.test(role) ? 'Patient' : 'System';
        const text = String(item.text ?? item.message ?? item.content ?? '').trim();
        if (text && !isTemplate(text)) out.push({ speaker, text });
      }
    }
    return out;
  }
  return String(raw)
    .split('\n')
    .map(lineToTurn)
    .filter(Boolean);
}

// ---------------------------------------------------------------------------
// Calls
// ---------------------------------------------------------------------------

const cleanStr = (v, fallback = null) => {
  if (v == null) return fallback;
  const s = String(v).trim();
  return s && !isTemplate(s) ? s : fallback;
};

export function normalizeAppointment(raw) {
  if (!raw || typeof raw !== 'object') return null;
  return {
    id: raw.id ?? null,
    doctor_name: cleanStr(raw.doctor_name, 'Specialist'),
    location_code: cleanStr(raw.location_code, 'MAIN'),
    location_name: cleanStr(raw.location_name, cleanStr(raw.location_code, 'Clinic')),
    appointment_time: cleanStr(raw.formatted_time) || cleanStr(raw.appointment_time, 'Time to be confirmed'),
    body_part: cleanStr(raw.body_part),
    issue_type: cleanStr(raw.issue_type),
    instructions: cleanStr(raw.notes, 'Please arrive 15 minutes early with photo identification and insurance card.'),
  };
}

export function normalizeCall(raw = {}) {
  const bodyPart = cleanStr(raw.body_part) || cleanStr(raw.detected_body_part);
  const issueType = cleanStr(raw.issue_type) || cleanStr(raw.detected_issue_type);
  const summary = cleanStr(raw.summary);
  const transcriptLines = parseTranscript(raw.transcript);
  const appointment = normalizeAppointment(raw.appointment);

  const doctorName = appointment?.doctor_name;
  const concern = bodyPart && issueType ? `${bodyPart} (${issueType})` : bodyPart || issueType || 'an unspecified concern';

  return {
    id: raw.id,
    call_sid: cleanStr(raw.call_sid, raw.id != null ? `ID-${raw.id}` : '—'),
    caller_phone: cleanStr(raw.caller_phone, '—'),
    patient_id: raw.patient_id ?? null,
    patient_name: cleanStr(raw.patient_name, 'Unknown Caller'),
    status: cleanStr(raw.status, 'FAILED'),
    body_part: bodyPart,
    issue_type: issueType,
    duration_seconds: Number.isFinite(+raw.duration_seconds) ? +raw.duration_seconds : 0,
    created_at: raw.created_at || null,
    formatted_date: cleanStr(raw.formatted_date) || formatDateTime(raw.created_at),
    transcript_source: cleanStr(raw.transcript_source, 'Telephony Webhook'),
    summary,
    appointment,
    transcript: transcriptLines,
    soap: {
      subjective: summary || `Inbound call regarding ${concern}. No clinical summary was captured for this call.`,
      objective: `Voice intake via Kyron AI. Triage extracted: ${bodyPart || 'unknown body part'} / ${issueType || 'unknown issue type'}.`,
      assessment: appointment && doctorName
        ? `Protocol match: ${doctorName} confirmed for ${concern}.`
        : raw.status === 'REDIRECTED'
          ? 'Caller was redirected to the intake coordinator per practice protocol.'
          : 'No booking was completed on this call.',
      plan: appointment?.appointment_time
        ? `Confirmed consultation with ${doctorName} — ${appointment.appointment_time}.`
        : 'No appointment scheduled. Follow up via the callback number on file.',
    },
  };
}

// ---------------------------------------------------------------------------
// Doctors (GET /api/protocols/summary payloads)
// ---------------------------------------------------------------------------

/** Human-readable specialty derived from protocol coverage. */
export function deriveSpecialty(protocols = []) {
  const parts = [...new Set(protocols.map((p) => p.body_part).filter(Boolean))];
  if (parts.length === 0) return 'Orthopedic Care';
  const label = parts.slice(0, 3).join(' · ');
  return parts.length > 3 ? `${label} +${parts.length - 3} more` : `${label} Orthopedics`;
}

export function normalizeDoctor(raw = {}, locNameMap = {}, slots = []) {
  const protocols = Array.isArray(raw.protocols)
    ? raw.protocols.map((p) => ({
        body_part: cleanStr(p.body_part),
        // Backend: accepted_type. Mock: type. Accept both.
        type: cleanStr(p.accepted_type) || cleanStr(p.type),
      })).filter((p) => p.body_part && p.type)
    : [];
  const locations = Array.isArray(raw.locations)
    ? raw.locations.map((l) =>
        typeof l === 'string'
          ? { code: l, name: locNameMap[l] || l }
          : { code: l.code, name: l.name || locNameMap[l.code] || l.code },
      ).filter((l) => l.code)
    : [];

  const openSlots = slots.filter((s) => !s.is_booked);
  const next = openSlots
    .map((s) => s.start_time)
    .filter(Boolean)
    .sort()[0];

  return {
    id: raw.id,
    name: cleanStr(raw.name, 'Unknown Provider'),
    specialty: cleanStr(raw.specialty) || deriveSpecialty(protocols),
    accepts_new_patients: raw.accepts_new_patients !== false,
    locations,
    protocols,
    next_slot: cleanStr(raw.next_slot) || (next ? formatDateTime(next) : 'No open slots'),
    open_slots_count: Number.isFinite(+raw.open_slot_count)
      ? +raw.open_slot_count
      : Number.isFinite(+raw.open_slots_count)
        ? +raw.open_slots_count
        : openSlots.length,
    intake_criteria:
      cleanStr(raw.intake_criteria) ||
      (raw.accepts_new_patients === false
        ? 'Panel closed to new patients. Established follow-ups only — new referrals are redirected per practice protocol.'
        : 'Accepting new consultations and returning follow-ups. Protocol-driven routing applies.'),
  };
}

// ---------------------------------------------------------------------------
// Patients (aggregated client-side: no list endpoint exists)
// ---------------------------------------------------------------------------

/**
 * Build directory records from live calls + appointments. Backend patients
 * only carry {id,name,phone,date_of_birth,is_new_patient,created_at}, so the
 * chart shows honest values and "—" where the API has no field (no invented
 * MRN / insurance / email).
 */
export function buildPatientsFromCalls(calls = [], appointments = []) {
  const byKey = new Map();

  const apptsByPatient = new Map();
  for (const a of appointments) {
    if (a?.patient_id == null) continue;
    if (!apptsByPatient.has(a.patient_id)) apptsByPatient.set(a.patient_id, []);
    apptsByPatient.get(a.patient_id).push(a);
  }

  for (const call of calls) {
    const key = call.patient_id != null ? `id:${call.patient_id}` : `phone:${call.caller_phone}`;
    if (!byKey.has(key)) {
      byKey.set(key, {
        id: call.patient_id ?? key,
        patient_key: key,
        name: call.patient_name,
        phone: call.caller_phone,
        dob: '—',
        age: null,
        gender: '—',
        is_new_patient: null, // unknown from call payloads alone
        call_ids: [],
        clinicalTags: [],
      });
    }
    const rec = byKey.get(key);
    rec.call_ids.push(call.id);
    // Prefer the most complete display name seen for this chart.
    if (rec.name === 'Unknown Caller' && call.patient_name !== 'Unknown Caller') rec.name = call.patient_name;
    const tag = call.body_part && call.issue_type ? `${call.body_part} · ${call.issue_type}` : call.body_part || call.issue_type;
    if (tag && !rec.clinicalTags.includes(tag)) rec.clinicalTags.push(tag);
    if (call.patient_id != null && apptsByPatient.has(call.patient_id)) {
      rec.appointment_count = apptsByPatient.get(call.patient_id).length;
    }
  }

  // Charts that only appear via appointments (booked outside a logged call).
  for (const [pid, list] of apptsByPatient) {
    const key = `id:${pid}`;
    if (!byKey.has(key)) {
      const first = list[0];
      byKey.set(key, {
        id: pid,
        patient_key: key,
        name: first.patient_name || 'Unknown Caller',
        phone: '—',
        dob: '—',
        age: null,
        gender: '—',
        is_new_patient: null,
        call_ids: [],
        clinicalTags: [],
        appointment_count: list.length,
      });
    }
  }

  return [...byKey.values()].sort((a, b) => b.call_ids.length - a.call_ids.length);
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

export function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit', hour12: true,
  });
}

export function formatDuration(totalSeconds = 0) {
  const s = Math.max(0, Math.floor(+totalSeconds || 0));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

export function initialsOf(name = '') {
  return String(name)
    .replace(/^Dr\.\s*/i, '')
    .split(/\s+/)
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase() || '•';
}
