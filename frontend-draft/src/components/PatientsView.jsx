import React, { useEffect, useMemo, useState } from 'react';
import {
  Search,
  User,
  Phone,
  Mail,
  MapPin,
  Shield,
  Calendar,
  ChevronRight,
  Copy,
} from 'lucide-react';
import { initialsOf } from '../api/normalize';
import { statusMeta } from './status';

export default function PatientsView({
  patients,
  calls,
  appointments,
  selectedPatientKey,
  onSelectPatientKey,
  onSelectCall,
  onShowToast,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('ALL');
  const [localKey, setLocalKey] = useState(selectedPatientKey);
  const [expandedCallId, setExpandedCallId] = useState(null);

  useEffect(() => {
    if (selectedPatientKey) setLocalKey(selectedPatientKey);
  }, [selectedPatientKey]);

  const filteredPatients = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return patients.filter((p) => {
      if (filterType === 'NEW' && p.is_new_patient !== true) return false;
      if (filterType === 'ESTABLISHED' && p.is_new_patient !== false) return false;
      if (!q) return true;
      return (
        p.name.toLowerCase().includes(q) ||
        String(p.phone ?? '').toLowerCase().includes(q) ||
        String(p.dob ?? '').toLowerCase().includes(q)
      );
    });
  }, [patients, searchQuery, filterType]);

  const selectedPatient = useMemo(
    () => patients.find((p) => p.patient_key === localKey) || filteredPatients[0] || patients[0] || null,
    [patients, localKey, filteredPatients],
  );

  const patientCalls = useMemo(() => {
    if (!selectedPatient) return [];
    return calls.filter((c) => {
      if (selectedPatient.id != null && typeof selectedPatient.id === 'number') {
        if (c.patient_id === selectedPatient.id) return true;
      }
      if (selectedPatient.phone && selectedPatient.phone !== '—' && c.caller_phone === selectedPatient.phone) return true;
      return c.patient_name === selectedPatient.name;
    });
  }, [calls, selectedPatient]);

  const patientAppointments = useMemo(() => {
    if (!selectedPatient) return [];
    const fromLedger = typeof selectedPatient.id === 'number'
      ? appointments.filter((a) => a.patient_id === selectedPatient.id)
      : [];
    const seen = new Set(fromLedger.map((a) => a.id));
    const fromCalls = patientCalls
      .filter((c) => c.appointment && !seen.has(c.appointment.id))
      .map((c) => ({ ...c.appointment, status: c.status }));
    return [...fromLedger, ...fromCalls];
  }, [appointments, patientCalls, selectedPatient]);

  const selectPatient = (key) => {
    setLocalKey(key);
    onSelectPatientKey?.(key);
  };

  const copyPatientChart = () => {
    if (!selectedPatient) return;
    navigator.clipboard?.writeText(
      [
        'KYRON MEDICAL - PATIENT SUMMARY',
        `Name: ${selectedPatient.name}`,
        `DOB: ${selectedPatient.dob} | Phone: ${selectedPatient.phone}`,
        selectedPatient.email ? `Email: ${selectedPatient.email}` : null,
        selectedPatient.address ? `Address: ${selectedPatient.address}` : null,
        selectedPatient.insurance?.provider ? `Insurance: ${selectedPatient.insurance.provider}` : null,
        (selectedPatient.clinicalTags?.length ?? 0) > 0 ? `Tags: ${selectedPatient.clinicalTags.join(', ')}` : null,
      ].filter(Boolean).join('\n'),
    );
    onShowToast?.(`✓ Patient summary for ${selectedPatient.name} copied to clipboard`);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start min-w-0">
      {/* Directory */}
      <section className="lg:col-span-4 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col min-h-[420px] max-h-[75vh] lg:max-h-none lg:h-[calc(100vh-16rem)]">
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 space-y-3 shrink-0">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 min-w-0">
              <User className="w-4 h-4 text-blue-600 shrink-0" />
              <span className="truncate">Patient Directory</span>
            </h2>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-mono whitespace-nowrap shrink-0">
              {filteredPatients.length} {filteredPatients.length === 1 ? 'patient' : 'patients'}
            </span>
          </div>
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by name, phone, DOB..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="flex items-center gap-1.5 text-xs overflow-x-auto pb-1 -mx-1 px-1">
            {[
              { v: 'ALL', label: 'All Records' },
              { v: 'ESTABLISHED', label: 'Established' },
              { v: 'NEW', label: 'New Intakes' },
            ].map((f) => (
              <button
                key={f.v}
                onClick={() => setFilterType(f.v)}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors whitespace-nowrap shrink-0 ${
                  filterType === f.v ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto divide-y divide-slate-100">
          {filteredPatients.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm">
              <User className="w-8 h-8 mx-auto text-slate-300 mb-2" />
              No matching patient records found.
            </div>
          ) : (
            filteredPatients.map((patient) => {
              const isSelected = selectedPatient?.patient_key === patient.patient_key;
              return (
                <div
                  key={patient.patient_key}
                  onClick={() => selectPatient(patient.patient_key)}
                  className={`p-3.5 cursor-pointer transition-colors flex items-start gap-3 hover:bg-slate-50 min-w-0 ${
                    isSelected ? 'bg-blue-50/70 border-l-4 border-blue-600' : 'border-l-4 border-transparent'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
                    isSelected ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700 border border-slate-200'
                  }`}>
                    {initialsOf(patient.name)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 min-w-0">
                      <span className="font-semibold text-slate-900 text-sm truncate min-w-0">{patient.name}</span>
                      <span className="text-xs font-mono text-slate-500 whitespace-nowrap shrink-0">
                        {typeof patient.id === 'number' ? `#${patient.id}` : '—'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500 min-w-0">
                      <span className="truncate">{patient.phone}</span>
                      <span aria-hidden className="shrink-0">•</span>
                      <span className="whitespace-nowrap shrink-0">DOB: {patient.dob}</span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-2 min-w-0">
                      <PanelPill isNew={patient.is_new_patient} />
                      {(patient.clinicalTags?.length ?? 0) > 0 && (
                        <span className="text-[11px] text-slate-500 truncate min-w-0">{patient.clinicalTags[0]}</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* Chart */}
      <section className="lg:col-span-8 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col min-h-[420px] lg:h-[calc(100vh-16rem)]">
        {selectedPatient ? (
          <>
            <div className="p-5 border-b border-slate-200 bg-slate-50/50 flex flex-wrap items-center justify-between gap-4 shrink-0">
              <div className="flex items-center gap-4 min-w-0 flex-1 basis-64">
                <div className="w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-base shadow-sm shrink-0">
                  {initialsOf(selectedPatient.name)}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <h1 className="text-xl font-bold text-slate-900 tracking-tight break-words min-w-0">{selectedPatient.name}</h1>
                    {typeof selectedPatient.id === 'number' && (
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-semibold whitespace-nowrap">Chart #{selectedPatient.id}</span>
                    )}
                    <PanelPill isNew={selectedPatient.is_new_patient} long />
                  </div>
                  <p className="text-xs text-slate-500 mt-1 break-words">
                    {selectedPatient.gender ?? '—'} • DOB: {selectedPatient.dob}
                    {selectedPatient.age != null ? ` (${selectedPatient.age} years old)` : ''}
                    {` • ${patientCalls.length} call${patientCalls.length === 1 ? '' : 's'} on file`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-wrap shrink-0">
                <button
                  onClick={copyPatientChart}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors whitespace-nowrap"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Summary</span>
                </button>
                {selectedPatient.phone && selectedPatient.phone !== '—' && (
                  <a
                    href={`tel:${selectedPatient.phone}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap"
                  >
                    <Phone className="w-3.5 h-3.5" />
                    <span>Call Patient</span>
                  </a>
                )}
              </div>
            </div>

            <div className="p-4 sm:p-6 overflow-y-auto space-y-6 flex-1 min-h-0">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 min-w-0">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 shrink-0" /> Contact Information
                  </h3>
                  <div className="space-y-2 text-sm text-slate-700 min-w-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <Phone className="w-4 h-4 text-slate-400 shrink-0" />
                      <span className="font-medium text-slate-900 break-words min-w-0">{selectedPatient.phone}</span>
                    </div>
                    {selectedPatient.email && (
                      <div className="flex items-center gap-2 min-w-0">
                        <Mail className="w-4 h-4 text-slate-400 shrink-0" />
                        <span className="truncate min-w-0">{selectedPatient.email}</span>
                      </div>
                    )}
                    {selectedPatient.address && (
                      <div className="flex items-start gap-2 min-w-0">
                        <MapPin className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                        <span className="break-words min-w-0">{selectedPatient.address}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 min-w-0">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 shrink-0" /> Insurance & Contacts
                  </h3>
                  {selectedPatient.insurance ? (
                    <div className="space-y-1.5 text-xs text-slate-700 min-w-0">
                      <div className="break-words"><span className="text-slate-500">Payer:</span> <strong className="text-slate-900">{selectedPatient.insurance.provider}</strong></div>
                      <div><span className="text-slate-500">Policy ID:</span> <span className="font-mono text-slate-900 font-semibold break-all">{selectedPatient.insurance.policyNumber}</span></div>
                      <div><span className="text-slate-500">Status:</span> <span className="text-emerald-700 font-medium">{selectedPatient.insurance.status}</span></div>
                      {selectedPatient.emergencyContact && (
                        <div className="pt-2 border-t border-slate-200 mt-2 text-slate-600 break-words">
                          <span className="text-slate-500">Emergency Contact:</span> <strong>{selectedPatient.emergencyContact.name}</strong> ({selectedPatient.emergencyContact.relation}) • {selectedPatient.emergencyContact.phone}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">No payer information captured for this chart yet.</p>
                  )}
                </div>
              </div>

              {(selectedPatient.clinicalTags?.length ?? 0) > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {selectedPatient.clinicalTags.map((t) => (
                    <span key={t} className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 break-words">{t}</span>
                  ))}
                </div>
              )}

              <div className="min-w-0">
                <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-blue-600 shrink-0" />
                  <span>Clinical Appointments ({patientAppointments.length})</span>
                </h3>
                {patientAppointments.length === 0 ? (
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-500 text-center">
                    No clinical appointments currently scheduled for this patient.
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {patientAppointments.map((appt, idx) => (
                      <div key={appt.id ?? idx} className="bg-emerald-50/60 border border-emerald-200/80 rounded-lg p-3.5 flex flex-wrap items-start justify-between gap-3">
                        <div className="flex items-start gap-3 min-w-0 flex-1 basis-56">
                          <div className="w-8 h-8 rounded bg-emerald-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                            <Calendar className="w-4 h-4" />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-bold text-slate-900 text-sm break-words">{appt.doctor_name}</span>
                              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-semibold whitespace-nowrap">{appt.status || 'Confirmed'}</span>
                            </div>
                            <div className="text-xs text-slate-600 mt-0.5 break-words">
                              {appt.location_name}{appt.body_part ? ` • ${appt.body_part}${appt.issue_type ? ` (${appt.issue_type})` : ''}` : ''}
                            </div>
                            <div className="text-xs font-semibold text-emerald-800 mt-1 break-words">{appt.appointment_time}</div>
                          </div>
                        </div>
                        {appt.instructions && (
                          <div className="text-xs text-slate-500 max-w-xs italic break-words min-w-0">Instructions: {appt.instructions}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="min-w-0">
                <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                  <Phone className="w-4 h-4 text-blue-600 shrink-0" />
                  <span>Voice AI Call History ({patientCalls.length})</span>
                </h3>
                {patientCalls.length === 0 ? (
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-500 text-center">
                    No recorded voice calls on file for this patient.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {patientCalls.map((call) => {
                      const isExpanded = expandedCallId === call.id;
                      const meta = statusMeta(call.status);
                      return (
                        <div key={call.id} className="bg-white border border-slate-200 rounded-lg overflow-hidden min-w-0">
                          <div className="p-3.5 flex flex-wrap items-center justify-between gap-3 bg-slate-50/40">
                            <div className="flex items-center gap-2 flex-wrap text-xs min-w-0">
                              <span className={`font-semibold px-2 py-0.5 rounded-full whitespace-nowrap shrink-0 ${meta.solid}`}>{call.status}</span>
                              <span className="font-mono text-slate-500 font-semibold break-all">{call.call_sid}</span>
                              {(call.body_part || call.issue_type) && (
                                <span className="text-slate-600 font-medium break-words">
                                  {call.body_part}{call.body_part && call.issue_type ? ` (${call.issue_type})` : call.issue_type ? `(${call.issue_type})` : ''}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              <button onClick={() => onSelectCall?.(call.id)} className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors whitespace-nowrap">
                                Open in Calls →
                              </button>
                              {call.transcript.length > 0 && (
                                <button onClick={() => setExpandedCallId(isExpanded ? null : call.id)} className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 transition-colors whitespace-nowrap">
                                  <span>{isExpanded ? 'Hide Transcript' : 'View Transcript'}</span>
                                  <ChevronRight className={`w-3.5 h-3.5 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                                </button>
                              )}
                            </div>
                          </div>
                          <div className="p-3.5 text-xs border-t border-slate-100 break-words min-w-0">
                            <strong className="text-slate-900 font-semibold">Clinical Summary:</strong>{' '}
                            <span className="text-slate-700">{call.summary || 'No summary captured.'}</span>
                          </div>
                          {isExpanded && call.transcript.length > 0 && (
                            <div className="p-4 bg-slate-900 text-slate-100 border-t border-slate-200 text-xs space-y-3 max-h-72 overflow-y-auto">
                              {call.transcript.map((line, lIdx) => (
                                <div key={lIdx} className="space-y-0.5 min-w-0">
                                  <span className={`font-bold text-[11px] tracking-wide uppercase ${
                                    line.speaker === 'Kyron AI' ? 'text-blue-400' : line.speaker === 'Patient' ? 'text-emerald-400' : 'text-slate-400'
                                  }`}>
                                    {line.speaker}:
                                  </span>
                                  <p className="text-slate-200 text-xs leading-relaxed pl-2 border-l border-slate-700 break-words">{line.text}</p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {selectedPatient.notes && (
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 text-xs text-slate-700 space-y-2 min-w-0">
                  <h4 className="font-bold text-slate-900 uppercase tracking-wider">Intake Notes</h4>
                  <p className="text-slate-600 break-words">{selectedPatient.notes}</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
            <User className="w-12 h-12 mb-3 text-slate-300" />
            <p className="font-medium text-slate-600">No patient selected</p>
            <p className="text-xs text-slate-400 mt-1">Select a patient record from the directory.</p>
          </div>
        )}
      </section>
    </div>
  );
}

function PanelPill({ isNew, long = false }) {
  if (isNew === true) {
    return (
      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 whitespace-nowrap shrink-0">
        {long ? 'New Patient Intake' : 'New Patient'}
      </span>
    );
  }
  if (isNew === false) {
    return (
      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 whitespace-nowrap shrink-0">
        {long ? 'Established Patient' : 'Established'}
      </span>
    );
  }
  return (
    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 whitespace-nowrap shrink-0">
      On file
    </span>
  );
}
