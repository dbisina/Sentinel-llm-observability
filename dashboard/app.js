/* =====================================================
   SENTINEL DASHBOARD - JavaScript Application
   Real-time LLM Observability Dashboard
   ===================================================== */

// API Configuration - use relative paths since we're served from same origin
const API_BASE = '';

// State
let state = {
    isConnected: false,
    lastUpdate: null,
    metrics: {},
    anomalies: [],
    incidents: [],
    healthStatus: null,
    totalRequests: 0
};

// DOM Elements
const elements = {
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),
    lastUpdated: document.getElementById('lastUpdated'),
    totalTokens: document.getElementById('totalTokens'),
    tokensDelta: document.getElementById('tokensDelta'),
    avgLatency: document.getElementById('avgLatency'),
    latencyDelta: document.getElementById('latencyDelta'),
    totalCost: document.getElementById('totalCost'),
    costPerRequest: document.getElementById('costPerRequest'),
    totalRequests: document.getElementById('totalRequests'),
    throughput: document.getElementById('throughput'),
    metricsGrid: document.getElementById('metricsGrid'),
    anomaliesList: document.getElementById('anomaliesList'),
    anomalyCount: document.getElementById('anomalyCount'),
    incidentsList: document.getElementById('incidentsList'),
    healthGrid: document.getElementById('healthGrid'),
    promptInput: document.getElementById('promptInput'),
    sendPrompt: document.getElementById('sendPrompt'),
    chatResponse: document.getElementById('chatResponse'),
    chatStatus: document.getElementById('chatStatus'),
    refreshMetrics: document.getElementById('refreshMetrics'),
    triggerAnomaly: document.getElementById('triggerAnomaly')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    init();
});

async function init() {
    await fetchHealthStatus();
    await fetchMetricsSummary();
    setupEventListeners();
    startPolling();
}

// Event Listeners
function setupEventListeners() {
    elements.sendPrompt.addEventListener('click', sendChatRequest);
    elements.promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatRequest();
        }
    });
    elements.refreshMetrics.addEventListener('click', fetchMetricsSummary);

    // Trigger anomaly button
    if (elements.triggerAnomaly) {
        elements.triggerAnomaly.addEventListener('click', triggerAnomalyDemo);
    }
}

// Polling for real-time updates
function startPolling() {
    setInterval(async () => {
        await fetchHealthStatus();
        await fetchMetricsSummary();
    }, 10000); // Every 10 seconds
}

// API Calls
async function fetchHealthStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        state.isConnected = data.status === 'healthy';
        state.healthStatus = data;
        state.lastUpdate = new Date();

        updateStatusIndicator();
        updateHealthGrid(data);
        updateLastUpdated();
    } catch (error) {
        console.error('Health check failed:', error);
        state.isConnected = false;
        updateStatusIndicator();
    }
}

async function fetchMetricsSummary() {
    try {
        const response = await fetch(`${API_BASE}/metrics/summary`);
        const data = await response.json();

        // Extract data from correct structure
        const sessionStats = data.session_stats || {};
        const summary = data.summary || {};
        const recentAnomalies = data.recent_anomalies || [];

        state.metrics = sessionStats;
        state.anomalies = recentAnomalies;
        state.totalRequests = summary.total_requests || 0;

        updateStatsCards(sessionStats, summary);
        updateMetricsGrid(sessionStats);
        updateAnomaliesList(recentAnomalies);

        // Update request count
        elements.totalRequests.textContent = state.totalRequests;

    } catch (error) {
        console.error('Metrics fetch failed:', error);
    }
}

async function sendChatRequest() {
    const prompt = elements.promptInput.value.trim();
    if (!prompt) return;

    // Update UI state
    elements.sendPrompt.disabled = true;
    elements.chatStatus.textContent = 'Processing...';
    elements.chatStatus.style.background = 'var(--warning-light)';
    elements.chatStatus.style.color = 'var(--warning)';

    elements.chatResponse.innerHTML = `
        <div class="response-placeholder">
            <div class="skeleton" style="height: 16px; width: 100%; margin-bottom: 8px;"></div>
            <div class="skeleton" style="height: 16px; width: 80%; margin-bottom: 8px;"></div>
            <div class="skeleton" style="height: 16px; width: 60%;"></div>
        </div>
    `;

    try {
        const startTime = Date.now();
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        const data = await response.json();
        const clientLatency = Date.now() - startTime;

        // Update response display
        displayChatResponse(data, clientLatency);

        // Update anomalies if any detected
        if (data.anomalies_detected && data.anomalies_detected.length > 0) {
            state.anomalies = [...data.anomalies_detected, ...state.anomalies].slice(0, 10);
            updateAnomaliesList(state.anomalies);
        }

        // Update incidents if created
        if (data.incident_created) {
            state.incidents = [data.incident_created, ...state.incidents].slice(0, 5);
            updateIncidentsList(state.incidents);
        }

        // Refresh metrics
        await fetchMetricsSummary();

        elements.chatStatus.textContent = 'Ready';
        elements.chatStatus.style.background = 'var(--primary-100)';
        elements.chatStatus.style.color = 'var(--primary-700)';

    } catch (error) {
        console.error('Chat request failed:', error);
        elements.chatResponse.innerHTML = `
            <div style="color: var(--error); font-size: 14px;">
                Error: ${error.message || 'Failed to connect to API'}
            </div>
        `;

        elements.chatStatus.textContent = 'Error';
        elements.chatStatus.style.background = 'var(--error-light)';
        elements.chatStatus.style.color = 'var(--error)';
    } finally {
        elements.sendPrompt.disabled = false;
    }
}

// UI Update Functions
function updateStatusIndicator() {
    if (state.isConnected) {
        elements.statusDot.className = 'status-dot healthy';
        elements.statusText.textContent = 'Connected';
    } else {
        elements.statusDot.className = 'status-dot error';
        elements.statusText.textContent = 'Disconnected';
    }
}

function updateLastUpdated() {
    if (state.lastUpdate) {
        const time = state.lastUpdate.toLocaleTimeString();
        elements.lastUpdated.textContent = `Updated ${time}`;
    }
}

function updateStatsCards(sessionStats, summary) {
    // Total tokens from session stats (using session. prefix keys)
    const totalTokens = sessionStats['session.total_tokens'] || 0;
    const requestCount = summary.total_requests || 0;

    elements.totalTokens.textContent = formatNumber(totalTokens);
    elements.tokensDelta.textContent = requestCount > 0 ? `${requestCount} requests` : 'No requests yet';
    elements.tokensDelta.className = 'stat-delta positive';

    // Average latency
    const avgLatency = sessionStats['session.avg_latency_ms'] || 0;
    elements.avgLatency.textContent = avgLatency > 0 ? `${avgLatency.toFixed(0)}ms` : '--';
    elements.latencyDelta.textContent = avgLatency > 1000 ? 'High' : avgLatency > 0 ? 'Normal' : '--';
    elements.latencyDelta.className = avgLatency > 1000 ? 'stat-delta negative' : 'stat-delta positive';

    // Cost
    const avgCost = sessionStats['session.avg_cost_per_request'] || 0;
    const totalCost = sessionStats['session.total_cost'] || 0;
    elements.totalCost.textContent = totalCost > 0 ? `$${totalCost.toFixed(4)}` : '--';
    elements.costPerRequest.textContent = avgCost > 0 ? `avg $${avgCost.toFixed(5)}/req` : 'No cost data';

    // Throughput
    const avgThroughput = sessionStats['session.avg_throughput'] || 0;
    elements.throughput.textContent = avgThroughput > 0 ? `${avgThroughput.toFixed(0)} tok/s` : '--';
}

function updateMetricsGrid(sessionStats) {
    const metricsToShow = [
        { key: 'session.total_tokens', label: 'Total Tokens' },
        { key: 'session.avg_latency_ms', label: 'Avg Latency' },
        { key: 'session.avg_cost_per_request', label: 'Avg Cost' },
        { key: 'session.avg_throughput', label: 'Throughput' },
        { key: 'session.total_cost', label: 'Total Cost' },
        { key: 'session.min_latency_ms', label: 'Min Latency' },
        { key: 'session.max_latency_ms', label: 'Max Latency' },
        { key: 'session.request_count', label: 'Requests' }
    ];

    elements.metricsGrid.innerHTML = metricsToShow.map(m => {
        const value = sessionStats[m.key];
        const displayValue = value !== undefined && value !== null ? formatMetricValue(m.key, value) : '--';
        const shortLabel = m.label;
        return `
            <div class="metric-item">
                <div class="metric-name">${shortLabel}</div>
                <div class="metric-value">${displayValue}</div>
            </div>
        `;
    }).join('');
}

function updateAnomaliesList(anomalies) {
    elements.anomalyCount.textContent = anomalies.length;
    elements.anomalyCount.className = anomalies.length > 0 ? 'anomaly-count has-anomalies' : 'anomaly-count';

    if (anomalies.length === 0) {
        elements.anomaliesList.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span>No anomalies detected</span>
            </div>
        `;
        return;
    }

    elements.anomaliesList.innerHTML = anomalies.map(a => {
        const severityClass = (a.severity || 'SEV-3').toLowerCase().replace('-', '-');
        return `
            <div class="anomaly-item">
                <div class="anomaly-header">
                    <span class="anomaly-metric">${a.metric_name || 'Unknown'}</span>
                    <span class="anomaly-severity ${severityClass}">${a.severity || 'SEV-3'}</span>
                </div>
                <div class="anomaly-details">
                    <span>Value: ${formatMetricValue(a.metric_name, a.value)}</span>
                    <span>Z-Score: ${(a.z_score || 0).toFixed(2)}</span>
                    <span>Deviation: ${(a.deviation_percent || 0).toFixed(0)}%</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateIncidentsList(incidents) {
    if (incidents.length === 0) {
        elements.incidentsList.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
                <span>No incidents created yet</span>
            </div>
        `;
        return;
    }

    elements.incidentsList.innerHTML = incidents.map(inc => `
        <a href="${inc.url || '#'}" target="_blank" class="incident-item" style="text-decoration: none; display: block;">
            <div class="incident-title">${inc.title || 'Incident'}</div>
            <div class="incident-meta">
                <span>${inc.severity || 'SEV-3'}</span>
                <span>${inc.id || '--'}</span>
            </div>
        </a>
    `).join('');
}

function updateHealthGrid(health) {
    const components = health.components || {};

    // Map component keys to display-friendly names and extract status
    const healthItems = Object.entries(components).map(([name, data]) => {
        // Determine status - components have nested structure with stats
        let status = 'ok'; // Default to ok if component exists
        if (data && typeof data === 'object') {
            // Check if there's error info in stats
            const stats = data.stats || {};
            if (stats.error || stats.failed) {
                status = 'error';
            }
        }

        const displayName = name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        return { name: displayName, status };
    });

    elements.healthGrid.innerHTML = healthItems.map(item => {
        const dotClass = item.status === 'ok' ? 'ok' :
            item.status === 'error' ? 'error' :
                item.status === 'warning' ? 'warning' : 'ok';
        return `
            <div class="health-item">
                <span class="health-dot ${dotClass}"></span>
                <span class="health-label">${item.name}</span>
            </div>
        `;
    }).join('');
}

function displayChatResponse(data, clientLatency) {
    const response = data.response || 'No response received';
    const metrics = data.metrics || {};

    // Truncate response for display
    const truncatedResponse = response.length > 500
        ? response.substring(0, 500) + '...'
        : response;

    const metricsHtml = [
        { label: 'Tokens', value: metrics['llm.tokens.total']?.toFixed(0) || '--' },
        { label: 'Latency', value: `${(metrics['llm.latency.ms'] || 0).toFixed(0)}ms` },
        { label: 'Cost', value: `$${(metrics['llm.cost.per_request'] || 0).toFixed(5)}` },
        { label: 'Client RTT', value: `${clientLatency}ms` }
    ].map(m => `<span class="response-metric-tag">${m.label}: ${m.value}</span>`).join('');

    // Anomaly indicator
    const anomalyHtml = data.anomalies_detected && data.anomalies_detected.length > 0
        ? `<div style="margin-top: 12px; padding: 8px; background: var(--error-light); border-radius: 6px; font-size: 12px; color: var(--error);">
             ⚠️ ${data.anomalies_detected.length} anomaly detected
           </div>`
        : '';

    // Incident indicator  
    const incidentHtml = data.incident_created
        ? `<div style="margin-top: 8px; padding: 8px; background: var(--warning-light); border-radius: 6px; font-size: 12px; color: var(--warning);">
             🎫 Incident created: <a href="${data.incident_created.url}" target="_blank">${data.incident_created.id}</a>
           </div>`
        : '';

    elements.chatResponse.innerHTML = `
        <div class="response-content">${escapeHtml(truncatedResponse)}</div>
        <div class="response-metrics">${metricsHtml}</div>
        ${anomalyHtml}
        ${incidentHtml}
    `;
}

// Helper Functions
function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toFixed(0);
}

function formatMetricValue(key, value) {
    if (value === undefined || value === null) return '--';

    if (key.includes('cost')) return `$${value.toFixed(5)}`;
    if (key.includes('latency') || key.includes('ms')) return `${value.toFixed(0)}ms`;
    if (key.includes('throughput')) return `${value.toFixed(0)}/s`;
    if (key.includes('tokens') || key.includes('count') || key.includes('request')) return value.toFixed(0);
    if (Number.isInteger(value)) return value.toString();
    return value.toFixed(2);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Trigger anomaly for demo
async function triggerAnomalyDemo() {
    const btn = elements.triggerAnomaly;
    btn.disabled = true;
    btn.textContent = 'Triggering...';

    try {
        const response = await fetch(`${API_BASE}/trigger-anomaly?anomaly_type=all`, {
            method: 'POST'
        });
        const data = await response.json();

        // Update anomalies and incidents from response
        if (data.anomalies_detected && data.anomalies_detected.length > 0) {
            state.anomalies = [...data.anomalies_detected, ...state.anomalies].slice(0, 10);
            updateAnomaliesList(state.anomalies);
        }

        if (data.incident_created) {
            state.incidents = [data.incident_created, ...state.incidents].slice(0, 5);
            updateIncidentsList(state.incidents);
        }

        // Refresh metrics
        await fetchMetricsSummary();

        btn.textContent = '✓ Triggered!';
        setTimeout(() => {
            btn.textContent = '⚠️ Trigger';
            btn.disabled = false;
        }, 2000);

    } catch (error) {
        console.error('Trigger failed:', error);
        btn.textContent = '✗ Failed';
        setTimeout(() => {
            btn.textContent = '⚠️ Trigger';
            btn.disabled = false;
        }, 2000);
    }
}

// =====================================================
// ACCESSIBILITY FEATURES
// =====================================================

const a11yState = {
    zoomLevel: 0, // 0=100%, 1=125%, 2=150%
    ttsEnabled: false,
    highContrast: false,
    largeText: false,
    speechSynthesis: window.speechSynthesis
};

// DOM Elements for accessibility
const a11yElements = {
    btnMagnify: document.getElementById('btnMagnify'),
    btnTTS: document.getElementById('btnTTS'),
    btnContrast: document.getElementById('btnContrast'),
    btnLargeText: document.getElementById('btnLargeText'),
    startDemoBtn: document.getElementById('startDemoBtn'),
    demoAnomalyType: document.getElementById('demoAnomalyType'),
    demoStatus: document.getElementById('demoStatus'),
    demoEmailNotification: document.getElementById('demoEmailNotification')
};

// Setup accessibility event listeners
function setupAccessibilityListeners() {
    if (a11yElements.btnMagnify) {
        a11yElements.btnMagnify.addEventListener('click', toggleMagnification);
    }
    if (a11yElements.btnTTS) {
        a11yElements.btnTTS.addEventListener('click', toggleTTS);
    }
    if (a11yElements.btnContrast) {
        a11yElements.btnContrast.addEventListener('click', toggleHighContrast);
    }
    if (a11yElements.btnLargeText) {
        a11yElements.btnLargeText.addEventListener('click', toggleLargeText);
    }
    if (a11yElements.startDemoBtn) {
        a11yElements.startDemoBtn.addEventListener('click', startDemoFlow);
    }
}

// Toggle magnification (100% -> 125% -> 150% -> 100%)
function toggleMagnification() {
    const zoomLevels = ['', 'zoom-125', 'zoom-150'];

    // Remove current zoom class
    document.body.classList.remove('zoom-125', 'zoom-150');

    // Cycle to next zoom level
    a11yState.zoomLevel = (a11yState.zoomLevel + 1) % 3;

    if (zoomLevels[a11yState.zoomLevel]) {
        document.body.classList.add(zoomLevels[a11yState.zoomLevel]);
    }

    // Update button state
    a11yElements.btnMagnify.classList.toggle('active', a11yState.zoomLevel !== 0);

    // Announce change
    const zoomPercentages = ['100%', '125%', '150%'];
    announceToUser(`Zoom set to ${zoomPercentages[a11yState.zoomLevel]}`);
}

// Toggle Text-to-Speech
function toggleTTS() {
    a11yState.ttsEnabled = !a11yState.ttsEnabled;
    a11yElements.btnTTS.classList.toggle('active', a11yState.ttsEnabled);

    if (a11yState.ttsEnabled) {
        readDashboardSummary();
    } else {
        if (a11yState.speechSynthesis) {
            a11yState.speechSynthesis.cancel();
        }
        announceToUser('Text-to-speech disabled');
    }
}

// Read dashboard summary aloud
function readDashboardSummary() {
    if (!a11yState.speechSynthesis) {
        console.warn('Speech synthesis not supported');
        return;
    }

    // Cancel any ongoing speech
    a11yState.speechSynthesis.cancel();

    // Collect dashboard data
    const totalTokens = elements.totalTokens?.textContent || '0';
    const avgLatency = elements.avgLatency?.textContent || '--';
    const totalCost = elements.totalCost?.textContent || '--';
    const totalRequests = elements.totalRequests?.textContent || '0';
    const anomalyCount = elements.anomalyCount?.textContent || '0';

    const summaryText = `
        Sentinel Dashboard Summary.
        Total tokens processed: ${totalTokens}.
        Average latency: ${avgLatency}.
        Total cost: ${totalCost}.
        Total requests: ${totalRequests}.
        Active anomalies: ${anomalyCount}.
        ${parseInt(anomalyCount) > 0 ? 'Attention: Anomalies have been detected.' : 'All systems are operating normally.'}
    `;

    const utterance = new SpeechSynthesisUtterance(summaryText);
    utterance.rate = 0.9;
    utterance.pitch = 1;

    a11yState.speechSynthesis.speak(utterance);
}

// Toggle high contrast mode
function toggleHighContrast() {
    a11yState.highContrast = !a11yState.highContrast;
    document.body.classList.toggle('high-contrast', a11yState.highContrast);
    a11yElements.btnContrast.classList.toggle('active', a11yState.highContrast);

    announceToUser(`High contrast mode ${a11yState.highContrast ? 'enabled' : 'disabled'}`);
}

// Toggle large text mode
function toggleLargeText() {
    a11yState.largeText = !a11yState.largeText;
    document.body.classList.toggle('large-text', a11yState.largeText);
    a11yElements.btnLargeText.classList.toggle('active', a11yState.largeText);

    announceToUser(`Large text mode ${a11yState.largeText ? 'enabled' : 'disabled'}`);
}

// Announce message to user (for screen readers)
function announceToUser(message) {
    // Create or update aria-live region
    let announcer = document.getElementById('a11y-announcer');
    if (!announcer) {
        announcer = document.createElement('div');
        announcer.id = 'a11y-announcer';
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.style.cssText = 'position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden;';
        document.body.appendChild(announcer);
    }
    announcer.textContent = message;
}

// =====================================================
// DEMO ZONE - Interactive Workflow Demonstration
// =====================================================

let demoIsRunning = false;

async function startDemoFlow() {
    if (demoIsRunning) return;
    demoIsRunning = true;

    const btn = a11yElements.startDemoBtn;
    const anomalyType = a11yElements.demoAnomalyType?.value || 'all';

    btn.disabled = true;
    btn.textContent = '⏳ Running...';

    // Reset all steps
    resetDemoSteps();

    // Hide email notification
    if (a11yElements.demoEmailNotification) {
        a11yElements.demoEmailNotification.style.display = 'none';
    }

    updateDemoStatus('Starting observability workflow demonstration...');

    try {
        // Step 1: Trigger Anomaly
        await animateStep(1, 'Triggering anomaly metrics...');
        await delay(800);

        // Step 2: AI Detection
        await animateStep(2, 'AI analyzing metrics for anomalies...');

        // Actually trigger the anomaly via API
        const response = await fetch(`${API_BASE}/trigger-anomaly?anomaly_type=${anomalyType}`, {
            method: 'POST'
        });
        const data = await response.json();

        await delay(600);

        // Step 3: Datadog Incident
        await animateStep(3, 'Creating Datadog incident...');

        // Update anomalies list
        if (data.anomalies_detected && data.anomalies_detected.length > 0) {
            state.anomalies = [...data.anomalies_detected, ...state.anomalies].slice(0, 10);
            updateAnomaliesList(state.anomalies);
        }

        // Update incidents list
        if (data.incident_created) {
            state.incidents = [data.incident_created, ...state.incidents].slice(0, 5);
            updateIncidentsList(state.incidents);
        }

        await delay(800);

        // Step 4: Email Alert
        await animateStep(4, 'Sending email notification to AI engineer...');
        await delay(600);

        // Show simulated email notification
        showEmailNotification(data);

        updateDemoStatus('✅ Demo complete! The full observability pipeline has been demonstrated.');

        // Read success message if TTS is enabled
        if (a11yState.ttsEnabled) {
            const utterance = new SpeechSynthesisUtterance('Demo complete. Anomaly detected, incident created, and email notification sent.');
            a11yState.speechSynthesis.speak(utterance);
        }

    } catch (error) {
        console.error('Demo failed:', error);
        updateDemoStatus('❌ Demo failed. Please check the console for errors.');
    } finally {
        btn.disabled = false;
        btn.textContent = '▶️ Run Demo';
        demoIsRunning = false;
    }
}

function resetDemoSteps() {
    for (let i = 1; i <= 4; i++) {
        const step = document.getElementById(`demoStep${i}`);
        if (step) {
            step.classList.remove('active', 'completed');
        }
    }

    // Reset connectors
    document.querySelectorAll('.demo-connector').forEach(conn => {
        conn.classList.remove('active');
    });
}

async function animateStep(stepNum, statusMessage) {
    // Update status
    updateDemoStatus(statusMessage);

    // Get step element
    const step = document.getElementById(`demoStep${stepNum}`);
    if (!step) return;

    // Remove previous active states
    for (let i = 1; i <= 4; i++) {
        const s = document.getElementById(`demoStep${i}`);
        if (s && i < stepNum) {
            s.classList.remove('active');
            s.classList.add('completed');
        }
    }

    // Activate connector before this step
    if (stepNum > 1) {
        const connectors = document.querySelectorAll('.demo-connector');
        if (connectors[stepNum - 2]) {
            connectors[stepNum - 2].classList.add('active');
        }
    }

    // Activate current step
    step.classList.add('active');
}

function showEmailNotification(data) {
    const emailDiv = a11yElements.demoEmailNotification;
    if (!emailDiv) return;

    // Update email content based on actual data
    const anomalies = data.anomalies_detected || [];
    const incident = data.incident_created || {};

    let summaryText = 'Critical anomaly detected in LLM observability pipeline.';
    let rootCauseText = 'AI analysis indicates unusual patterns in LLM response metrics.';

    if (anomalies.length > 0) {
        const anomaly = anomalies[0];
        summaryText = `${anomaly.metric_name || 'Metric'} exceeded threshold. ` +
            `Z-score: ${(anomaly.z_score || 0).toFixed(2)} (threshold: 3.0). ` +
            `Deviation: ${(anomaly.deviation_percent || 0).toFixed(0)}%`;
    }

    if (incident.id) {
        rootCauseText = `Incident ${incident.id} created in Datadog. ` +
            `AI root cause analysis suggests investigating recent prompt patterns and API response times.`;
    }

    const emailSummary = document.getElementById('emailIncidentSummary');
    const emailRootCause = document.getElementById('emailRootCause');

    if (emailSummary) emailSummary.textContent = summaryText;
    if (emailRootCause) emailRootCause.textContent = rootCauseText;

    // Show email notification with animation
    emailDiv.style.display = 'block';
}

function updateDemoStatus(message) {
    if (a11yElements.demoStatus) {
        a11yElements.demoStatus.textContent = message;
    }
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Initialize accessibility features on load
document.addEventListener('DOMContentLoaded', () => {
    setupAccessibilityListeners();
});

