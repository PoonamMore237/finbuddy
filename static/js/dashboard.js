// static/js/dashboard.js
// Advanced Interactive Financial Intelligence Dashboard

let trendChartInstance = null;
let categoryChartInstance = null;
let cachedAuditData = null;
let currentFilter = '';
let currentSearch = '';

// ─────────────────────────────────────────
// Toast Notification Utility
// ─────────────────────────────────────────

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

async function fetchJSON(url) {
  try {
    const res = await fetch(url);
    if (res.status === 401) {
      window.location.href = '/login';
      return null;
    }
    return await res.json();
  } catch (err) {
    console.error(`Fetch failed for ${url}:`, err);
    return null;
  }
}

// ─────────────────────────────────────────
// Stat Cards & Summaries
// ─────────────────────────────────────────

async function loadStats() {
  const summary = await fetchJSON('/api/summary');
  if (!summary || summary.length === 0) return;

  const today = new Date();
  const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
  const current = summary.find(s => s.month === currentMonth) || summary[summary.length - 1] || { income: 0, expense: 0 };

  const income = current.income || 0;
  const expense = current.expense || 0;
  const net = income - expense;
  const savingsRate = income > 0 ? ((net / income) * 100).toFixed(1) : '0';

  document.getElementById('statIncome').textContent = `₹${income.toLocaleString('en-IN')}`;
  document.getElementById('statExpense').textContent = `₹${expense.toLocaleString('en-IN')}`;

  const netEl = document.getElementById('statNet');
  netEl.textContent = `₹${Math.abs(net).toLocaleString('en-IN')}`;
  netEl.style.color = net >= 0 ? 'var(--income)' : 'var(--danger)';
  if (net < 0) netEl.textContent = '-' + netEl.textContent;

  const rateEl = document.getElementById('statSavingsRate');
  rateEl.textContent = `${savingsRate}%`;
  rateEl.style.color = savingsRate >= 20 ? 'var(--income)' : (savingsRate >= 0 ? 'var(--warning)' : 'var(--danger)');
}

// ─────────────────────────────────────────
// AI Financial Health Score & Audit
// ─────────────────────────────────────────

async function loadHealthScore() {
  const audit = await fetchJSON('/api/financial-health');
  if (!audit) return;
  cachedAuditData = audit;

  const score = audit.score || 50;
  const rating = audit.rating || 'Fair';

  // Gauge animation
  const gaugePath = document.getElementById('scoreGaugePath');
  const scoreText = document.getElementById('scoreText');
  const ratingBadge = document.getElementById('ratingBadge');
  const summaryText = document.getElementById('healthSummaryText');

  gaugePath.setAttribute('stroke-dasharray', `${score}, 100`);
  scoreText.textContent = score;
  ratingBadge.textContent = `${score}/100 · ${rating}`;

  if (score >= 80) {
    gaugePath.setAttribute('stroke', 'var(--income)');
    ratingBadge.style.background = 'rgba(16, 185, 129, 0.2)';
    ratingBadge.style.color = 'var(--income)';
  } else if (score >= 60) {
    gaugePath.setAttribute('stroke', '#38bdf8');
    ratingBadge.style.background = 'rgba(56, 189, 248, 0.2)';
    ratingBadge.style.color = '#38bdf8';
  } else {
    gaugePath.setAttribute('stroke', 'var(--warning)');
    ratingBadge.style.background = 'rgba(245, 158, 11, 0.2)';
    ratingBadge.style.color = 'var(--warning)';
  }

  if (audit.report && audit.report.summary) {
    summaryText.textContent = audit.report.summary;
  }
}

function openAuditModal() {
  if (!cachedAuditData) {
    showToast('Calculating AI audit report...', 'info');
    loadHealthScore().then(() => renderAuditModal());
  } else {
    renderAuditModal();
  }
  document.getElementById('auditModal').classList.add('active');
}

function renderAuditModal() {
  const content = document.getElementById('auditModalContent');
  if (!cachedAuditData || !cachedAuditData.report) {
    content.innerHTML = '<p style="text-align:center;padding:20px;">Could not load audit data.</p>';
    return;
  }

  const { score, rating, metrics, report } = cachedAuditData;

  let actionsHtml = '';
  if (report.action_plan && report.action_plan.length > 0) {
    actionsHtml = report.action_plan.map(a => `
      <div class="action-item">
        <div>
          <strong>${a.action}</strong>
          <span style="display:block;font-size:11px;color:var(--text-dim);margin-top:2px;">Priority: ${a.priority}</span>
        </div>
        <div class="action-item-savings">+₹${(a.estimated_monthly_savings || 0).toLocaleString('en-IN')}/mo</div>
      </div>
    `).join('');
  }

  content.innerHTML = `
    <div class="audit-metric-row">
      <div class="audit-metric-box">
        <span>Score</span>
        <strong style="color:var(--accent);">${score}/100</strong>
      </div>
      <div class="audit-metric-box">
        <span>Rating</span>
        <strong>${rating}</strong>
      </div>
      <div class="audit-metric-box">
        <span>Savings Rate</span>
        <strong style="color:#38bdf8;">${metrics.savings_rate}%</strong>
      </div>
    </div>

    <p style="font-size:13.5px;color:var(--text);margin-bottom:14px;">${report.summary}</p>

    <div class="audit-section-title">✅ Key Strengths</div>
    <ul class="audit-list">
      ${(report.strengths || []).map(s => `<li>${s}</li>`).join('')}
    </ul>

    <div class="audit-section-title" style="color:var(--warning);">⚠ Risk Alerts & Spending Leaks</div>
    <ul class="audit-list risks">
      ${(report.risk_alerts || []).map(r => `<li>${r}</li>`).join('')}
    </ul>

    <div class="audit-section-title" style="color:#38bdf8;">🎯 AI Action Plan & Projected Savings</div>
    ${actionsHtml}
  `;
}

// ─────────────────────────────────────────
// Category Budgets
// ─────────────────────────────────────────

async function loadBudgets() {
  const budgets = await fetchJSON('/api/budgets');
  const grid = document.getElementById('budgetGrid');

  if (!budgets || budgets.length === 0) {
    grid.innerHTML = '<p style="color:var(--text-muted);font-size:13px;grid-column:1/-1;">No budget limits configured yet. Click "+ Set / Edit Budget" above!</p>';
    return;
  }

  grid.innerHTML = budgets.map(b => {
    const pct = Math.min(b.percentage, 100);
    return `
      <div class="budget-card">
        <div class="budget-card-header">
          <span class="budget-cat-name">${b.category}</span>
          <span class="budget-status-pill ${b.status}">${b.status.toUpperCase()}</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill ${b.status}" style="width: ${pct}%;"></div>
        </div>
        <div class="budget-card-footer">
          <span>₹${Math.round(b.spent).toLocaleString('en-IN')} spent</span>
          <span>${b.monthly_limit > 0 ? `₹${Math.round(b.monthly_limit).toLocaleString('en-IN')} limit (${b.percentage}%)` : 'No limit'}</span>
        </div>
      </div>
    `;
  }).join('');
}

// ─────────────────────────────────────────
// Charts (Income vs Expense Trend & Categories)
// ─────────────────────────────────────────

async function loadTrendChart() {
  const data = await fetchJSON('/api/summary');
  if (!data) return;

  const labels = data.map(d => {
    const [year, month] = d.month.split('-');
    return new Date(year, month - 1).toLocaleString('default', { month: 'short', year: '2-digit' });
  });

  const ctx = document.getElementById('trendChart').getContext('2d');
  if (trendChartInstance) trendChartInstance.destroy();

  trendChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Income',
          data: data.map(d => d.income || 0),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.12)',
          tension: 0.35,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: '#10b981',
        },
        {
          label: 'Expenses',
          data: data.map(d => d.expense || 0),
          borderColor: '#f97316',
          backgroundColor: 'rgba(249, 115, 22, 0.12)',
          tension: 0.35,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: '#f97316',
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: '#e2e8f0', font: { family: 'Plus Jakarta Sans', size: 12 } } },
      },
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#94a3b8', callback: v => `₹${v.toLocaleString('en-IN')}` }, grid: { color: 'rgba(255,255,255,0.05)' } },
      },
    },
  });
}

async function loadCategoryChart() {
  const data = await fetchJSON('/api/categories');
  const canvas = document.getElementById('categoryChart');
  if (!data || data.length === 0) {
    canvas.parentElement.innerHTML = '<h3 class="chart-title">Monthly Spending by Category</h3><p style="color:var(--text-muted);font-size:13px;text-align:center;margin-top:30px;">No expenses logged this month yet.</p>';
    return;
  }

  const palette = ['#10b981', '#f97316', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6', '#f59e0b', '#06b6d4'];

  const ctx = canvas.getContext('2d');
  if (categoryChartInstance) categoryChartInstance.destroy();

  categoryChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.category.charAt(0).toUpperCase() + d.category.slice(1)),
      datasets: [{
        data: data.map(d => d.total),
        backgroundColor: palette.slice(0, data.length),
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#e2e8f0', font: { family: 'Plus Jakarta Sans', size: 11.5 }, padding: 12 },
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ₹${ctx.parsed.toLocaleString('en-IN')}`,
          },
        },
      },
    },
  });
}

// ─────────────────────────────────────────
// Wealth & SIP Compound Simulator
// ─────────────────────────────────────────

function updateSimulator() {
  const p = parseFloat(document.getElementById('sliderMonthly').value);
  const rAnnual = parseFloat(document.getElementById('sliderReturn').value);
  const years = parseInt(document.getElementById('sliderYears').value);

  document.getElementById('valMonthly').textContent = `₹${p.toLocaleString('en-IN')}`;
  document.getElementById('valReturn').textContent = `${rAnnual}%`;
  document.getElementById('valYears').textContent = `${years} Year${years > 1 ? 's' : ''}`;

  const r = (rAnnual / 100) / 12;
  const n = years * 12;

  let futureValue = 0;
  if (r > 0) {
    futureValue = p * (((1 + r) ** n - 1) / r) * (1 + r);
  } else {
    futureValue = p * n;
  }

  const totalInvested = p * n;
  const wealthGain = futureValue - totalInvested;
  const inflationRate = 0.06;
  const realValue = futureValue / ((1 + inflationRate) ** years);

  document.getElementById('resInvested').textContent = `₹${Math.round(totalInvested).toLocaleString('en-IN')}`;
  document.getElementById('resWealthGain').textContent = `₹${Math.round(wealthGain).toLocaleString('en-IN')}`;
  document.getElementById('resFutureValue').textContent = `₹${Math.round(futureValue).toLocaleString('en-IN')}`;
  document.getElementById('resRealValue').textContent = `₹${Math.round(realValue).toLocaleString('en-IN')}`;

  const insightEl = document.getElementById('simInsightText');
  const multiple = (futureValue / totalInvested).toFixed(1);
  insightEl.innerHTML = `💡 <strong>Compound Growth Insight:</strong> In ${years} years, your portfolio will multiply your invested capital by <strong>${multiple}x</strong>. Your wealth gain of ₹${Math.round(wealthGain).toLocaleString('en-IN')} generates passive returns on autopilot!`;
}

document.getElementById('sliderMonthly').addEventListener('input', updateSimulator);
document.getElementById('sliderReturn').addEventListener('input', updateSimulator);
document.getElementById('sliderYears').addEventListener('input', updateSimulator);

// ─────────────────────────────────────────
// Transactions Table & Delete Action
// ─────────────────────────────────────────

async function loadTransactions() {
  let url = `/api/transactions?limit=50`;
  if (currentSearch) url += `&search=${encodeURIComponent(currentSearch)}`;
  if (currentFilter) url += `&txn_type=${encodeURIComponent(currentFilter)}`;

  const data = await fetchJSON(url);
  const tbody = document.getElementById('txnTableBody');

  if (!data || data.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-muted);">No matching transactions found.</td></tr>';
    return;
  }

  tbody.innerHTML = data.map(t => `
    <tr>
      <td>${t.date}</td>
      <td style="font-weight:600;text-transform:capitalize;">${t.category}</td>
      <td style="color:var(--text-muted);">${t.description || '—'}</td>
      <td><span class="badge badge-${t.type}">${t.type}</span></td>
      <td style="font-family:var(--font-mono);font-weight:700;">₹${parseFloat(t.amount).toLocaleString('en-IN')}</td>
      <td style="text-align:right;">
        <button type="button" class="btn-del-row" data-id="${t.id}" title="Delete transaction">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
        </button>
      </td>
    </tr>
  `).join('');

  // Attach delete handlers
  tbody.querySelectorAll('.btn-del-row').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      if (!confirm('Are you sure you want to delete this transaction?')) return;

      try {
        const res = await fetch(`/api/transactions/${id}`, { method: 'DELETE' });
        if (res.ok) {
          showToast('Transaction deleted.', 'success');
          loadTransactions();
          loadStats();
          loadBudgets();
          loadTrendChart();
          loadCategoryChart();
        } else {
          showToast('Failed to delete transaction.', 'error');
        }
      } catch (e) {
        showToast('Error deleting transaction.', 'error');
      }
    });
  });
}

// Search and filter handling
document.getElementById('txnSearchInput').addEventListener('input', (e) => {
  currentSearch = e.target.value.trim();
  loadTransactions();
});

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.getAttribute('data-filter');
    loadTransactions();
  });
});

// ─────────────────────────────────────────
// Modals Management
// ─────────────────────────────────────────

// Open buttons
document.getElementById('btnOpenAddTxn').addEventListener('click', () => {
  document.getElementById('txnDate').value = new Date().toISOString().slice(0, 10);
  document.getElementById('addTxnModal').classList.add('active');
});

document.getElementById('btnOpenSetBudget').addEventListener('click', () => {
  document.getElementById('setBudgetModal').classList.add('active');
});

document.getElementById('btnOpenAudit').addEventListener('click', openAuditModal);
document.getElementById('btnViewAuditDetails').addEventListener('click', openAuditModal);

// Close buttons
document.querySelectorAll('.btn-close-modal').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.getAttribute('data-close');
    document.getElementById(target).classList.remove('active');
  });
});

// Close when clicking on backdrop
document.querySelectorAll('.modal-backdrop').forEach(modal => {
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('active');
  });
});

// Manual Transaction Form Submit
document.getElementById('manualTxnForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const amount = parseFloat(document.getElementById('txnAmount').value);
  const type = document.getElementById('txnType').value;
  const category = document.getElementById('txnCategory').value.trim();
  const dateVal = document.getElementById('txnDate').value;
  const description = document.getElementById('txnDescription').value.trim();

  try {
    const res = await fetch('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount, type, category, date: dateVal, description }),
    });

    if (res.ok) {
      showToast('Transaction recorded successfully!', 'success');
      document.getElementById('addTxnModal').classList.remove('active');
      document.getElementById('manualTxnForm').reset();
      loadTransactions();
      loadStats();
      loadBudgets();
      loadTrendChart();
      loadCategoryChart();
    } else {
      showToast('Could not save transaction.', 'error');
    }
  } catch (err) {
    showToast('Failed to save transaction.', 'error');
  }
});

// Set Budget Form Submit
document.getElementById('setBudgetForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const category = document.getElementById('budgetCategory').value.trim();
  const monthly_limit = parseFloat(document.getElementById('budgetLimit').value);

  try {
    const res = await fetch('/api/budgets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category, monthly_limit }),
    });

    if (res.ok) {
      showToast(`Budget for ${category} updated!`, 'success');
      document.getElementById('setBudgetModal').classList.remove('active');
      document.getElementById('setBudgetForm').reset();
      loadBudgets();
      loadHealthScore();
    } else {
      showToast('Could not save budget limit.', 'error');
    }
  } catch (err) {
    showToast('Failed to save budget.', 'error');
  }
});

// ─────────────────────────────────────────
// Boot Dashboard
// ─────────────────────────────────────────

loadStats();
loadHealthScore();
loadBudgets();
loadTrendChart();
loadCategoryChart();
updateSimulator();
loadTransactions();
