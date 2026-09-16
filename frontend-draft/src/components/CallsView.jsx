import React, { useMemo, useState } from 'react';
import {
  Phone,
  Search,
  Calendar,
  CheckCircle2,
  ArrowUpRight,
  AlertTriangle,
  Clock,
  FileText,
  Copy,
  MessageSquare,
  User,
  PhoneOff,
} from 'lucide-react';
import { CALL_FILTERS, sourceBadgeClass, sourceHelp, statusMeta } from './status';
import { formatDuration } from '../api/normalize';

const patientKeyOf = (call) =>
  call.patient_id != null ? `id:${call.patient_id}` : `phone:${call.caller_phone}`;

function copyText(text, onDone) {
  const done = () => onDone?.();
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
  } else {
    fallbackCopy(text, done);
  }
}

function fallbackCopy(text, done) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } catch { /* noop */ }
  document.body.removeChild(ta);
  done?.();
}

export default function CallsView({
  calls,
  metrics,
  selectedCallId,
  onSelectCall,
  onNavigateToPatient,
  onShowToast,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');

  const counts = useMemo(() => {
    if (metrics) {
      const conv = metrics.conversion ?? '—';
      return {
        total: metrics.total,
        scheduled: metrics.scheduled,
        redirected: metrics.redirected,
        triage: calls.filter((c) => c.status === 'TRIAGE').length,
        incomplete: (metrics.abandoned ?? 0) + (metrics.failed ?? 0),
        conversion: typeof conv === 'string' ? conv : `${conv}%`,
      };
    }
    const total = calls.length;
    const scheduled = calls.filter((c) => c.status === 'SCHEDULED').length;
    return {
      total,
      scheduled,
      redirected: calls.filter((c) => c.status === 'REDIRECTED').length,
      triage: calls.filter((c) => c.status === 'TRIAGE').length,
      incomplete: calls.filter((c) => c.status === 'ABANDONED' || c.status === 'FAILED').length,
      conversion: total > 0 ? `${Math.round((scheduled / total) * 100)}%` : '—',
    };
  }, [calls, metrics]);

  const filteredCalls = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return calls.filter((call) => {
      if (filterStatus !== 'ALL' && call.status !== filterStatus) return false;
      if (!q) return true;
      return (
        call.patient_name.toLowerCase().includes(q) ||
        call.caller_phone.toLowerCase().includes(q) ||
        (call.body_part && call.body_part.toLowerCase().includes(q)) ||
        (call.issue_type && call.issue_type.toLowerCase().includes(q)) ||
        (call.summary && call.summary.toLowerCase().includes(q))
      );
    });
  }, [calls, searchQuery, filterStatus]);

  const selectedCall =
    calls.find((c) => c.id === selectedCallId) || filteredCalls[0] || calls[0] || null;

  const copySOAPNote = () => {
    if (!selectedCall) return;
    copyText(
      [
        'KYRON MEDICAL - CLINICAL INTAKE NOTE (SOAP)',
        `Patient: ${selectedCall.patient_name} (${selectedCall.caller_phone})`,
        `Call SID: ${selectedCall.call_sid} | Status: ${selectedCall.status}`,
        `Provider: ${selectedCall.appointment?.doctor_name ?? 'Triage Team'}`,
        `Date: ${selectedCall.formatted_date}`,
        '',
        `SUBJECTIVE:\n${selectedCall.soap.subjective}`,
        '',
        `OBJECTIVE:\n${selectedCall.soap.objective}`,
        '',
        `ASSESSMENT:\n${selectedCall.soap.assessment}`,
        '',
        `PLAN:\n${selectedCall.soap.plan}`,
      ].join('\n'),
      () => onShowToast?.(`✓ Clinical note for ${selectedCall.patient_name} copied to clipboard`),
    );
  };

  const copyTranscript = () => {
    if (!selectedCall || selectedCall.transcript.length === 0) return;
    copyText(
      selectedCall.transcript.map((t) => `${t.speaker}: ${t.text}`).join('\n'),
      () => onShowToast?.('✓ Conversational transcript copied'),
    );
  };

  return (
    <div className="space-y-6 min-w-0">
      <MetricGrid counts={counts} />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: call feed */}
        <section className="lg:col-span-5 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col min-h-[420px] max-h-[75vh] lg:max-h-none lg:h-[calc(100vh-16rem)]">
          <div className="p-4 border-b border-slate-200 bg-slate-50/50 space-y-3 shrink-0">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 min-w-0">
                <Phone className="w-4 h-4 text-blue-600 shrink-0" />
                <span className="truncate">Inbound Call Logs</span>
              </h2>
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-mono whitespace-nowrap shrink-0">
                {filteredCalls.length} calls
              </span>
            </div>

            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder="Search patient, phone, body part, symptom..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="flex items-center gap-1.5 text-xs overflow-x-auto pb-1 -mx-1 px-1">
              {CALL_FILTERS.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setFilterStatus(f.value)}
                  className={`px-2.5 py-1 rounded-md font-medium transition-colors whitespace-nowrap shrink-0 ${
                    filterStatus === f.value
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto divide-y divide-slate-100">
            {filteredCalls.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">No matching call logs found.</div>
            ) : (
              filteredCalls.map((call) => {
                const isSelected = selectedCall?.id === call.id;
                const meta = statusMeta(call.status);
                const concern = call.body_part && call.issue_type
                  ? `${call.body_part} (${call.issue_type})`
                  : call.body_part || call.issue_type || 'Unspecified concern';
                return (
                  <div
                    key={call.id}
                    onClick={() => onSelectCall(call.id)}
                    className={`p-4 cursor-pointer transition-colors hover:bg-slate-50 ${
                      isSelected ? 'bg-blue-50/70 border-l-4 border-blue-600' : 'border-l-4 border-transparent'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1 min-w-0">
                      <span className="font-semibold text-slate-900 text-sm truncate min-w-0">{call.patient_name}</span>
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border whitespace-nowrap shrink-0 ${meta.pill}`}>
                        {call.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-x-2 gap-y-0.5 flex-wrap text-xs text-slate-500 mb-1.5">
                      <span className="truncate">{call.caller_phone}</span>
                      <span aria-hidden>•</span>
                      <span className="break-words">{concern}</span>
                      <span aria-hidden>•</span>
                      <span className="whitespace-nowrap">⏱ {formatDuration(call.duration_seconds)}</span>
                    </div>
                    <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed break-words">
                      {call.summary || 'Inbound call encounter logged.'}
                    </p>
                  </div>
                );
              })
            )}
          </div>
        </section>

        {/* Right: inspector */}
        <section className="lg:col-span-7 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col min-h-[420px] max-h-none lg:h-[calc(100vh-16rem)]">
          {selectedCall ? (
            <>
              <div className="p-5 border-b border-slate-200 bg-slate-50/50 flex flex-wrap items-start justify-between gap-4 shrink-0">
                <div className="min-w-0 flex-1 basis-64">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <h1 className="text-xl font-bold text-slate-900 tracking-tight break-words min-w-0">
                      {selectedCall.patient_name}
                    </h1>
                    <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full whitespace-nowrap shrink-0 ${statusMeta(selectedCall.status).solid}`}>
                      {selectedCall.status}
                    </span>
                    <span className="font-mono text-xs text-slate-500 font-semibold px-2 py-0.5 bg-slate-200 rounded break-all">
                      {selectedCall.call_sid}
                    </span>
                  </div>
                  <div className="flex items-center gap-x-2 gap-y-1 flex-wrap text-xs text-slate-500 mt-1.5">
                    <span className="break-words">Phone: <strong className="font-semibold">{selectedCall.caller_phone}</strong></span>
                    <span aria-hidden>•</span>
                    <span className="whitespace-nowrap">Duration: <strong className="font-semibold">{formatDuration(selectedCall.duration_seconds)}</strong></span>
                    <span aria-hidden>•</span>
                    <span className="whitespace-nowrap">{selectedCall.formatted_date}</span>
                    <span
                      title={sourceHelp(selectedCall.transcript_source)}
                      className={`text-[11px] font-medium px-2 py-0.5 rounded-full border whitespace-nowrap ${sourceBadgeClass(selectedCall.transcript_source)}`}
                    >
                      {selectedCall.transcript_source}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap shrink-0">
                  <button
                    onClick={() => onNavigateToPatient(patientKeyOf(selectedCall))}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors whitespace-nowrap"
                  >
                    <User className="w-3.5 h-3.5" />
                    <span>View Patient Chart →</span>
                  </button>
                  <button
                    onClick={copySOAPNote}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy SOAP Note</span>
                  </button>
                </div>
              </div>

              <div className="p-4 sm:p-6 overflow-y-auto space-y-6 flex-1 min-h-0">
                {selectedCall.appointment ? (
                  <div className="bg-emerald-50/80 border border-emerald-200 rounded-xl p-4 flex flex-wrap items-start justify-between gap-4">
                    <div className="flex items-start gap-3.5 min-w-0 flex-1 basis-64">
                      <div className="w-10 h-10 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0">
                        <Calendar className="w-5 h-5" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-bold text-slate-900 text-base">Appointment Confirmed</h3>
                          {(selectedCall.body_part || selectedCall.issue_type) && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-200/60 text-emerald-900 font-semibold break-words">
                              {selectedCall.body_part}{selectedCall.body_part && selectedCall.issue_type ? ` (${selectedCall.issue_type})` : selectedCall.issue_type ? `(${selectedCall.issue_type})` : ''}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-700 font-medium mt-0.5 break-words">
                          <strong>{selectedCall.appointment.doctor_name}</strong> • {selectedCall.appointment.location_name}
                        </div>
                        <div className="text-sm font-bold text-emerald-800 mt-1.5 break-words">
                          {selectedCall.appointment.appointment_time}
                        </div>
                        <p className="text-xs text-slate-600 mt-1 italic break-words">
                          Preparation: {selectedCall.appointment.instructions}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => onShowToast?.('✓ Synced with Practice EMR Calendar')}
                      className="px-3 py-1.5 text-xs font-semibold text-emerald-800 bg-emerald-100 hover:bg-emerald-200 rounded-lg border border-emerald-300 transition-colors whitespace-nowrap shrink-0"
                    >
                      Export to EMR
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600">
                    <PhoneOff className="w-4 h-4 text-slate-400 shrink-0" />
                    <span>No appointment was booked on this call{selectedCall.status === 'REDIRECTED' ? ' — caller was redirected per protocol' : ''}.</span>
                  </div>
                )}

                <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden">
                  <div className="px-4 py-2.5 bg-slate-100/70 border-b border-slate-200 flex items-center justify-between gap-2 flex-wrap">
                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5 min-w-0">
                      <FileText className="w-4 h-4 text-blue-600 shrink-0" />
                      <span className="truncate">Clinical Intake Documentation (SOAP)</span>
                    </span>
                    <span className="text-[11px] font-mono text-slate-500 whitespace-nowrap">Derived from call record</span>
                  </div>
                  <div className="p-4 space-y-3.5 text-xs">
                    <SoapBlock title="Subjective (S)" body={selectedCall.soap.subjective} />
                    <SoapBlock title="Objective (O)" body={selectedCall.soap.objective} />
                    <div>
                      <strong className="text-blue-700 font-bold uppercase tracking-wider block mb-1">Assessment (A) — Routing</strong>
                      <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-slate-900 text-xs leading-relaxed break-words">
                        {selectedCall.soap.assessment}
                        {selectedCall.status === 'REDIRECTED' && (
                          <div className="mt-2 pt-2 border-t border-blue-200 text-purple-900 font-medium">
                            🔒 <strong>Protocol Compliance:</strong> Enforced physician panel constraint.
                          </div>
                        )}
                      </div>
                    </div>
                    <SoapBlock title="Plan (P)" body={selectedCall.soap.plan} />
                  </div>
                </div>

                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <div className="px-4 py-2.5 bg-slate-100/70 border-b border-slate-200 flex items-center justify-between gap-2 flex-wrap">
                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5 min-w-0">
                      <MessageSquare className="w-4 h-4 text-blue-600 shrink-0" />
                      <span className="truncate">Telephony Transcript</span>
                    </span>
                    {selectedCall.transcript.length > 0 && (
                      <button onClick={copyTranscript} className="text-xs text-slate-600 hover:text-slate-900 font-semibold flex items-center gap-1 whitespace-nowrap">
                        <Copy className="w-3 h-3" />
                        <span>Copy Dialogue</span>
                      </button>
                    )}
                  </div>
                  {selectedCall.transcript.length === 0 ? (
                    <div className="p-6 text-center text-xs text-slate-500">No transcript recorded for this call yet.</div>
                  ) : (
                    <div className="p-4 bg-slate-900 text-slate-100 text-xs space-y-3 max-h-72 overflow-y-auto">
                      {selectedCall.transcript.map((line, idx) => (
                        <div key={idx} className="space-y-0.5 min-w-0">
                          <span className={`font-bold text-[11px] tracking-wide uppercase ${
                            line.speaker === 'Kyron AI' ? 'text-blue-400' : line.speaker === 'Patient' ? 'text-emerald-400' : 'text-slate-400'
                          }`}>
                            {line.speaker}:
                          </span>
                          <p className="text-slate-200 text-xs leading-relaxed pl-2 border-l border-slate-700 break-words">
                            {line.text}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
              <Phone className="w-12 h-12 mb-3 text-slate-300" />
              <p className="font-medium text-slate-600">Select a call from the list</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function SoapBlock({ title, body }) {
  return (
    <div className="min-w-0">
      <strong className="text-blue-700 font-bold uppercase tracking-wider block mb-1">{title}</strong>
      <p className="text-slate-800 text-sm leading-relaxed pl-2 border-l-2 border-blue-400 break-words">{body}</p>
    </div>
  );
}

function MetricGrid({ counts }) {
  const cards = [
    { label: 'Total Calls', value: counts.total, sub: 'Inbound patient volume', icon: Phone, iconCls: 'text-blue-500', valueCls: 'text-slate-900' },
    { label: 'Scheduled', value: counts.scheduled, sub: `${counts.conversion} booking rate`, icon: CheckCircle2, iconCls: 'text-emerald-500', valueCls: 'text-emerald-600' },
    { label: 'Redirected', value: counts.redirected, sub: 'Protocol safe-routing', icon: ArrowUpRight, iconCls: 'text-purple-500', valueCls: 'text-purple-600' },
    { label: 'Nurse Triage', value: counts.triage, sub: 'Urgent red-flag transfers', icon: AlertTriangle, iconCls: 'text-amber-500', valueCls: 'text-amber-600' },
    { label: 'Incomplete', value: counts.incomplete, sub: 'Dropped / failed calls', icon: Clock, iconCls: 'text-rose-500', valueCls: 'text-rose-600' },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 sm:gap-4">
      {cards.map(({ label, value, sub, icon: Icon, iconCls, valueCls }) => (
        <div key={label} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm min-w-0">
          <div className="flex items-center justify-between gap-2 text-xs text-slate-500 font-medium uppercase tracking-wider min-w-0">
            <span className="truncate">{label}</span>
            <Icon className={`w-4 h-4 shrink-0 ${iconCls}`} />
          </div>
          <div className={`text-2xl font-extrabold mt-2 tabular-nums ${valueCls}`}>{value}</div>
          <p className="text-xs text-slate-500 mt-1 truncate">{sub}</p>
        </div>
      ))}
    </div>
  );
}
