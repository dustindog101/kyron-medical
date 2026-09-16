// ==========================================================================
// Kyron Medical — Backend API client (frontend-draft)
//
// The draft speaks ONLY to the existing Flask backend over /api/.... No
// telephony keys, no Vogent calls — sync/simulation all run server-side.
//
// API_BASE resolution:
//   - Production (EC2 / Docker): relative "" so the Flask server that serves
//     the built dist/ also answers /api/* on the same origin.
//   - Local dev (vite :5173): vite.config.js proxies /api -> localhost:5000.
//   - Override: VITE_API_BASE=https://54-90-91-169.sslip.io npm run dev
// ==========================================================================

export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');

async function req(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    // Non-JSON (proxy down, HTML error page) — surfaced below.
  }
  if (!res.ok) {
    const msg = (data && (data.message || data.error)) || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

const qs = (params = {}) => {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : '';
};

export const api = {
  getCalls: ({ status = 'ALL', limit = 100 } = {}) =>
    req(`/api/calls${qs({ status, limit })}`),

  getCall: (id) => req(`/api/calls/${id}`),

  /** Force a Vogent dial-history reconciliation, then returns fresh counts. */
  syncCalls: () => req('/api/calls/sync', { method: 'POST' }),

  /**
   * One-click end-to-end scenario runner (server-side routing + booking).
   * Payload: { caller_name, caller_phone, is_new_patient, body_part,
   *             issue_type, preferred_doctor|null, preferred_location|null }
   */
  simulateCall: (payload) =>
    req('/api/calls/simulate', { method: 'POST', body: payload }),

  /** { locations: [{code,name}], doctors: [{id,name,accepts_new_patients,locations,protocols}] } */
  getProtocolsSummary: () => req('/api/protocols/summary'),

  getAppointments: ({ patient_id, doctor_id } = {}) =>
    req(`/api/appointments${qs({ patient_id, doctor_id })}`),

  getSlots: ({ doctor_id, location_code, limit = 10 } = {}) =>
    req(`/api/slots${qs({ doctor_id, location_code, limit })}`),
};
