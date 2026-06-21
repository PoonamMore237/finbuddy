// static/js/dashboard.js
// Fetches data from the API and renders charts using Chart.js.

const CHART_DEFAULTS = {
  color: '#e2e8f0',
  gridColor: '#2e3347',
  accent: '#22c55e',
  expense: '#f97316',
};

// ─────────────────────────────────────────
// Fetch helpers
// ─────────────────────────────────────────

async function fetchJSON(url) {
  const res = await fetch(url);
  if (res.status === 401) { window.location.href = '/login'; return null; }
  return res.json();
}

// ─────────────────────────────────────────
// Stat cards
// ─────────────────────────────────────────

async function loadStats() {
  const summary = await fetchJSON('/api/summary');
  if (!summary || summary.length === 0) return;

  // Find current month
  const today = new Date();
  const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
  const current = summary.find(s => s.month === currentMonth) || { income: 0, expense: 0 };

  const income = current.income || 0;
  const expense = current.expense || 0;
  const net = income - expense;

  document.getElementById('statIncome').textContent = `₹${income.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  document.getElementById('statExpense').textContent = `₹${expense.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

  const netEl = document.getElementById('statNet');
  netEl.textContent = `₹${Math.abs(net).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  netEl.style.color = net >= 0 ? 'var(--income)' : 'var(--expense)';
  if (net < 0) netEl.textContent = '-' + netEl.textContent;
}

// ─────────────────────────────────────────
// Trend Chart (line — income vs expense)
// ─────────────────────────────────────────

async function loadTrendChart() {
  const data = await fetchJSON('/api/summary');
  if (!data) return;

  const labels = data.map(d => {
    const [year, month] = d.month.split('-');
    return new Date(year, month - 1).toLocaleString('default', { month: 'short', year: '2-digit' });
  });

  new Chart(document.getElementById('trendChart'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Income',
          data: data.map(d => d.income || 0),
          borderColor: CHART_DEFAULTS.accent,
          backgroundColor: 'rgba(34,197,94,0.08)',
          tension: 0.4,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: CHART_DEFAULTS.accent,
        },
        {
          label: 'Expenses',
          data: data.map(d => d.expense || 0),
          borderColor: CHART_DEFAULTS.expense,
          backgroundColor: 'rgba(249,115,22,0.08)',
          tension: 0.4,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: CHART_DEFAULTS.expense,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: CHART_DEFAULTS.color, font: { family: 'Inter', size: 12 } } },
      },
      scales: {
        x: { ticks: { color: CHART_DEFAULTS.color }, grid: { color: CHART_DEFAULTS.gridColor } },
        y: { ticks: { color: CHART_DEFAULTS.color, callback: v => `₹${v.toLocaleString('en-IN')}` }, grid: { color: CHART_DEFAULTS.gridColor } },
      },
    },
  });
}

// ─────────────────────────────────────────
// Category Donut Chart
// ─────────────────────────────────────────

async function loadCategoryChart() {
  const data = await fetchJSON('/api/categories');
  if (!data || data.length === 0) {
    document.getElementById('categoryChart').parentElement.innerHTML +=
      '<p style="color:var(--text-muted);font-size:13px;text-align:center;margin-top:16px">No expenses this month yet.</p>';
    return;
  }

  const palette = [
    '#22c55e','#f97316','#3b82f6','#a855f7',
    '#ec4899','#14b8a6','#f59e0b','#6366f1',
  ];

  new Chart(document.getElementById('categoryChart'), {
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
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: CHART_DEFAULTS.color, font: { family: 'Inter', size: 12 }, padding: 12 },
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
// Transactions Table
// ─────────────────────────────────────────

async function loadTransactions() {
  const data = await fetchJSON('/api/transactions?limit=20');
  const tbody = document.getElementById('txnTableBody');

  if (!data || data.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No transactions yet. Start chatting to log one!</td></tr>';
    return;
  }

  tbody.innerHTML = data.map(t => `
    <tr>
      <td>${t.date}</td>
      <td>${t.category.charAt(0).toUpperCase() + t.category.slice(1)}</td>
      <td style="color:var(--text-muted)">${t.description || '—'}</td>
      <td><span class="badge badge-${t.type}">${t.type}</span></td>
      <td style="font-family:var(--font-mono);font-weight:600">₹${parseFloat(t.amount).toLocaleString('en-IN')}</td>
    </tr>
  `).join('');
}

// ─────────────────────────────────────────
// Boot
// ─────────────────────────────────────────

loadStats();
loadTrendChart();
loadCategoryChart();
loadTransactions();
