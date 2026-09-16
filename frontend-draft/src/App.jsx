import React, { useCallback, useEffect, useRef, useState } from 'react';
import Navbar from './components/Navbar';
import CallsView from './components/CallsView';
import PatientsView from './components/PatientsView';
import ProvidersView from './components/ProvidersView';
import ScheduleView from './components/ScheduleView';
import SimulatorModal from './components/SimulatorModal';
import { useDashboardData } from './hooks/useDashboardData';

export default function App() {
  const {
    calls, appointments, doctors, locations, metrics, patients,
    loading, refreshing, simulating, error, usingDemo, lastUpdated,
    refresh, simulate, useDemoData, retryLive,
  } = useDashboardData();

  const [activeTab, setActiveTab] = useState('calls');
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [selectedPatientKey, setSelectedPatientKey] = useState(null);
  const [isSimModalOpen, setIsSimModalOpen] = useState(false);
  const [simError, setSimError] = useState(null);
  const [toast, setToast] = useState(null);
  const toastTimer = useRef(null);

  const showToast = useCallback((message) => {
    setToast(message);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3200);
  }, []);

  useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current); }, []);

  // Keep the reviewer's selection stable across polling refreshes.
  useEffect(() => {
    if (calls.length === 0) {
      setSelectedCallId(null);
      return;
    }
    setSelectedCallId((prev) =>
      prev != null && calls.some((c) => c.id === prev) ? prev : calls[0].id,
    );
  }, [calls]);

  const handleNavigateToPatient = useCallback((patientKey) => {
    setSelectedPatientKey(patientKey);
    setActiveTab('patients');
  }, []);

  const handleRefresh = useCallback(async () => {
    if (usingDemo) {
      showToast('Demo data is static — reconnect to the live backend to sync');
      return;
    }
    await refresh();
    showToast('✓ Telephony & EHR appointments synchronized');
  }, [refresh, showToast, usingDemo]);

  const handleRunSimulation = useCallback(async (formData) => {
    setSimError(null);
    if (usingDemo) {
      setSimError('Demo mode is offline. Reconnect to the live backend to run simulations.');
      return;
    }
    const res = await simulate(formData);
    if (!res.ok) {
      setSimError(res.message || 'Simulation failed. Check that the backend is reachable.');
      return;
    }
    setIsSimModalOpen(false);
    setActiveTab('calls');
    if (res.callId != null) setSelectedCallId(res.callId);
    showToast(`✓ Call logged: ${res.status} — dashboard updated from backend`);
  }, [simulate, showToast, usingDemo]);

  const firstLoad = loading && calls.length === 0 && !error && !usingDemo;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenSimulate={() => { setSimError(null); setIsSimModalOpen(true); }}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        callCount={calls.length}
        patientCount={patients.length}
        connected={!usingDemo && !error}
        usingDemo={usingDemo}
        lastUpdated={lastUpdated}
      />

      {/* Connection banners */}
      {error && !usingDemo && (
        <div className="bg-rose-50 border-b border-rose-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-rose-800 min-w-0">
              <strong className="font-bold">Backend unreachable</strong>
              <span className="hidden sm:inline"> — {error.message || 'could not load /api/calls'}. Start the Flask backend (port 5000) or check VITE_API_BASE.</span>
            </p>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={retryLive}
                className="px-3 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition-colors"
              >
                Retry
              </button>
              <button
                onClick={useDemoData}
                className="px-3 py-1.5 text-xs font-semibold text-rose-800 bg-white hover:bg-rose-100 rounded-lg border border-rose-300 transition-colors"
              >
                Preview with demo data
              </button>
            </div>
          </div>
        </div>
      )}
      {usingDemo && (
        <div className="bg-amber-50 border-b border-amber-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-amber-800">
              <strong className="font-bold">Demo preview mode</strong> — static sample data. Simulation and sync are disabled.
            </p>
            <button
              onClick={retryLive}
              className="px-3 py-1.5 text-xs font-semibold text-amber-900 bg-white hover:bg-amber-100 rounded-lg border border-amber-300 transition-colors shrink-0"
            >
              Reconnect live backend
            </button>
          </div>
        </div>
      )}

      <main className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 min-w-0">
        {firstLoad ? (
          <LoadingState />
        ) : calls.length === 0 && !usingDemo && !error ? (
          <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-sm">
            <p className="font-bold text-slate-900">No calls yet</p>
            <p className="text-xs text-slate-500 mt-1">Run a simulation or wait for an inbound call to appear here.</p>
            <button
              onClick={() => setIsSimModalOpen(true)}
              className="mt-4 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              Simulate first call
            </button>
          </div>
        ) : (
          <>
            {activeTab === 'calls' && (
              <CallsView
                calls={calls}
                metrics={metrics}
                selectedCallId={selectedCallId}
                onSelectCall={setSelectedCallId}
                onNavigateToPatient={handleNavigateToPatient}
                onShowToast={showToast}
              />
            )}
            {activeTab === 'patients' && (
              <PatientsView
                patients={patients}
                calls={calls}
                appointments={appointments}
                selectedPatientKey={selectedPatientKey}
                onSelectPatientKey={setSelectedPatientKey}
                onSelectCall={(id) => { setSelectedCallId(id); setActiveTab('calls'); }}
                onShowToast={showToast}
              />
            )}
            {activeTab === 'providers' && (
              <ProvidersView
                physicians={doctors}
                locations={locations}
                loading={loading}
                onShowToast={showToast}
              />
            )}
            {activeTab === 'schedule' && (
              <ScheduleView
                appointments={appointments}
                locations={locations}
                onShowToast={showToast}
              />
            )}
          </>
        )}
      </main>

      <SimulatorModal
        isOpen={isSimModalOpen}
        onClose={() => setIsSimModalOpen(false)}
        onRunSimulation={handleRunSimulation}
        physicians={doctors}
        running={simulating}
        error={simError}
      />

      {toast && (
        <div className="fixed bottom-5 right-5 z-50 bg-slate-900 text-white pl-4 pr-5 py-3 rounded-lg shadow-xl text-xs font-semibold flex items-center gap-2 border border-slate-700 max-w-[calc(100vw-2.5rem)]">
          <span className="break-words">{toast}</span>
        </div>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading dashboard">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 sm:gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="h-3 w-16 bg-slate-200 rounded animate-pulse" />
            <div className="h-7 w-12 bg-slate-200 rounded mt-3 animate-pulse" />
            <div className="h-3 w-24 bg-slate-100 rounded mt-2 animate-pulse" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl h-96 animate-pulse" />
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl h-96 animate-pulse" />
      </div>
      <p className="text-center text-xs text-slate-500">Connecting to backend API…</p>
    </div>
  );
}
