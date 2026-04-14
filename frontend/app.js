// Triunfo MVP — Frontend App
'use strict';

const API = '';  // same origin, served by FastAPI

// ---- State ----
let selectedFile = null;
let currentDocId = null;
let currentResult = null;
let previewUrl = null;

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  loadHistory();
});

// ---- Health check ----
async function checkHealth() {
  const badge = document.getElementById('health-badge');
  try {
    const res = await fetch(`${API}/health`);
    if (res.ok) {
      badge.textContent = '● Sistema activo';
      badge.className = 'header-badge healthy';
    } else {
      badge.textContent = '● Error en API';
      badge.className = 'header-badge error';
    }
  } catch {
    badge.textContent = '● API desconectada';
    badge.className = 'header-badge error';
  }
}

// ---- View routing ----
function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(`view-${name}`).classList.add('active');
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const link = document.getElementById(`nav-${name}`);
  if (link) link.classList.add('active');
  if (name === 'history') loadHistory();
}

// ---- File handling ----
function handleDrop(e) {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) setFile(file);
}

function setFile(file) {
  selectedFile = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);

  document.getElementById('preview-img').src = previewUrl;
  document.getElementById('preview-name').textContent = file.name;
  document.getElementById('preview-size').textContent = formatBytes(file.size);
  document.getElementById('preview-area').classList.remove('hidden');
  document.getElementById('drop-zone').classList.add('hidden');
  document.getElementById('btn-process').disabled = false;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ---- Process document ----
async function processDocument() {
  if (!selectedFile) return;

  const btn = document.getElementById('btn-process');
  btn.disabled = true;

  document.getElementById('progress-area').classList.remove('hidden');
  setStage('classified', 'active');

  const formData = new FormData();
  formData.append('file', selectedFile);
  const providerHint = document.getElementById('provider-hint').value;
  const qualityHint = document.getElementById('quality-hint').value;
  if (providerHint) formData.append('provider_hint', providerHint);
  formData.append('quality_hint', qualityHint);

  try {
    setStage('classified', 'done');
    setStage('processing', 'active');

    const res = await fetch(`${API}/upload`, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error al procesar');
    }

    setStage('processing', 'done');
    setStage('validated', 'active');
    const result = await res.json();

    setStage('validated', 'done');
    setStage('routed', 'done');

    currentDocId = result.document_id;
    currentResult = result;

    setTimeout(() => renderResults(result), 400);
  } catch (err) {
    alert(`Error: ${err.message}`);
    btn.disabled = false;
    document.getElementById('progress-area').classList.add('hidden');
  }
}

function setStage(stageId, state) {
  const el = document.getElementById(`stage-${stageId}`);
  if (!el) return;
  el.className = `stage ${state}`;
}

// ---- Render results ----
function renderResults(result) {
  showView('results');

  // Image
  if (previewUrl) {
    document.getElementById('result-img').src = previewUrl;
  }
  document.getElementById('result-filename').textContent =
    result.ingestion?.file_name || 'documento.jpg';
  document.getElementById('result-provider-badge').textContent =
    `${result.provider || 'Desconocido'} — ${result.category || ''}`;

  // Panel A: Extracted fields
  renderFieldsTable(result);

  // Panel B: Model metrics
  renderMetrics(result);

  // Panel C: Validations
  renderValidations(result);

  // Panel D: Routing
  renderRouting(result);
}

// ---- Panel A ----
function renderFieldsTable(result) {
  const tbody = document.getElementById('fields-tbody');
  tbody.innerHTML = '';

  const fields = result.extracted_fields || {};
  const agents = result.agent_outputs || {};

  const confBadge = document.getElementById('confidence-global');
  const score = result.confidence_score || 0;
  confBadge.textContent = `Score: ${(score * 100).toFixed(1)}%`;
  confBadge.style.background = score >= 0.88 ? 'rgba(34,197,94,.2)' :
                                score >= 0.70 ? 'rgba(234,179,8,.2)' : 'rgba(239,68,68,.2)';
  confBadge.style.color = score >= 0.88 ? '#22c55e' :
                          score >= 0.70 ? '#eab308' : '#ef4444';

  // Ordenar campos: críticos primero
  const criticals = ['provider_name', 'issue_date', 'total_amount', 'reference_number'];
  const allFields = Object.keys(fields);
  const ordered = [...criticals.filter(f => allFields.includes(f)),
                   ...allFields.filter(f => !criticals.includes(f))];

  for (const fname of ordered) {
    const cf = fields[fname];
    if (!cf) continue;

    const tr = document.createElement('tr');
    const conf = cf.confidence || 0;
    const confClass = conf >= 0.85 ? 'conf-high' : conf >= 0.70 ? 'conf-med' : 'conf-low';
    const isCritical = criticals.includes(fname);

    // Valores por agente
    const agentConfs = {};
    for (const aid of ['docai', 'tesseract', 'vertex']) {
      const out = agents[aid];
      if (out && out.fields && out.fields[fname]) {
        agentConfs[aid] = out.fields[fname];
      }
    }

    tr.innerHTML = `
      <td><span class="field-name${isCritical ? ' text-green' : ''}">${formatFieldName(fname)}</span></td>
      <td><span class="${cf.value != null ? 'field-value monospace' : 'field-null'}">${formatValue(cf.value)}</span></td>
      <td>
        <div class="conf-cell ${confClass}">
          <div class="conf-bar"><div class="conf-fill" style="width:${(conf*100).toFixed(0)}%"></div></div>
          <span class="conf-val">${(conf * 100).toFixed(0)}%</span>
        </div>
      </td>
      <td><span class="source-tag">${cf.source || '—'}</span></td>
      ${['docai', 'tesseract', 'vertex'].map(aid => {
        const fv = agentConfs[aid];
        if (!fv) return `<td><span class="agent-na">N/A</span></td>`;
        const c = fv.confidence || 0;
        const col = c >= 0.85 ? '#22c55e' : c >= 0.70 ? '#eab308' : '#ef4444';
        return `<td><span class="agent-conf" style="color:${col}" onclick="showAgentDetail('${aid}', '${fname}')">${(c*100).toFixed(0)}%</span></td>`;
      }).join('')}
    `;
    tbody.appendChild(tr);
  }
}

function formatFieldName(name) {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatValue(val) {
  if (val === null || val === undefined) return 'N/A';
  if (Array.isArray(val)) return `[${val.length} items]`;
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
}

// ---- Panel B ----
function renderMetrics(result) {
  const grid = document.getElementById('metrics-grid');
  const timeline = document.getElementById('pipeline-timeline');
  const summary = result.processing_summary || {};

  const totalMs = summary.total_duration_ms || 0;
  const modelsUsed = summary.models_used || [];
  const stages = summary.stages || [];

  grid.innerHTML = `
    <div class="metric-card">
      <div class="metric-label">Tiempo Total</div>
      <div class="metric-value">${(totalMs / 1000).toFixed(2)}</div>
      <div class="metric-unit">segundos</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Modelos usados</div>
      <div class="metric-value">${modelsUsed.length}</div>
      <div class="metric-unit">${modelsUsed.join(', ') || '—'}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Confidence</div>
      <div class="metric-value" style="color:${scoreColor(result.confidence_score)}">${((result.confidence_score || 0) * 100).toFixed(1)}%</div>
      <div class="metric-unit">score global</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Campos faltantes</div>
      <div class="metric-value">${(summary.missing_fields || []).length}</div>
      <div class="metric-unit">de ${Object.keys(result.extracted_fields || {}).length} totales</div>
    </div>
  `;

  const maxMs = Math.max(...stages.map(s => s.duration_ms), 1);
  timeline.innerHTML = stages.map(s => {
    const pct = Math.max(2, (s.duration_ms / maxMs) * 100);
    const color = s.status === 'SUCCESS' ? '#3b82f6' :
                  s.status === 'SKIPPED' ? '#2a3248' :
                  s.status === 'FAILED' ? '#ef4444' : '#f97316';
    const statusClass = `status-${(s.status || 'unknown').toLowerCase()}`;
    return `
      <div class="timeline-item">
        <span class="tl-name">${s.name}</span>
        <div class="tl-bar-wrap"><div class="tl-bar" style="width:${pct}%;background:${color}"></div></div>
        <span class="tl-ms">${s.duration_ms}ms</span>
        <span class="tl-status ${statusClass}">${s.status}</span>
      </div>
    `;
  }).join('');
}

function scoreColor(score) {
  if (score >= 0.88) return '#22c55e';
  if (score >= 0.70) return '#eab308';
  return '#ef4444';
}

// ---- Panel C ----
function renderValidations(result) {
  const val = result.validation || {};
  const errors = val.errors || [];
  const warnings = val.warnings || [];
  const missing = result.processing_summary?.missing_fields || [];

  const statusEl = document.getElementById('validation-status');
  if (errors.length > 0) {
    statusEl.textContent = `✗ FALLIDAS (${errors.length} error${errors.length > 1 ? 'es' : ''})`;
    statusEl.className = 'validation-status failed';
  } else if (warnings.length > 0) {
    statusEl.textContent = `⚠ WARNINGS (${warnings.length})`;
    statusEl.className = 'validation-status warnings';
  } else {
    statusEl.textContent = '✓ PASADAS — Sin errores ni warnings';
    statusEl.className = 'validation-status passed';
  }

  const errEl = document.getElementById('validation-errors');
  errEl.innerHTML = errors.map(e => `<li>✗ ${e}</li>`).join('');

  const warnEl = document.getElementById('validation-warnings');
  warnEl.innerHTML = warnings.map(w => `<li>⚠ ${w}</li>`).join('');

  const missEl = document.getElementById('missing-fields');
  missEl.innerHTML = missing.length > 0
    ? `<span class="text-muted">Campos faltantes: ${missing.join(', ')}</span>`
    : '';
}

// ---- Panel D ----
function renderRouting(result) {
  const routing = result.routing || 'UNKNOWN';
  const reason = result.routing_reason || '';

  const decEl = document.getElementById('routing-decision');
  decEl.textContent = routing;
  decEl.className = `routing-decision ${routing}`;

  document.getElementById('routing-reason').textContent = reason;

  const actEl = document.getElementById('routing-actions');
  actEl.innerHTML = '';

  if (routing === 'AUTO_APPROVE') {
    const btn = document.createElement('button');
    btn.className = 'btn-green';
    btn.textContent = '✓ Enviar a SAP';
    btn.onclick = () => approveDocument();
    actEl.appendChild(btn);
  } else if (routing === 'HITL_STANDARD' || routing === 'HITL_PRIORITY') {
    const btn = document.createElement('button');
    btn.className = 'btn-primary';
    btn.textContent = 'Revisar manualmente';
    btn.disabled = true;
    actEl.appendChild(btn);
    const note = document.createElement('p');
    note.style.cssText = 'font-size:11px;color:var(--text-muted);margin-top:6px';
    note.textContent = 'HITL no implementado en MVP';
    actEl.appendChild(note);
  } else {
    const msg = document.createElement('p');
    msg.className = 'text-red';
    msg.style.fontSize = '12px';
    msg.textContent = 'Documento rechazado — no se puede enviar a SAP';
    actEl.appendChild(msg);
  }

  // Download buttons
  const dlDiv = document.createElement('div');
  dlDiv.style.cssText = 'display:flex;gap:8px;margin-top:8px;flex-wrap:wrap';

  const dlJsonBtn = document.createElement('button');
  dlJsonBtn.className = 'btn-ghost';
  dlJsonBtn.textContent = '⬇ JSON';
  dlJsonBtn.onclick = () => downloadJSON(result);
  dlDiv.appendChild(dlJsonBtn);

  const dlPdfBtn = document.createElement('button');
  dlPdfBtn.className = 'btn-ghost';
  dlPdfBtn.textContent = '⬇ PDF';
  dlPdfBtn.onclick = () => downloadPDF(result.document_id);
  dlDiv.appendChild(dlPdfBtn);

  actEl.appendChild(dlDiv);
}

// ---- SAP Approve ----
async function approveDocument() {
  if (!currentDocId) return;
  try {
    const res = await fetch(`${API}/document/${currentDocId}/approve`, { method: 'POST' });
    const data = await res.json();
    showSapModal(data);
    // Actualizar resultado
    if (data.status === 'SUCCESS') {
      currentResult.sap_response = data;
    }
  } catch (err) {
    alert(`Error al enviar a SAP: ${err.message}`);
  }
}

function showSapModal(data) {
  const modal = document.getElementById('sap-modal');
  const body = document.getElementById('sap-modal-body');

  let html = '';
  if (data.status === 'SUCCESS') {
    html = `
      <div class="sap-success">✓ Documento creado en SAP</div>
      <div class="modal-field-row"><span class="modal-field-key">Número SAP</span><span class="modal-field-val">${data.sap_document_number}</span></div>
      <div class="modal-field-row"><span class="modal-field-key">Fecha contabilización</span><span class="modal-field-val">${data.sap_posting_date}</span></div>
      <div class="modal-field-row"><span class="modal-field-key">Creado por</span><span class="modal-field-val">${data.audit?.created_by || 'TRIUNFO_SYSTEM'}</span></div>
    `;
  } else if (data.status === 'DUPLICATE') {
    html = `
      <div class="sap-duplicate">⚠ Documento duplicado en SAP</div>
      <div class="modal-field-row"><span class="modal-field-key">Doc existente</span><span class="modal-field-val">${data.sap_document_number}</span></div>
      <div class="modal-field-row"><span class="modal-field-key">Referencia</span><span class="modal-field-val">${data.existing_document?.reference_number || '—'}</span></div>
    `;
  } else {
    html = `
      <div class="sap-error">✗ Error SAP: ${data.status}</div>
      <div class="modal-field-row"><span class="modal-field-key">Mensaje</span><span class="modal-field-val">${data.message}</span></div>
      ${(data.errors || []).map(e => `<div class="modal-field-row"><span class="modal-field-val text-red">${e}</span></div>`).join('')}
    `;
  }

  body.innerHTML = html;
  modal.classList.remove('hidden');
}

// ---- Agent detail modal ----
function showAgentDetail(agentId, fieldName) {
  if (!currentResult) return;
  const agents = currentResult.agent_outputs || {};
  const agent = agents[agentId];
  if (!agent) return;

  const modal = document.getElementById('agent-modal');
  const body = document.getElementById('modal-body');
  document.getElementById('modal-title').textContent =
    `${agentId.toUpperCase()} — ${formatFieldName(fieldName)}`;

  const fields = agent.fields || {};
  let html = `
    <div class="modal-field-row"><span class="modal-field-key">Status</span><span class="modal-field-val">${agent.status}</span></div>
    <div class="modal-field-row"><span class="modal-field-key">Duración</span><span class="modal-field-val">${agent.duration_ms}ms</span></div>
    <div class="modal-field-row"><span class="modal-field-key">Modelo</span><span class="modal-field-val">${agent.metadata?.model_version || '—'}</span></div>
    <hr style="border-color:var(--border);margin:12px 0">
    <h4 style="margin-bottom:10px;font-size:12px;color:var(--text-muted)">CAMPOS EXTRAÍDOS</h4>
  `;

  for (const [fname, fv] of Object.entries(fields)) {
    if (!fv || fv.value == null) continue;
    const conf = fv.confidence || 0;
    const col = conf >= 0.85 ? '#22c55e' : conf >= 0.70 ? '#eab308' : '#ef4444';
    html += `
      <div class="modal-field-row">
        <span class="modal-field-key">${formatFieldName(fname)}</span>
        <span class="modal-field-val" style="display:flex;gap:8px;align-items:center">
          <span class="monospace">${formatValue(fv.value)}</span>
          <span style="color:${col};font-size:11px">${(conf*100).toFixed(0)}%</span>
        </span>
      </div>
    `;
  }

  if (agent.raw_text) {
    html += `<hr style="border-color:var(--border);margin:12px 0"><pre>${escapeHtml(agent.raw_text.substring(0, 500))}</pre>`;
  }

  body.innerHTML = html;
  modal.classList.remove('hidden');
}

// ---- History ----
async function loadHistory() {
  try {
    const res = await fetch(`${API}/documents`);
    if (!res.ok) return;
    const data = await res.json();
    renderHistory(data.documents || []);
  } catch {
    // API offline
  }
}

function renderHistory(docs) {
  const tbody = document.getElementById('history-tbody');
  if (!tbody) return;
  if (docs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:40px">Sin documentos procesados</td></tr>';
    return;
  }

  tbody.innerHTML = docs.map(d => {
    const chipClass = {
      AUTO_APPROVE: 'chip-green',
      HITL_STANDARD: 'chip-yellow',
      HITL_PRIORITY: 'chip-orange',
      AUTO_REJECT: 'chip-red',
    }[d.routing] || '';
    const conf = ((d.confidence_score || 0) * 100).toFixed(1);
    return `
      <tr>
        <td class="monospace">${escapeHtml(d.file_name || '—')}</td>
        <td>${escapeHtml(d.provider || '—')}</td>
        <td><span class="routing-chip ${chipClass}">${d.routing || '—'}</span></td>
        <td style="color:${scoreColor(d.confidence_score)}">${conf}%</td>
        <td class="text-muted">${formatTimestamp(d.uploaded_at)}</td>
        <td><button class="btn-ghost" onclick="viewDocument('${d.document_id}')">Ver →</button></td>
      </tr>
    `;
  }).join('');
}

async function viewDocument(docId) {
  try {
    const res = await fetch(`${API}/document/${docId}`);
    if (!res.ok) return;
    const result = await res.json();
    currentDocId = docId;
    currentResult = result;
    renderResults(result);
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

async function resetDocuments() {
  if (!confirm('¿Limpiar todos los documentos del historial?')) return;
  await fetch(`${API}/documents/reset`, { method: 'DELETE' });
  loadHistory();
}

// ---- Utilities ----
function closeModal(e) {
  if (e.target.classList.contains('modal')) {
    e.target.classList.add('hidden');
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatTimestamp(ts) {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleString('es-AR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

function downloadJSON(data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `triunfo-${data.document_id?.slice(0, 8) || 'result'}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

async function downloadPDF(docId) {
  try {
    const res = await fetch(`${API}/document/${docId}/pdf`);
    if (!res.ok) throw new Error('Error al descargar PDF');
    const data = await res.json();
    // Convertir base64 a blob
    const binaryString = atob(data.data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `triunfo-${docId.slice(0, 8)}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(`Error al descargar PDF: ${err.message}`);
  }
}
