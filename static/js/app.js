/**
 * TradeGuard Web Dashboard JavaScript Engine.
 * Handles API calls, dynamic Chart.js rendering, live filtering, and workflow action triggers.
 */

let allBreaksData = [];
let allTradesData = [];
let chartMatchTrend = null;
let chartSeverityDist = null;
let chartBreakTypes = null;
let chartDeskExposure = null;

// Initialize Dashboard on DOM Content Loaded
document.addEventListener("DOMContentLoaded", () => {
    fetchDashboardData();
});

// Toast notification helper
function showToast(message, icon = "⚡") {
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toast-message");
    const toastIcon = document.getElementById("toast-icon");
    
    toastIcon.textContent = icon;
    toastMsg.textContent = message;
    toast.classList.remove("hidden");
    
    setTimeout(() => {
        toast.classList.add("hidden");
    }, 4000);
}

// Navigation Tab Switcher
function switchTab(viewId, btnElement) {
    document.querySelectorAll(".tab-view").forEach(el => el.classList.add("hidden"));
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
    
    document.getElementById(`view-${viewId}`).classList.remove("hidden");
    btnElement.classList.add("active");
}

// Fetch all dashboard data from Flask REST API
async function fetchDashboardData() {
    try {
        const [statusRes, summaryRes, breaksRes, tradesRes, riskRes, reportsRes] = await Promise.all([
            fetch("/api/status").then(r => r.json()),
            fetch("/api/summary").then(r => r.json()),
            fetch("/api/breaks").then(r => r.json()),
            fetch("/api/trades").then(r => r.json()),
            fetch("/api/risk-summary").then(r => r.json()),
            fetch("/api/reports/list").then(r => r.json()),
        ]);

        updateHeaderStatus(statusRes);
        updateKpiCards(summaryRes.latest, statusRes);
        renderCharts(summaryRes.history, riskRes.severities, riskRes.break_types, riskRes.desks);
        
        allBreaksData = breaksRes.breaks || [];
        populateBreaksTable(allBreaksData);

        allTradesData = tradesRes.trades || [];
        populateTradesTable(allTradesData);

        populateRiskTable(riskRes.desks || []);
        populateReportsCards(reportsRes.reports || []);

    } catch (err) {
        console.error("Failed fetching dashboard data:", err);
        showToast("Error loading data from server: " + err.message, "⚠️");
    }
}

// Update Header Status Banner
function updateHeaderStatus(status) {
    if (status.latest_run) {
        document.getElementById("header-run-id").textContent = status.latest_run.Run_ID || "REC_STAGE";
    }
}

// Update KPI Executive Summary Cards
function updateKpiCards(latest, status) {
    if (!latest || Object.keys(latest).length === 0) return;

    const matchPct = parseFloat(latest.Match_Percentage || 0).toFixed(2);
    document.getElementById("kpi-match-pct").textContent = `${matchPct}%`;
    document.getElementById("kpi-match-bar").style.width = `${matchPct}%`;

    const matchBadge = document.getElementById("kpi-match-status");
    if (matchPct >= 95) {
        matchBadge.textContent = "OPTIMAL";
        matchBadge.className = "kpi-badge match-badge";
    } else if (matchPct >= 90) {
        matchBadge.textContent = "ACCEPTABLE";
        matchBadge.className = "kpi-badge match-badge";
    } else {
        matchBadge.textContent = "ATTENTION";
        matchBadge.className = "kpi-badge critical-badge";
    }

    document.getElementById("kpi-fo-count").textContent = (latest.Front_Count || status.front_office_count || 0).toLocaleString();
    document.getElementById("kpi-bo-count").textContent = (latest.Back_Count || status.back_office_count || 0).toLocaleString();
    
    const totalBreaks = (latest.Critical_Breaks || 0) + (latest.High_Breaks || 0) + (latest.Medium_Breaks || 0) + (latest.Low_Breaks || 0);
    document.getElementById("kpi-breaks-count").textContent = totalBreaks.toLocaleString();
    document.getElementById("kpi-matched-count").textContent = `${(latest.Matched_Count || 0).toLocaleString()} Trades Matched`;

    document.getElementById("kpi-critical-count").textContent = (latest.Critical_Breaks || 0).toLocaleString();
    document.getElementById("kpi-exec-time").textContent = `${parseFloat(latest.Execution_Time || 0).toFixed(4)}s`;
}

// Render Chart.js Visualizations
function renderCharts(history, severities, breakTypes, desks) {
    // 1. Match Rate Trend Line Chart
    if (chartMatchTrend) chartMatchTrend.destroy();
    const ctxTrend = document.getElementById("chart-match-trend").getContext("2d");
    
    const dates = (history || []).map(h => (h.Created_At || "").substring(0, 10));
    const matchPcts = (history || []).map(h => h.Match_Percentage);

    chartMatchTrend = new Chart(ctxTrend, {
        type: "line",
        data: {
            labels: dates.length > 0 ? dates : ["Run 1"],
            datasets: [{
                label: "Match Rate (%)",
                data: matchPcts.length > 0 ? matchPcts : [92.7],
                borderColor: "#00f2fe",
                backgroundColor: "rgba(0, 242, 254, 0.1)",
                borderWidth: 3,
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } },
                y: { min: 80, max: 100, grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } }
            }
        }
    });

    // 2. Break Severity Doughnut Chart
    if (chartSeverityDist) chartSeverityDist.destroy();
    const ctxSev = document.getElementById("chart-severity-dist").getContext("2d");
    
    const sevLabels = (severities || []).map(s => s.Severity);
    const sevCounts = (severities || []).map(s => s.Break_Count);

    chartSeverityDist = new Chart(ctxSev, {
        type: "doughnut",
        data: {
            labels: sevLabels.length > 0 ? sevLabels : ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            datasets: [{
                data: sevCounts.length > 0 ? sevCounts : [30, 14, 24, 21],
                backgroundColor: ["#ff477e", "#ff9f1c", "#ffd166", "#00f5d4"],
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: "right", labels: { color: "#f8fafc" } } }
        }
    });

    // 3. Break Types Bar Chart
    if (chartBreakTypes) chartBreakTypes.destroy();
    const ctxType = document.getElementById("chart-break-types").getContext("2d");

    const typeLabels = (breakTypes || []).map(b => b.Break_Type);
    const typeCounts = (breakTypes || []).map(b => b.Break_Count);

    chartBreakTypes = new Chart(ctxType, {
        type: "bar",
        data: {
            labels: typeLabels.length > 0 ? typeLabels : ["Missing", "Unexpected", "Price", "Quantity"],
            datasets: [{
                label: "Exception Count",
                data: typeCounts.length > 0 ? typeCounts : [18, 12, 16, 10],
                backgroundColor: "#3b82f6",
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: "#94a3b8" } },
                y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } }
            }
        }
    });

    // 4. Desk Exposure Bar Chart
    if (chartDeskExposure) chartDeskExposure.destroy();
    const ctxDesk = document.getElementById("chart-desk-exposure").getContext("2d");

    const deskLabels = (desks || []).map(d => d.Desk);
    const deskBreaks = (desks || []).map(d => d.Total_Breaks);

    chartDeskExposure = new Chart(ctxDesk, {
        type: "bar",
        data: {
            labels: deskLabels.length > 0 ? deskLabels : ["Rates", "FX", "Equities", "Credit", "Commodities"],
            datasets: [{
                label: "Breaks Count",
                data: deskBreaks.length > 0 ? deskBreaks : [20, 18, 15, 22, 14],
                backgroundColor: "#8b5cf6",
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: "#94a3b8" } },
                y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } }
            }
        }
    });
}

// Populate Break Explorer Table
function populateBreaksTable(breaks) {
    const tbody = document.getElementById("tbody-breaks");
    tbody.innerHTML = "";

    if (!breaks || breaks.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:#64748b; padding:2rem;">No reconciliation breaks found.</td></tr>`;
        return;
    }

    breaks.forEach(b => {
        const resStatus = b.Resolution_Status || 'UNRESOLVED';
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="mono font-semibold" style="color:#00f2fe;">${b.Trade_ID}</td>
            <td><span class="sev-pill sev-${b.Severity}">${b.Severity}</span></td>
            <td class="font-medium">${b.Break_Type}</td>
            <td class="mono">${b.Expected_Value || '-'}</td>
            <td class="mono">${b.Actual_Value || '-'}</td>
            <td>${b.Desk}</td>
            <td>${b.Counterparty}</td>
            <td>${b.Asset_Class}</td>
            <td><span class="res-pill res-${resStatus}">${resStatus.replace('_', ' ')}</span></td>
            <td>
                <button class="btn-action-resolve" onclick="openResolveModal(${b.ID})">
                    ${resStatus === 'UNRESOLVED' ? '⚡ Resolve' : '✏️ Edit'}
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Filter Break Explorer Table
function filterBreaksTable() {
    const searchVal = document.getElementById("search-breaks").value.toLowerCase();
    const sevVal = document.getElementById("filter-severity").value;
    const typeVal = document.getElementById("filter-break-type").value;
    const resVal = document.getElementById("filter-resolution") ? document.getElementById("filter-resolution").value : "ALL";

    const filtered = allBreaksData.filter(b => {
        const matchesSearch = (b.Trade_ID || '').toLowerCase().includes(searchVal) ||
                              (b.Trader || '').toLowerCase().includes(searchVal) ||
                              (b.Counterparty || '').toLowerCase().includes(searchVal) ||
                              (b.Symbol || '').toLowerCase().includes(searchVal);
        
        const matchesSev = (sevVal === "ALL") || (b.Severity === sevVal);
        const matchesType = (typeVal === "ALL") || (b.Break_Type === typeVal);
        const matchesRes = (resVal === "ALL") || ((b.Resolution_Status || 'UNRESOLVED') === resVal);

        return matchesSearch && matchesSev && matchesType && matchesRes;
    });

    populateBreaksTable(filtered);
}

// Resolution Modal Event Handlers
function openResolveModal(breakId) {
    const breakItem = allBreaksData.find(b => b.ID === breakId);
    if (!breakItem) return;

    document.getElementById("modal-break-id").value = breakItem.ID;
    document.getElementById("modal-trade-id").textContent = breakItem.Trade_ID;
    document.getElementById("modal-break-type").textContent = breakItem.Break_Type;
    document.getElementById("modal-exp-act").textContent = `${breakItem.Expected_Value || '-'} / ${breakItem.Actual_Value || '-'}`;
    document.getElementById("modal-desk-cp").textContent = `${breakItem.Desk} / ${breakItem.Counterparty}`;
    
    document.getElementById("modal-status").value = breakItem.Resolution_Status || "RESOLVED";
    document.getElementById("modal-notes").value = breakItem.Resolution_Reason || "";

    const modal = document.getElementById("modal-resolve");
    modal.classList.remove("hidden");
}

function closeResolveModal() {
    const modal = document.getElementById("modal-resolve");
    modal.classList.add("hidden");
}

function onReasonSelectChange(selectElem) {
    if (selectElem.value !== "Custom Note") {
        document.getElementById("modal-notes").value = selectElem.value;
    }
}

async function handleResolveSubmit(event) {
    event.preventDefault();
    const breakId = parseInt(document.getElementById("modal-break-id").value);
    const status = document.getElementById("modal-status").value;
    const reason = document.getElementById("modal-notes").value || document.getElementById("modal-reason-select").value;
    const user = document.getElementById("modal-user").value || "Product Controller";

    try {
        const res = await fetch("/api/breaks/resolve", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ break_id: breakId, status, reason, user })
        }).then(r => r.json());

        if (res.status === "success") {
            showToast(res.message, "✅");
            closeResolveModal();
            fetchDashboardData();
        } else {
            showToast("Failed to update break: " + res.message, "❌");
        }
    } catch (err) {
        showToast("Error updating break status: " + err.message, "❌");
    }
}

// Populate Trade Population Table
function populateTradesTable(trades) {
    const tbody = document.getElementById("tbody-trades");
    tbody.innerHTML = "";

    if (!trades || trades.length === 0) {
        tbody.innerHTML = `<tr><td colspan="14" style="text-align:center; color:#64748b; padding:2rem;">No trades found in staging database.</td></tr>`;
        return;
    }

    trades.forEach(t => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="mono font-semibold">${t.Trade_ID}</td>
            <td class="mono">${t.Trade_Date}</td>
            <td class="mono">${t.Settlement_Date}</td>
            <td>${t.Trader}</td>
            <td>${t.Desk}</td>
            <td>${t.Portfolio}</td>
            <td>${t.Counterparty}</td>
            <td>${t.Asset_Class}</td>
            <td class="mono font-bold" style="color:${t.Buy_Sell === 'BUY' ? '#00f5d4' : '#ff477e'}">${t.Buy_Sell}</td>
            <td class="mono">${(t.Quantity || 0).toLocaleString()}</td>
            <td class="mono">$${(t.Price || 0).toFixed(2)}</td>
            <td class="mono">${t.Currency}</td>
            <td class="mono font-bold">$${(t.Trade_Notional || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
            <td><span class="kpi-badge match-badge">${t.Trade_Status}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// Filter Trade Population Table
function filterTradesTable() {
    const searchVal = document.getElementById("search-trades").value.toLowerCase();
    const filtered = allTradesData.filter(t => {
        return (t.Trade_ID || '').toLowerCase().includes(searchVal) ||
               (t.Trader || '').toLowerCase().includes(searchVal) ||
               (t.Counterparty || '').toLowerCase().includes(searchVal) ||
               (t.Symbol || '').toLowerCase().includes(searchVal);
    });
    populateTradesTable(filtered);
}

// Populate Desk Risk Summary Table
function populateRiskTable(desks) {
    const tbody = document.getElementById("tbody-desk-risk");
    tbody.innerHTML = "";

    desks.forEach(d => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="font-bold">${d.Desk}</td>
            <td class="mono">${(d.Total_Trades || 0).toLocaleString()}</td>
            <td class="mono font-bold">$${(d.Total_Notional || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
            <td class="mono text-warning font-bold">${d.Total_Breaks}</td>
            <td class="mono text-danger font-bold">${d.Critical_Breaks}</td>
            <td class="mono font-bold" style="color:${d.Exception_Rate > 5 ? '#ff477e' : '#00f5d4'}">${d.Exception_Rate}%</td>
        `;
        tbody.appendChild(tr);
    });
}

// Populate Reports Cards
function populateReportsCards(reports) {
    const container = document.getElementById("reports-cards-container");
    container.innerHTML = "";

    if (!reports || reports.length === 0) {
        container.innerHTML = `<p style="color:#64748b;">No generated reports found. Run 'Reconcile' or 'Power BI Export' to generate reports.</p>`;
        return;
    }

    reports.forEach(r => {
        const iconMap = { excel: "📊", csv: "📄", json: "📦", powerbi: "📈", pdf: "📕" };
        const card = document.createElement("div");
        card.className = "report-card";
        card.innerHTML = `
            <div>
                <div class="report-icon">${iconMap[r.category] || '📁'}</div>
                <div class="report-name">${r.filename}</div>
                <div class="report-meta">${r.category.toUpperCase()} • ${(r.size_bytes / 1024).toFixed(1)} KB</div>
            </div>
            <a href="/api/download/${r.category}/${r.filename}" class="btn btn-secondary mt-3" style="width:100%; justify-content:center;">
                📥 Download
            </a>
        `;
        container.appendChild(card);
    });
}

// Action Handlers
async function triggerGeneratePDF() {
    showToast("Generating 1-Page Executive PDF Brief...", "📄");
    try {
        const res = await fetch("/api/reports/pdf", { method: "POST" }).then(r => r.json());
        showToast(res.message, "✅");
        fetchDashboardData();
    } catch (err) {
        showToast("PDF generation failed: " + err.message, "❌");
    }
}
async function triggerGenerateData() {
    const countInput = document.getElementById("cfg-count");
    const breakRateInput = document.getElementById("cfg-break-rate");
    const count = countInput ? parseInt(countInput.value) || 1000 : 1000;
    const breakRate = breakRateInput ? parseFloat(breakRateInput.value) / 100.0 : 0.04;

    showToast(`Generating ${count.toLocaleString()} trade feeds (Break Rate: ${(breakRate*100).toFixed(1)}%)...`, "⚡");
    try {
        const res = await fetch("/api/generate-data", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ count: count, seed: 42, break_rate: breakRate })
        }).then(r => r.json());
        
        showToast(res.message, "✅");
        fetchDashboardData();
    } catch (err) {
        showToast("Failed data generation: " + err.message, "❌");
    }
}

async function triggerReconciliation() {
    const thresholdInput = document.getElementById("cfg-threshold");
    const threshold = thresholdInput ? parseFloat(thresholdInput.value) || 0.01 : 0.01;

    showToast(`Executing SQL trade reconciliation engine (Tolerance: $${threshold.toFixed(2)})...`, "🔄");
    try {
        const res = await fetch("/api/reconcile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ threshold: threshold })
        }).then(r => r.json());
        
        showToast(res.message, "✅");
        fetchDashboardData();
    } catch (err) {
        showToast("Reconciliation failed: " + err.message, "❌");
    }
}

async function triggerSimulateHistory() {
    showToast("Simulating 30 historical reconciliation runs over past 30 days...", "📈");
    try {
        const res = await fetch("/api/simulate-history", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ runs: 30, seed: 42 })
        }).then(r => r.json());

        showToast(res.message, "✅");
        fetchDashboardData();
    } catch (err) {
        showToast("Historical simulation failed: " + err.message, "❌");
    }
}

async function triggerExportPowerBI() {
    showToast("Generating Power BI analytics CSV datasets...", "📊");
    try {
        const res = await fetch("/api/export-powerbi", { method: "POST" }).then(r => r.json());
        showToast(res.message, "✅");
        fetchDashboardData();
    } catch (err) {
        showToast("Power BI export failed: " + err.message, "❌");
    }
}
