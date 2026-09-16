// Kyron Medical Voice Scheduling Agent - Call Review Dashboard Client

// Use relative origin if loaded via http/https; fallback to localhost if file://
const API_BASE = window.location.protocol.startsWith('http') ? '' : 'http://localhost:5000';

let allCalls = [];
let currentFilter = 'ALL';
let activeCallId = null;
let pollTimer = null;

// DOM Elements
const callsListEl = document.getElementById('calls-list');
const callsCountEl = document.getElementById('calls-count');
const inspectorEmptyEl = document.getElementById('inspector-empty');
const inspectorContentEl = document.getElementById('inspector-content');

// Metrics Elements
const metricTotalEl = document.getElementById('metric-total');
const metricScheduledEl = document.getElementById('metric-scheduled');
const metricRedirectedEl = document.getElementById('metric-redirected');
const metricAbandonedEl = document.getElementById('metric-abandoned');
const metricFailedEl = document.getElementById('metric-failed');
const metricConversionEl = document.getElementById('metric-conversion');

// Inspector Details Elements
const detailStatusEl = document.getElementById('detail-status');
const detailSourceBadgeEl = document.getElementById('detail-source-badge');
const transcriptSourceBadgeEl = document.getElementById('transcript-source-badge');
const detailSidEl = document.getElementById('detail-sid');
const detailDateEl = document.getElementById('detail-date');
const detailPatientNameEl = document.getElementById('detail-patient-name');
const detailPhoneEl = document.getElementById('detail-phone');
const detailDurationEl = document.getElementById('detail-duration');
const appointmentBannerEl = document.getElementById('appointment-banner');
const bannerPhysicianLocationEl = document.getElementById('banner-physician-location');
const bannerTimeEl = document.getElementById('banner-time');
const bannerBodyPartEl = document.getElementById('banner-body-part');
const bannerIssueTypeEl = document.getElementById('banner-issue-type');
const detailSummaryEl = document.getElementById('detail-summary');
const transcriptStreamEl = document.getElementById('transcript-stream');
const btnCopyTranscript = document.getElementById('btn-copy-transcript');

// Modal Elements
const modalBackdrop = document.getElementById('modal-backdrop');
const btnSimulate = document.getElementById('btn-simulate');
const btnModalClose = document.getElementById('btn-modal-close');
const btnModalCancel = document.getElementById('btn-modal-cancel');
const simForm = document.getElementById('sim-form');
const btnRefresh = document.getElementById('btn-refresh');

// Init
document.addEventListener('DOMContentLoaded', () => {
  fetchCalls();
  setupEventListeners();
  // Auto-refresh calls every 3 seconds so incoming test calls appear in real time
  pollTimer = setInterval(fetchCalls, 3000);
});

function setupEventListeners() {
  btnRefresh.addEventListener('click', async () => {
    btnRefresh.textContent = 'Syncing...';
    try {
      await fetch(`${API_BASE}/api/calls/sync`, { method: 'POST' });
    } catch (e) {}
    await fetchCalls();
    btnRefresh.textContent = 'Refresh';
  });

  // Filter tabs
  document.querySelectorAll('.filter-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.filter-tab').forEach((t) => t.classList.remove('active'));
      tab.classList.add('active');
      currentFilter = tab.dataset.status;
      renderCallsList();
    });
  });

  // Modal triggers
  btnSimulate.addEventListener('click', () => {
    modalBackdrop.style.display = 'flex';
  });

  const closeModal = () => {
    modalBackdrop.style.display = 'none';
  };
  btnModalClose.addEventListener('click', closeModal);
  btnModalCancel.addEventListener('click', closeModal);

  // Simulation Submit
  simForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      caller_name: document.getElementById('sim-name').value,
      caller_phone: document.getElementById('sim-phone').value,
      is_new_patient: document.getElementById('sim-patient-type').value === 'new',
      body_part: document.getElementById('sim-body-part').value,
      issue_type: document.getElementById('sim-issue-type').value,
      preferred_doctor: document.getElementById('sim-requested-doctor').value || null,
      preferred_location: document.getElementById('sim-location').value || null,
    };

    const submitBtn = document.getElementById('btn-modal-submit');
    submitBtn.textContent = 'Simulating call...';
    submitBtn.disabled = true;

    try {
      const res = await fetch(`${API_BASE}/api/calls/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        closeModal();
        await fetchCalls();
        if (data.call_id) {
          selectCall(data.call_id);
        }
      } else {
        alert('Simulation failed: Check server logs');
      }
    } catch (err) {
      console.error('Simulation error:', err);
      alert('Could not connect to API server.');
    } finally {
      submitBtn.textContent = 'Run Simulation';
      submitBtn.disabled = false;
    }
  });

  // Copy transcript (with fallback for non-secure http contexts)
  btnCopyTranscript.addEventListener('click', () => {
    const activeCall = allCalls.find((c) => c.id === activeCallId);
    if (activeCall && activeCall.transcript) {
      const done = () => {
        btnCopyTranscript.textContent = 'Copied!';
        setTimeout(() => {
          btnCopyTranscript.textContent = 'Copy Text';
        }, 1800);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(activeCall.transcript).then(done).catch(() => fallbackCopy(activeCall.transcript, done));
      } else {
        fallbackCopy(activeCall.transcript, done);
      }
    }
  });
}

function fallbackCopy(text, done) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
  } catch (e) {}
  document.body.removeChild(ta);
  if (done) done();
}

async function fetchCalls() {
  try {
    const res = await fetch(`${API_BASE}/api/calls`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Update metrics
    metricTotalEl.textContent = data.metrics.total_calls;
    metricScheduledEl.textContent = data.metrics.scheduled;
    metricRedirectedEl.textContent = data.metrics.redirected;
    metricAbandonedEl.textContent = data.metrics.abandoned;
    metricFailedEl.textContent = data.metrics.failed;
    metricConversionEl.textContent = `${data.metrics.conversion_rate} booking conversion`;

    const previousTopId = allCalls.length > 0 ? allCalls[0].id : null;
    allCalls = data.calls || [];
    renderCallsList();

    // Keep the reviewer's current selection stable across auto-refresh:
    // only auto-select when nothing is selected (or the selected call
    // disappeared). Never yank the inspector away to a newer call.
    if (allCalls.length > 0) {
      if (!activeCallId || !allCalls.some((c) => c.id === activeCallId)) {
        selectCall(allCalls[0].id);
      } else {
        selectCall(activeCallId);
      }
    } else {
      inspectorEmptyEl.style.display = 'block';
      inspectorContentEl.style.display = 'none';
    }
  } catch (err) {
    console.error('Failed to load calls:', err);
    callsListEl.innerHTML = `<div class="empty-state">Unable to load calls. Ensure backend is running.</div>`;
  }
}

function getSourceClass(source) {
  if (!source) return 'source-webhook';
  if (source.includes('Sync')) return 'source-sync';
  if (source.includes('Simulation')) return 'source-sim';
  return 'source-webhook';
}

function renderCallsList() {
  const filtered = currentFilter === 'ALL'
    ? allCalls
    : allCalls.filter((c) => c.status === currentFilter);

  callsCountEl.textContent = `${filtered.length} call${filtered.length === 1 ? '' : 's'}`;

  if (filtered.length === 0) {
    callsListEl.innerHTML = `<div class="empty-state">No ${currentFilter.toLowerCase()} calls found.</div>`;
    return;
  }

  callsListEl.innerHTML = filtered
    .map((call) => {
      const activeClass = call.id === activeCallId ? 'active' : '';
      const summaryText = call.summary || 'No summary recorded';
      const patientLabel = call.patient_name || call.caller_phone;
      const src = call.transcript_source || 'Vogent Telephony Webhook';

      return `
        <div class="call-item ${activeClass}" onclick="selectCall(${call.id})">
          <div class="call-item-top">
            <span class="caller-name">${escapeHtml(patientLabel)}</span>
            <span class="status-pill ${call.status}">${call.status}</span>
          </div>
          <div class="call-item-meta">
            <span class="call-item-time">${formatDate(call.created_at)}</span>
            <span class="source-tag">${escapeHtml(src)}</span>
            ${call.detected_body_part ? `<span>• ${call.detected_body_part}</span>` : ''}
            ${call.detected_issue_type ? `<span>(${call.detected_issue_type})</span>` : ''}
          </div>
          <p class="call-item-summary">${escapeHtml(summaryText)}</p>
        </div>
      `;
    })
    .join('');
}

function selectCall(callId) {
  activeCallId = callId;
  const call = allCalls.find((c) => c.id === callId);
  if (!call) return;

  // Update active state in list
  document.querySelectorAll('.call-item').forEach((el) => el.classList.remove('active'));
  const activeItem = document.querySelector(`.call-item[onclick="selectCall(${callId})"]`);
  if (activeItem) activeItem.classList.add('active');

  // Render Inspector
  inspectorEmptyEl.style.display = 'none';
  inspectorContentEl.style.display = 'flex';

  detailStatusEl.className = `status-pill ${call.status}`;
  detailStatusEl.textContent = call.status;

  const src = call.transcript_source || 'Vogent Telephony Webhook';
  const srcClass = getSourceClass(src);
  const srcHelp = src.includes('Webhook')
    ? 'Outcome reported by the voice flow itself (authoritative)'
    : src.includes('Sync')
      ? 'Transcript synced from Vogent dial history; outcome inferred when the flow never reported one'
      : 'Manually simulated call for protocol testing';
  if (detailSourceBadgeEl) {
    detailSourceBadgeEl.className = `source-badge ${srcClass}`;
    detailSourceBadgeEl.textContent = src;
    detailSourceBadgeEl.title = srcHelp;
  }
  if (transcriptSourceBadgeEl) {
    transcriptSourceBadgeEl.className = `source-badge ${srcClass}`;
    transcriptSourceBadgeEl.textContent = src;
    transcriptSourceBadgeEl.title = srcHelp;
  }

  detailSidEl.textContent = call.call_sid || `ID-${call.id}`;
  detailDateEl.textContent = call.formatted_date || formatDate(call.created_at);
  detailPatientNameEl.textContent = call.patient_name || 'Anonymous Caller';
  detailPhoneEl.textContent = call.caller_phone;
  detailDurationEl.textContent = formatDuration(call.duration_seconds || 0);

  // Appointment banner
  if (call.status === 'SCHEDULED' && call.appointment) {
    appointmentBannerEl.style.display = 'flex';
    bannerPhysicianLocationEl.textContent = `${call.appointment.doctor_name} • ${call.appointment.location_name}`;
    bannerTimeEl.textContent = call.appointment.formatted_time || call.appointment.appointment_time;
    bannerBodyPartEl.textContent = call.appointment.body_part || 'Clinical';
    bannerIssueTypeEl.textContent = call.appointment.issue_type || 'Consult';
  } else {
    appointmentBannerEl.style.display = 'none';
  }

  // Summary
  detailSummaryEl.textContent = call.summary || 'No clinical summary generated for this call.';

  // Transcript formatting
  renderTranscript(call.transcript);
}

function renderTranscript(rawTranscript) {
  if (!rawTranscript || rawTranscript.trim().startsWith('{{')) {
    transcriptStreamEl.innerHTML = '<div class="empty-state">No transcript recorded yet.</div>';
    return;
  }

  const lines = rawTranscript.split('\n').filter((l) => l.trim().length > 0);
  transcriptStreamEl.innerHTML = lines
    .map((line) => {
      const trimmed = line.trim();
      const isAgent = /^(Agent|AI|Assistant|\[AI\]|\[Agent\]):/i.test(trimmed);
      const isCaller = /^(Caller|Human|User|Patient|\[HUMAN\]|\[Caller\]):/i.test(trimmed);
      const speaker = isAgent ? 'Agent' : isCaller ? 'Caller' : 'System';
      const text = trimmed.replace(/^(\[?(Agent|AI|Assistant|Caller|Human|User|Patient)\]?):\s*/i, '');

      return `
        <div class="chat-bubble ${speaker.toLowerCase()}">
          <span class="bubble-speaker">${speaker}</span>
          <div class="bubble-text">${escapeHtml(text)}</div>
        </div>
      `;
    })
    .join('');
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return isoStr;
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
