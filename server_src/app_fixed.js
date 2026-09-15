// AI生成



/* ECS Security Assessment Console — JavaScript */







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







    // Try modern Clipboard API first (requires secure context / HTTPS)



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







// Fallback copy for non-secure contexts (HTTP, remote port-forward)



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


        showResult('❌ Error: ' + e.message, 'error');



    }

}



// Stop assessment button
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







document.getElementById('assessment-form')?.addEventListener('submit', async (e) => {



    e.preventDefault();



    const serverIds = Array.from(document.querySelectorAll('input[name="server-ids"]:checked')).map(cb => cb.value);



    if (serverIds.length === 0) {



        showResult('❌ Please select at least one server.', 'error');



        return;



    }



    if (serverIds.length > 10) {



        showResult('❌ Maximum 10 servers per task.', 'error');



        return;



    }



    const benchmarks = Array.from(document.querySelectorAll('input[name="benchmark-select"]:checked')).map(cb => cb.value);



    if (benchmarks.length === 0) {



        showResult('❌ Please select at least one benchmark.', 'error');



        return;



    }







    const btn = document.getElementById('run-assessment-btn');



    btn.disabled = true;



    btn.innerHTML = '<span class="spinner"></span> Running assessment...';







    const stopBtn = document.getElementById('stop-assessment-btn');



    if (stopBtn) {



        stopBtn.style.display = 'inline-block';



        stopBtn.disabled = false;



        stopBtn.innerHTML = '⏹️ Stop Assessment';



    }







    const terminalCard = document.getElementById('terminal-card');



    const terminalOut = document.getElementById('terminal-output');



    const fill = document.getElementById('terminal-progress-fill');



    const badge = document.getElementById('terminal-progress-badge');







    if (terminalCard) terminalCard.style.display = 'block';



    if (terminalOut) terminalOut.textContent = '🚀 Initializing live progress terminal...\n';



    if (fill) fill.style.width = '5%';



    if (badge) {



        badge.textContent = '5%';



        badge.style.background = '#1e88e5';



    }







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