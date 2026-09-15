/* ECS Security Assessment Console — JavaScript */

/* ── Theme toggle (light/dark) ──
   Persists the user's choice in localStorage and applies it by
   setting data-theme on <html>. The inline script in each page's
   <head> sets the attribute before CSS loads to prevent a flash;
   this function handles user-initiated toggling. */
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
}

// Apply saved theme on load (fallback if the inline head script didn't run)
(function() {
    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
})();

// Helper: show result message
function showResult(message, type = 'info') {
    const area = document.getElementById('result-area');
    if (!area) return;
    const cls = type === 'error' ? 'warn-box' : type === 'success' ? 'success-box' : 'info-box';
    area.innerHTML = `<div class="${cls}"><p>${message}</p></div>`;
}

// Helper: copy to clipboard
function copyToClipboard(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const text = el.textContent;
    const statusEl = document.getElementById('copy-status');
    const showCopyStatus = (msg, ok) => {
        if (statusEl) {
            statusEl.innerHTML = `<span style="color:${ok ? '#2e7d32' : '#c62828'}; font-weight:bold;">${msg}</span>`;
            if (ok) setTimeout(() => { statusEl.innerHTML = ''; }, 3000);
        } else {
            showResult(msg, ok ? 'success' : 'error');
        }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showCopyStatus('✅ Public key copied to clipboard!', true);
        }).catch(() => {
            _fallbackCopy(text, showCopyStatus);
        });
    } else {
        _fallbackCopy(text, showCopyStatus);
    }
}

// Fallback copy for non-secure contexts
function _fallbackCopy(text, showCopyStatus) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        showCopyStatus('✅ Public key copied to clipboard!', true);
    } catch (e) {
        showCopyStatus('❌ Failed to copy. Please copy manually.', false);
    }
    document.body.removeChild(textarea);
}

// Keypair: generate
async function generateKeypair() {
    showResult('<span class="spinner"></span> Generating keypair...', 'info');
    try {
        const resp = await fetch('/api/keypair/generate', { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showResult('✅ Keypair generated! Please install the public key on your ECS servers, then refresh this page.', 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showResult('❌ Failed: ' + (data.detail || 'Unknown error'), 'error');
        }
    } catch (e) {
        showResult('❌ Error: ' + e.message, 'error');
    }
}

// Servers: add
document.getElementById('add-server-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const server = {
        ip: document.getElementById('server-ip').value,
        ssh_port: parseInt(document.getElementById('server-ssh-port').value) || 22,
        ssh_username: document.getElementById('server-ssh-username').value || 'root',
    };
    try {
        const resp = await fetch('/api/servers/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(server),
        });
        const data = await resp.json();
        if (data.success) {
            showResult(`✅ Server ${server.ip} added successfully!`, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showResult('❌ Failed: ' + (data.detail || 'Unknown error'), 'error');
        }
    } catch (e) {
        showResult('❌ Error: ' + e.message, 'error');
    }
});

// Servers: remove
async function removeServer(serverId) {
    if (!confirm('Remove this server?')) return;
    try {
        const resp = await fetch(`/api/servers/${serverId}`, { method: 'DELETE' });
        const data = await resp.json();
        if (data.success) {
            showResult('✅ Server removed!', 'success');
            setTimeout(() => location.reload(), 1000);
        }
    } catch (e) {
        showResult('❌ Error: ' + e.message, 'error');
    }
}

// LLM Config: save
document.getElementById('llm-config-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const config = {
        api_key: document.getElementById('api-key').value,
        base_url: document.getElementById('base-url').value,
        model: document.getElementById('model-select').value,
        temperature: parseFloat(document.getElementById('temperature').value),
        rag_enabled: document.getElementById('rag-enabled').value === 'true',
    };
    try {
        const resp = await fetch('/api/config/llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });
        const data = await resp.json();
        if (data.success) {
            showResult('✅ LLM configuration saved!', 'success');
        } else {
            showResult('❌ Failed: ' + (data.detail || 'Unknown error'), 'error');
        }
    } catch (e) {
        showResult('❌ Error: ' + e.message, 'error');
    }
});

// Assessment: run & live terminal polling
let _currentTaskId = null;
let _currentPollInterval = null;

function _stopPolling() {
    if (_currentPollInterval) {
        clearInterval(_currentPollInterval);
        _currentPollInterval = null;
    }
}

async function pollTaskStatus(taskId, btn) {
    const terminalOut = document.getElementById('terminal-output');
    const fill = document.getElementById('terminal-progress-fill');
    const badge = document.getElementById('terminal-progress-badge');
    const stopBtn = document.getElementById('stop-assessment-btn');
    let processedLogsCount = 0;

    _stopPolling();

    const interval = setInterval(async () => {
        try {
            const resp = await fetch(`/api/assessment/status/${taskId}`);
            const data = await resp.json();

            if (data.logs && data.logs.length > processedLogsCount) {
                const newLogs = data.logs.slice(processedLogsCount);
                newLogs.forEach(l => { terminalOut.textContent += l + '\n'; });
                processedLogsCount = data.logs.length;
                terminalOut.scrollTop = terminalOut.scrollHeight;
            }

            const pct = data.progress || 0;
            if (fill) fill.style.width = pct + '%';
            if (badge) badge.textContent = pct + '%';

            if (data.status === 'completed') {
                _stopPolling();
                _currentTaskId = null;
                if (btn) { btn.disabled = false; btn.innerHTML = '🚀 Run Assessment'; }
                if (stopBtn) stopBtn.style.display = 'none';
                if (fill) fill.style.width = '100%';
                if (badge) { badge.textContent = '100%'; badge.style.background = '#2e7d32'; }
                const s = data.summary;
                showResult(`✅ Assessment completed successfully!<br>
                    Servers: ${s.total_servers || 1} | Successful: ${s.successful || 1} | Failed: ${s.failed || 0}<br>
                    Controls: ${s.total_controls || 0} | Compliant: ${s.compliant || 0} | Non-compliant: ${s.non_compliant || 0} | Unknown: ${s.unknown || 0}<br>
                    Compliance Rate: <strong>${s.compliance_rate || '0%'}</strong><br>
                    <a href="/api/report/${taskId}/html" target="_blank" class="btn btn-primary" style="margin-top:10px;">📄 View Report</a>`, 'success');
            } else if (data.status === 'cancelled') {
                _stopPolling();
                _currentTaskId = null;
                if (btn) { btn.disabled = false; btn.innerHTML = '🚀 Run Assessment'; }
                if (stopBtn) stopBtn.style.display = 'none';
                if (badge) { badge.style.background = '#ef6c00'; badge.textContent = 'CANCELLED'; }
                showResult('⏹️ Assessment was cancelled. Partial results may be available.', 'info');
            } else if (data.status === 'failed') {
                _stopPolling();
                _currentTaskId = null;
                if (btn) { btn.disabled = false; btn.innerHTML = '🚀 Run Assessment'; }
                if (stopBtn) stopBtn.style.display = 'none';
                if (badge) { badge.style.background = '#c62828'; badge.textContent = 'FAILED'; }
                showResult('❌ Assessment task failed: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (e) {
            console.error('Polling error:', e);
        }
    }, 800);
    _currentPollInterval = interval;
}

// Stop assessment button
document.getElementById('stop-assessment-btn')?.addEventListener('click', async () => {
    if (!_currentTaskId) return;
    if (!confirm('Are you sure you want to cancel the assessment?')) return;
    const stopBtn = document.getElementById('stop-assessment-btn');
    stopBtn.disabled = true;
    stopBtn.innerHTML = '<span class="spinner"></span> Cancelling...';
    try {
        const resp = await fetch(`/api/assessment/cancel/${_currentTaskId}`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            // The poll loop will pick up the cancelled status
        } else {
            showResult('❌ Failed to cancel: ' + (data.detail || 'Unknown error'), 'error');
            stopBtn.disabled = false;
            stopBtn.innerHTML = '⏹️ Stop Assessment';
        }
    } catch (e) {
        showResult('❌ Error: ' + e.message, 'error');
        stopBtn.disabled = false;
        stopBtn.innerHTML = '⏹️ Stop Assessment';
    }
});

// Assessment form submit
document.getElementById('assessment-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const serverIds = Array.from(document.querySelectorAll('input[name="server-ids"]:checked')).map(cb => cb.value);
    if (serverIds.length === 0) { showResult('❌ Please select at least one server.', 'error'); return; }
    if (serverIds.length > 10) { showResult('❌ Maximum 10 servers per task.', 'error'); return; }
    const benchmarks = Array.from(document.querySelectorAll('input[name="benchmark-select"]:checked')).map(cb => cb.value);
    if (benchmarks.length === 0) { showResult('❌ Please select at least one benchmark.', 'error'); return; }

    const btn = document.getElementById('run-assessment-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Running assessment...';
    const stopBtn = document.getElementById('stop-assessment-btn');
    if (stopBtn) { stopBtn.style.display = 'inline-block'; stopBtn.disabled = false; stopBtn.innerHTML = '⏹️ Stop Assessment'; }
    const terminalCard = document.getElementById('terminal-card');
    const terminalOut = document.getElementById('terminal-output');
    const fill = document.getElementById('terminal-progress-fill');
    const badge = document.getElementById('terminal-progress-badge');
    if (terminalCard) terminalCard.style.display = 'block';
    if (terminalOut) terminalOut.textContent = '🚀 Initializing live progress terminal...\n';
    if (fill) fill.style.width = '5%';
    if (badge) { badge.textContent = '5%'; badge.style.background = '#1e88e5'; }

    const req = {
        task_name: document.getElementById('task-name').value,
        server_ids: serverIds,
        benchmarks: benchmarks,
    };
    try {
        const resp = await fetch('/api/assessment/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req),
        });
        const data = await resp.json();
        if (data.success && data.task_id) {
            _currentTaskId = data.task_id;
            pollTaskStatus(data.task_id, btn);
        } else {
            showResult('❌ Assessment failed to start: ' + (data.detail || 'Unknown error'), 'error');
            btn.disabled = false;
            btn.innerHTML = '🚀 Run Assessment';
            if (stopBtn) stopBtn.style.display = 'none';
        }
    } catch (e) {
        showResult('❌ Error: ' + e.message, 'error');
        btn.disabled = false;
        btn.innerHTML = '🚀 Run Assessment';
        if (stopBtn) stopBtn.style.display = 'none';
    }
});

// Checklist: upload
document.getElementById('checklist-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    try {
        const resp = await fetch('/api/checklist/upload', { method: 'POST', body: formData });
        const data = await resp.json();
        if (data.success) {
            showResult(`✅ Checklist uploaded! ${data.item_count} items found.`, 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showResult('❌ Upload failed: ' + (data.detail || 'Unknown error'), 'error');
        }
    } catch (e) {
        showResult('❌ Error: ' + e.message, 'error');
    }
});

// Checklist: analyze
async function analyzeChecklist(checklistId) {
    showResult('<span class="spinner"></span> Analyzing checklist with LLM...', 'info');
    try {
        const resp = await fetch(`/api/checklist/${checklistId}/analyze`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            const a = data.analysis;
            let html = `<h4>Overall Assessment</h4><p>${a.overall_assessment || 'N/A'}</p>`;
            if (a.missing_controls?.length) {
                html += '<h4>Missing Controls</h4><ul>';
                a.missing_controls.forEach(c => html += `<li>${c}</li>`);
                html += '</ul>';
            }
            if (a.recommendations?.length) {
                html += '<h4>Recommendations</h4><ul>';
                a.recommendations.forEach(r => html += `<li>${r}</li>`);
                html += '</ul>';
            }
            showResult(html, 'success');
        } else {
            showResult('❌ Analysis failed: ' + (data.detail || 'Unknown error'), 'error');
        }
    } catch (e) {
        showResult('❌ Error: ' + e.message, 'error');
    }
}