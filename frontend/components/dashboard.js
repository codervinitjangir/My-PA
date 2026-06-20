let dashboardCache = null;
let lastDashboardFetch = 0;
const CACHE_TTL = 30000; // 30 seconds

async function loadDashboard() {
    const now = Date.now();
    const chatMessages = document.getElementById("chat-messages");
    
    // Check cache
    if (dashboardCache && (now - lastDashboardFetch) < CACHE_TTL) {
        renderDashboard(dashboardCache);
        return;
    }

    try {
        const response = await fetch('/dashboard');
        if (!response.ok) throw new Error('Dashboard fetch failed');
        const data = await response.json();
        
        // Update cache
        dashboardCache = data;
        lastDashboardFetch = now;
        
        renderDashboard(data);
    } catch (err) {
        console.error("Dashboard error:", err);
    }
}

function renderDashboard(data) {
    let dashboardContainer = document.getElementById("jarvis-dashboard-card");
    const welcomeScreen = document.getElementById("welcome-screen");
    
    if (!dashboardContainer) {
        dashboardContainer = document.createElement("div");
        dashboardContainer.id = "jarvis-dashboard-card";
        dashboardContainer.className = "dashboard-card glass-panel";
        
        if (welcomeScreen && welcomeScreen.parentNode) {
            welcomeScreen.parentNode.insertBefore(dashboardContainer, welcomeScreen);
        } else {
            const chatMessages = document.getElementById("chat-messages");
            if(chatMessages) chatMessages.prepend(dashboardContainer);
        }
        
        // Render Command Center at the very top
        renderCommandCenter();
    }

    let briefAction = data.time_of_day === "morning" ? "Morning Brief" : 
                      data.time_of_day === "afternoon" ? "Afternoon Review" : "Evening Summary";

    dashboardContainer.innerHTML = `
        <div class="dashboard-header" style="display:flex; justify-content:space-between; align-items:center;">
            <h2>${data.greeting}</h2>
            <div style="display:flex; flex-direction:column; gap:4px; align-items:flex-end;">
                <div style="font-size: 0.8rem; background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.1);">
                    Telegram Bridge: ${data.telegram_enabled ? '🟢 Connected' : '🔴 Disconnected'}
                </div>
                ${data.wake_word ? `
                <div style="font-size: 0.8rem; background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.1); display:flex; align-items:center; gap:8px;">
                    <span>${data.wake_word.enabled ? '🟢' : '⚫'} Wake Word</span>
                    <span style="opacity:0.6; font-size:0.7rem;">Last Wake: ${data.wake_word.last_wake || 'Never'}</span>
                    <button onclick="toggleWakeWord()" style="background:var(--bg); border:1px solid rgba(255,255,255,0.2); color:white; border-radius:4px; cursor:pointer; padding:2px 6px;">Toggle ON/OFF</button>
                </div>
                ` : ''}
            </div>
        </div>
        <div class="dashboard-body">
            <div class="dashboard-section">
                <span class="dash-label">Current Focus:</span>
                <span class="dash-value">${data.current_focus}</span>
            </div>
            <div class="dashboard-section">
                <span class="dash-label">Active Project:</span>
                <span class="dash-value">${data.active_project}</span>
            </div>
            <div class="dashboard-section status-grid">
                <div class="dash-stat">CPU: ${data.computer_summary.cpu_usage}</div>
                <div class="dash-stat">RAM: ${data.computer_summary.memory_usage}</div>
                <div class="dash-stat">OS: ${data.computer_summary.os}</div>
                <div class="dash-stat">Pending: ${data.pending_items}</div>
            </div>
            ${data.timeline ? `
            <div class="dashboard-section timeline-widget">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span style="font-weight:bold;">Progress Timeline</span>
                    <span style="color:#0f8; font-weight:bold;">🔥 ${data.timeline.metrics.current_streak} Day Streak</span>
                </div>
                <div style="width:100%; background:rgba(255,255,255,0.1); border-radius:10px; height:8px; margin-bottom:10px;">
                    <div style="width:${data.timeline.metrics.progress_percentage}%; background:#0f8; height:100%; border-radius:10px;"></div>
                </div>
                <div style="font-size:0.85rem; opacity:0.8; display:flex; justify-content:space-between;">
                    <span>Completed: ${data.timeline.metrics.completed_count}</span>
                    <span>Pending: ${data.timeline.metrics.pending_count}</span>
                </div>
                ${data.timeline.metrics.milestones.length > 0 ? `<div style="margin-top:8px; color:gold; font-size:0.85rem;">🏆 ${data.timeline.metrics.milestones.join(', ')}</div>` : ''}
            </div>
            ` : ''}
            
            ${data.quick_links ? `
            <div class="dashboard-section quick-links-widget">
                <span style="font-weight:bold; display:block; margin-bottom:8px;">Quick Links</span>
                <div style="display:flex; flex-wrap:wrap; gap:8px;">
                    ${data.quick_links.map(link => `<button class="dash-btn" onclick="openSite('${link.site}')">${link.name}</button>`).join('')}
                </div>
            </div>
            ` : ''}
            
            ${data.top_sites && data.top_sites.length > 0 ? `
            <div class="dashboard-section top-sites-widget">
                <span style="font-weight:bold; display:block; margin-bottom:8px;">Most Used Sites</span>
                <ol style="margin:0; padding-left:20px; font-size:0.9rem;">
                    ${data.top_sites.map(s => `<li>${s.name} <span style="opacity:0.6">(${s.count} opens)</span></li>`).join('')}
                </ol>
            </div>
            ` : ''}
            
        </div>
    `;
    // Render screen card if state is available
    if (data.current_screen) renderScreenCard(data.current_screen);
}

function renderCommandCenter() {
    let container = document.getElementById("command-center-card");
    const welcomeScreen = document.getElementById("welcome-screen");
    const chatMessages = document.getElementById("chat-messages");

    if (!container) {
        container = document.createElement("div");
        container.id = "command-center-card";
        container.className = "command-center-card glass-panel";
        
        if (welcomeScreen && welcomeScreen.parentNode) {
            welcomeScreen.parentNode.insertBefore(container, welcomeScreen);
        } else if (chatMessages) {
            chatMessages.prepend(container);
        }
    }

    container.innerHTML = `
        <div class="command-center-header">
            <span style="font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; font-size: 0.85rem; color: var(--accent);">JARVIS Command Center</span>
        </div>
        <div class="command-actions">
            <button class="cmd-btn" onclick="openBriefingPanel()">🌅 Morning Brief</button>
            <button class="cmd-btn" onclick="sendDashboardAction('Continue Previous Session')">▶ Resume Session</button>
            <button class="cmd-btn" id="analyze-screen-btn" onclick="analyzeScreen()">👁 Analyze Screen</button>
            <button class="cmd-btn" onclick="sendDashboardAction('Open VS Code')">💻 Open Workspace</button>
            <button class="cmd-btn" onclick="scrollToQuickLinks()">🌐 Quick Links</button>
            <button class="cmd-btn" onclick="focusFriction()">📝 Add Friction</button>
            <button class="cmd-btn" onclick="forceRefreshDashboard()">🔄 Refresh</button>
        </div>
    `;
}

function scrollToQuickLinks() {
    const ql = document.querySelector('.quick-links-widget');
    if (ql) ql.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function focusFriction() {
    const input = document.getElementById('friction-input');
    if (input) {
        input.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => input.focus(), 300);
    }
}

function sendDashboardAction(message) {
    const input = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    if (input && sendBtn) {
        input.value = message;
        sendBtn.click();
    }
}

async function forceRefreshDashboard() {
    lastDashboardFetch = 0; // invalidate cache
    await loadDashboard();
}

async function openSite(siteAlias) {
    try {
        if (typeof showToast !== 'undefined') showToast(`Opening ${siteAlias}...`);
        
        const res = await fetch('/operator/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                action: 'open_site',
                payload: {site: siteAlias}
            })
        });
        const result = await res.json();
        if (!result.success && typeof showToast !== 'undefined') {
            showToast(`Failed: ${result.message}`);
        } else {
            setTimeout(forceRefreshDashboard, 500);
        }
    } catch (e) {
        console.error(e);
        if (typeof showToast !== 'undefined') showToast(`Error opening site`);
    }
}

async function toggleWakeWord() {
    try {
        const res = await fetch('/operator/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ action: 'toggle_wake_word' })
        });
        const result = await res.json();
        if (result.success && typeof showToast !== 'undefined') {
            showToast(result.enabled ? "Wake Word Enabled" : "Wake Word Disabled");
            setTimeout(forceRefreshDashboard, 500);
        }
    } catch (e) {
        console.error(e);
    }
}

async function openBriefingPanel() {
    try {
        const res = await fetch('/briefing');
        if (!res.ok) throw new Error('Briefing failed');
        const data = await res.json();
        const body = document.getElementById('briefing-body');
        if (body) {
            body.innerHTML = `
                <div class="brief-greeting">${data.greeting}</div>
                <div class="brief-section"><h4>Today Mode</h4><p>${data.today_mode}</p></div>
                <div class="brief-section"><h4>Energy Score</h4><p>${data.energy_score}</p></div>
                <div class="brief-section"><h4>Today's Focus</h4><p>${data.today_focus}</p></div>
                <div class="brief-section"><h4>Active Projects</h4>
                    <ul>${data.active_projects.map(p => `<li>${p}</li>`).join('')}</ul>
                </div>
                <div class="brief-section"><h4>Pending Tasks</h4><p>${data.pending_tasks} items require attention.</p></div>
                <div class="brief-section"><h4>Computer Status</h4><p>${data.computer_status}</p></div>
                <div class="brief-section brief-action">
                    <h4>Suggested Action</h4>
                    <button class="dash-btn" onclick="sendDashboardAction('${data.suggested_action}')">${data.suggested_action}</button>
                </div>
            `;
        }
        const panel = document.getElementById('briefing-panel');
        const overlay = document.getElementById('panel-overlay');
        if (panel && overlay) {
            panel.setAttribute('aria-hidden', 'false');
            overlay.setAttribute('aria-hidden', 'false');
        }
    } catch (e) { console.error(e); }
}

// Hook into page load
window.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    loadFrictions();
    loadUsage();
    setInterval(loadUsage, 30000);
    
    const closeBtn = document.getElementById('briefing-close');
    const panel = document.getElementById('briefing-panel');
    const overlay = document.getElementById('panel-overlay');
    if (closeBtn) closeBtn.addEventListener('click', () => {
        panel.setAttribute('aria-hidden', 'true');
        overlay.setAttribute('aria-hidden', 'true');
    });
});

// ── Friction Log ──────────────────────────────────────────────────────────────

async function loadFrictions() {
    try {
        const res = await fetch('/frictions');
        if (!res.ok) return;
        const items = await res.json();
        renderFrictions(items);
    } catch (e) { console.error('Friction fetch error:', e); }
}

function renderFrictions(items) {
    let container = document.getElementById('friction-log-card');
    const chatMessages = document.getElementById('chat-messages');
    const dashboard = document.getElementById('jarvis-dashboard-card');

    if (!container) {
        container = document.createElement('div');
        container.id = 'friction-log-card';
        container.className = 'friction-card glass-panel';
        // Insert after the dashboard card if it exists
        if (dashboard && dashboard.nextSibling) {
            chatMessages.insertBefore(container, dashboard.nextSibling);
        } else if (chatMessages) {
            chatMessages.appendChild(container);
        }
    }

    const openItems = items.filter(i => i.status === 'open');
    const resolvedItems = items.filter(i => i.status !== 'open');

    container.innerHTML = `
        <div class="friction-header">
            <span class="friction-title">Today's Frictions</span>
            <span class="friction-count">${openItems.length} open</span>
        </div>
        <div class="friction-list" id="friction-list">
            ${items.length === 0 ? `<div class="friction-empty">No friction logged. You're running smooth. ✓</div>` : ''}
            ${openItems.map(item => `
                <div class="friction-item" id="friction-${item.id}">
                    <span class="friction-checkbox" onclick="resolveFriction('${item.id}')" title="Mark as fixed">☐</span>
                    <span class="friction-text">${escapeHtml(item.text)}</span>
                    <button class="friction-delete" onclick="deleteFriction('${item.id}')" title="Delete">×</button>
                </div>
            `).join('')}
            ${resolvedItems.map(item => `
                <div class="friction-item friction-resolved" id="friction-${item.id}">
                    <span class="friction-checkbox" title="Resolved">☑</span>
                    <span class="friction-text">${escapeHtml(item.text)}</span>
                    <button class="friction-delete" onclick="deleteFriction('${item.id}')" title="Delete">×</button>
                </div>
            `).join('')}
        </div>
        <div class="friction-add">
            <input
                type="text"
                id="friction-input"
                class="friction-input"
                placeholder="Log a friction point..."
                maxlength="200"
                onkeydown="if(event.key==='Enter')addFriction()"
            />
            <button class="friction-add-btn" onclick="addFriction()">Add</button>
        </div>
    `;
}

function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function addFriction() {
    const input = document.getElementById('friction-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    input.disabled = true;
    try {
        const res = await fetch('/frictions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text})
        });
        if (res.ok) await loadFrictions();
    } catch (e) { console.error(e); }
    finally { input.disabled = false; input.focus(); }
}

async function resolveFriction(id) {
    try {
        const res = await fetch(`/frictions/${id}`, {method: 'PATCH'});
        if (res.ok) await loadFrictions();
    } catch (e) { console.error(e); }
}

async function deleteFriction(id) {
    try {
        const res = await fetch(`/frictions/${id}`, {method: 'DELETE'});
        if (res.ok) await loadFrictions();
    } catch (e) { console.error(e); }
}

// ── Usage Validation ──────────────────────────────────────────────────────────

async function loadUsage() {
    try {
        const res = await fetch('/usage');
        if (!res.ok) return;
        const data = await res.json();
        renderUsage(data);
    } catch (e) { console.error('Usage fetch error:', e); }
}

const FEATURE_LABELS = {
    dashboard_open:  'Dashboard',
    morning_brief:   'Morning Brief',
    screen_analysis: 'Screen Analysis',
    session_resume:  'Resume Session',
    browser_open:    'Browser Opens',
};

function renderUsage(data) {
    let container = document.getElementById('usage-card');
    const chatMessages = document.getElementById('chat-messages');
    const frictionCard = document.getElementById('friction-log-card');

    if (!container) {
        container = document.createElement('div');
        container.id = 'usage-card';
        container.className = 'usage-card glass-panel';
        if (frictionCard && frictionCard.nextSibling) {
            chatMessages.insertBefore(container, frictionCard.nextSibling);
        } else if (frictionCard) {
            chatMessages.appendChild(container);
        } else {
            const dash = document.getElementById('jarvis-dashboard-card');
            if (dash && dash.nextSibling) chatMessages.insertBefore(container, dash.nextSibling);
            else if (chatMessages) chatMessages.appendChild(container);
        }
    }

    const features = data.features || {};
    const sites = data.sites || {};
    const featureRows = Object.entries(FEATURE_LABELS)
        .map(([k, label]) => `
            <div class="usage-row">
                <span class="usage-label">${label}</span>
                <span class="usage-val">${features[k] || 0}</span>
            </div>`).join('');
    const siteRows = Object.entries(sites)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([k, v]) => `
            <div class="usage-row">
                <span class="usage-label">${k.charAt(0).toUpperCase() + k.slice(1)}</span>
                <span class="usage-val">${v}</span>
            </div>`).join('');

    const mostLabel  = data.most_used  ? (FEATURE_LABELS[data.most_used]  || data.most_used)  : '—';
    const leastLabel = data.least_used ? (FEATURE_LABELS[data.least_used] || data.least_used) : '—';

    container.innerHTML = `
        <div class="usage-header">
            <span class="usage-title">Today's Usage</span>
            <span class="usage-score">${data.score_label || '—'}</span>
        </div>
        <div class="usage-body">
            ${featureRows}
            ${siteRows ? `<div class="usage-divider">Quick Links</div>${siteRows}` : ''}
        </div>
        ${data.most_used || data.least_used ? `
        <div class="usage-footer">
            <span>Most used: <strong>${mostLabel}</strong></span>
            <span>Least used: <strong>${leastLabel}</strong></span>
        </div>` : ''}
    `;
}

// ── Screen Awareness ──────────────────────────────────────────────────────────

let _screenAnalyzing = false;

async function analyzeScreen() {
    if (_screenAnalyzing) return;
    _screenAnalyzing = true;
    const btn = document.getElementById('analyze-screen-btn');
    if (btn) { btn.textContent = '⏳ Analyzing...'; btn.disabled = true; }

    try {
        const res = await fetch('/operator/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({action: 'analyze_screen'})
        });
        const data = await res.json();

        if (data.error) {
            if (data.cooldown) {
                if (typeof showToast !== 'undefined') showToast(data.error);
            } else {
                if (typeof showToast !== 'undefined') showToast('Screen analysis failed.');
            }
        } else {
            renderScreenCard(data);
            if (typeof showToast !== 'undefined') showToast('Screen analyzed.');
        }
    } catch (e) {
        console.error('analyzeScreen error:', e);
        if (typeof showToast !== 'undefined') showToast('Screen analysis error.');
    } finally {
        _screenAnalyzing = false;
        if (btn) { btn.textContent = '👁 Analyze Screen'; btn.disabled = false; }
    }
}

function renderScreenCard(screen) {
    let container = document.getElementById('screen-card');
    const chatMessages = document.getElementById('chat-messages');
    const dashCard = document.getElementById('jarvis-dashboard-card');

    if (!container) {
        container = document.createElement('div');
        container.id = 'screen-card';
        container.className = 'screen-card glass-panel';
        if (dashCard && dashCard.nextSibling) {
            chatMessages.insertBefore(container, dashCard.nextSibling);
        } else if (chatMessages) {
            chatMessages.appendChild(container);
        }
    }

    const confidence = Math.round(screen.confidence || 0);
    const confColor = confidence >= 80 ? '#51cf66' : confidence >= 50 ? '#ffd43b' : '#ff6b6b';

    container.innerHTML = `
        <div class="screen-header">
            <span class="screen-title">Current Screen</span>
            <span class="screen-conf" style="color:${confColor}">${confidence}%</span>
        </div>
        <div class="screen-body">
            <div class="screen-row">
                <span class="screen-label">Application</span>
                <span class="screen-val">${escapeHtml(screen.application || 'Unknown')}</span>
            </div>
            <div class="screen-row">
                <span class="screen-label">Activity</span>
                <span class="screen-val">${escapeHtml(screen.activity || 'Unknown')}</span>
            </div>
            <div class="screen-row screen-summary-row">
                <span class="screen-label">Summary</span>
                <span class="screen-val screen-summary">${escapeHtml(screen.summary || '')}</span>
            </div>
        </div>
        <div class="screen-footer">
            <span class="screen-next-label">Next:</span>
            <span class="screen-next">${escapeHtml(screen.next_best_action || '')}</span>
        </div>
    `;
}
