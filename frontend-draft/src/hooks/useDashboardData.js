import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/client';
import {
  buildPatientsFromCalls,
  normalizeAppointment,
  normalizeCall,
  normalizeDoctor,
} from '../api/normalize';
import { INITIAL_CALLS, INITIAL_PATIENTS, INITIAL_PHYSICIANS } from '../data/clinicalData';

const POLL_MS = 5000;
const PAGE_LIMIT = 100;

/** Demo fallback: run the same mock rows through the live normalizers. */
function demoSnapshot() {
  const calls = INITIAL_CALLS.map(normalizeCall);
  const appointments = calls.flatMap((c) => (c.appointment ? [{ ...c.appointment, patient_id: c.patient_id, patient_name: c.patient_name, status: 'SCHEDULED' }] : []));
  const total = calls.length;
  const scheduled = calls.filter((c) => c.status === 'SCHEDULED').length;
  return {
    calls,
    appointments,
    slotsByDoctor: {},
    metrics: {
      total,
      scheduled,
      redirected: calls.filter((c) => c.status === 'REDIRECTED').length,
      abandoned: calls.filter((c) => c.status === 'ABANDONED').length,
      failed: calls.filter((c) => c.status === 'FAILED').length,
      conversion: total > 0 ? `${((scheduled / total) * 100).toFixed(1)}%` : '0.0%',
    },
    doctors: INITIAL_PHYSICIANS.map((d) => normalizeDoctor(d, {}, [])),
    locations: [
      { code: 'MAIN', name: 'Main Campus' },
      { code: 'NORTH', name: 'North Clinic' },
      { code: 'WEST', name: 'Westside Office' },
    ],
  };
}

export function useDashboardData() {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState(null);
  const [usingDemo, setUsingDemo] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const timer = useRef(null);
  const snapshotRef = useRef(null);

  const load = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true);
    try {
      const [callsRes, summaryRes, apptsRes, slotsRes] = await Promise.all([
        api.getCalls({ limit: PAGE_LIMIT }),
        api.getProtocolsSummary(),
        api.getAppointments(),
        api.getSlots({ limit: 50 }),
      ]);

      const rawCalls = Array.isArray(callsRes?.calls) ? callsRes.calls : [];
      const calls = rawCalls.map(normalizeCall);
      const byId = new Map(calls.map((c) => [c.id, c]));

      const locations = Array.isArray(summaryRes?.locations) ? summaryRes.locations : [];
      const locNameMap = Object.fromEntries(locations.map((l) => [l.code, l.name]));
      const rawSlots = Array.isArray(slotsRes?.slots) ? slotsRes.slots : [];
      const slotsByDoctor = {};
      for (const s of rawSlots) {
        if (s?.doctor_id == null) continue;
        (slotsByDoctor[s.doctor_id] ??= []).push(s);
      }
      const rawDoctors = Array.isArray(summaryRes?.doctors) ? summaryRes.doctors : [];
      const doctors = rawDoctors.map((d) => normalizeDoctor(d, locNameMap, slotsByDoctor[d.id] ?? []));

      const rawAppts = Array.isArray(apptsRes?.appointments) ? apptsRes.appointments : [];
      const appointments = rawAppts.map((a) => ({ ...normalizeAppointment(a), patient_id: a.patient_id ?? null, patient_name: a.patient_name ?? null, status: a.status ?? 'SCHEDULED' }));

      const m = callsRes?.metrics ?? {};
      const metrics = {
        total: m.total_calls ?? calls.length,
        scheduled: m.scheduled ?? calls.filter((c) => c.status === 'SCHEDULED').length,
        redirected: m.redirected ?? calls.filter((c) => c.status === 'REDIRECTED').length,
        abandoned: m.abandoned ?? calls.filter((c) => c.status === 'ABANDONED').length,
        failed: m.failed ?? calls.filter((c) => c.status === 'FAILED').length,
        conversion: typeof m.conversion_rate === 'string' ? m.conversion_rate : null,
      };

      setSnapshot({ calls, appointments, slotsByDoctor, metrics, doctors, locations, byId });
      setError(null);
      setUsingDemo(false);
      setLastUpdated(new Date());
    } catch (e) {
      // Keep last good data on poll failures; only hard-error the first load.
      setSnapshot((prev) => prev);
      setError((prevErr) => prevErr ?? e);
      if (!snapshotRef.current) {
        setError(e);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    snapshotRef.current = snapshot;
  }, [snapshot]);

  useEffect(() => {
    load();
    timer.current = setInterval(() => {
      if (!document.hidden) load({ quiet: true });
    }, POLL_MS);
    return () => clearInterval(timer.current);
  }, [load]);

  /** POST /api/calls/sync then reload. Never throws — returns {ok, message}. */
  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await api.syncCalls();
    } catch {
      // Sync is best-effort (Vogent may be unreachable); still reload local rows.
    }
    await load({ quiet: true });
    return true;
  }, [load]);

  /**
   * Run a live simulation through the backend routing + booking engine.
   * Returns the normalized new call record.
   */
  const simulate = useCallback(async (form) => {
    setSimulating(true);
    try {
      const payload = {
        caller_name: form.name.trim(),
        caller_phone: form.phone.trim(),
        is_new_patient: !!form.isNew,
        body_part: form.bodyPart,
        issue_type: form.issueType,
        preferred_doctor: form.doctor || null,
        // Backend accepts codes ("MAIN") or names ("Main Campus").
        preferred_location: form.location || null,
      };
      const res = await api.simulateCall(payload);
      await load({ quiet: true });
      const created = res?.call ? normalizeCall(res.call) : null;
      return { ok: true, status: res?.status ?? created?.status ?? 'SCHEDULED', call: created, callId: res?.call_id ?? created?.id };
    } catch (e) {
      return { ok: false, message: e.message || 'Simulation failed' };
    } finally {
      setSimulating(false);
    }
  }, [load]);

  const useDemoData = useCallback(() => {
    setSnapshot(demoSnapshot());
    setUsingDemo(true);
    setError(null);
    setLoading(false);
    setLastUpdated(new Date());
  }, []);

  const retryLive = useCallback(async () => {
    setError(null);
    setLoading(true);
    await load();
  }, [load]);

  const patients = useMemo(() => {
    if (!snapshot) return [];
    if (usingDemo) {
      // Preview-only path: rich mock charts, linked to demo calls by chart.
      const callIdsByChart = new Map();
      for (const c of snapshot.calls) {
        const key = c.patient_id != null ? String(c.patient_id) : c.caller_phone;
        if (!callIdsByChart.has(key)) callIdsByChart.set(key, []);
        callIdsByChart.get(key).push(c.id);
      }
      return INITIAL_PATIENTS.map((p) => ({
        id: p.id,
        patient_key: `id:${p.id}`,
        name: p.name,
        phone: p.phone,
        dob: p.dob,
        age: p.age,
        gender: p.gender,
        email: p.email,
        address: p.address,
        insurance: p.insurance,
        emergencyContact: p.emergencyContact,
        notes: p.notes,
        is_new_patient: p.is_new_patient,
        call_ids: callIdsByChart.get(String(p.id)) ?? callIdsByChart.get(p.phone) ?? [],
        clinicalTags: p.clinicalTags ?? [],
      }));
    }
    return buildPatientsFromCalls(snapshot.calls, snapshot.appointments);
  }, [snapshot, usingDemo]);

  return {
    calls: snapshot?.calls ?? [],
    appointments: snapshot?.appointments ?? [],
    doctors: snapshot?.doctors ?? [],
    locations: snapshot?.locations ?? [],
    metrics: snapshot?.metrics ?? null,
    patients,
    loading,
    refreshing,
    simulating,
    error: usingDemo ? null : error,
    usingDemo,
    lastUpdated,
    refresh,
    simulate,
    useDemoData,
    retryLive,
  };
}
