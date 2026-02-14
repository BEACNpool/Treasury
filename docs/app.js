/* Cardano Treasury Dashboard — app.js */

// ── Helpers ──────────────────────────────────────────
async function fetchText(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`fetch ${url} -> ${r.status}`);
  return await r.text();
}

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(',');
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',');
    const obj = {};
    headers.forEach((h, idx) => obj[h] = cols[idx]);
    rows.push(obj);
  }
  return { headers, rows };
}

function toNum(x) {
  const v = Number(x);
  return Number.isFinite(v) ? v : null;
}

function fmt(n) {
  if (n === null || n === undefined) return '';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n);
}

function fmtCompact(n) {
  if (n === null || n === undefined) return '';
  const abs = Math.abs(n);
  if (abs >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (abs >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (abs >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return fmt(n);
}

function downloadCSV(text, filename) {
  const blob = new Blob([text], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Plotly shared config ─────────────────────────────
const PLOT_LAYOUT_BASE = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  margin: { l: 70, r: 20, t: 10, b: 50 },
  xaxis: { gridcolor: '#233044', color: '#9fb0c0' },
  yaxis: { gridcolor: '#233044', color: '#9fb0c0' },
  legend: { orientation: 'h', y: -0.22, font: { color: '#9fb0c0', size: 11 } },
  font: { color: '#e6edf3', size: 12 },
  hoverlabel: { bgcolor: '#1e293b', bordercolor: '#334155', font: { color: '#e6edf3' } },
};

const PLOT_CFG = { displayModeBar: false, responsive: true };

const COLORS = {
  fees: '#60a5fa',
  inflow: '#34d399',
  withdrawals: '#f87171',
  delta: '#fbbf24',
  balance: '#a78bfa',
};

// ── Table builder ────────────────────────────────────
function buildTable(el, cols, display, rows, opts = {}) {
  const { colorDelta = false } = opts;

  const thead = document.createElement('thead');
  const trh = document.createElement('tr');
  cols.forEach(c => {
    const th = document.createElement('th');
    th.textContent = display[c] || c;
    trh.appendChild(th);
  });
  thead.appendChild(trh);

  const tbody = document.createElement('tbody');
  rows.forEach(r => {
    const tr = document.createElement('tr');
    cols.forEach(c => {
      const td = document.createElement('td');
      const raw = c.includes('year') || c.includes('epoch') ? r[c] : toNum(r[c]);
      if (typeof raw === 'number' && raw !== null) {
        td.textContent = fmt(raw);
        if (colorDelta && (c.includes('delta') || c.includes('implied'))) {
          td.className = raw >= 0 ? 'val-pos' : 'val-neg';
        }
      } else {
        td.textContent = r[c] || '';
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  el.innerHTML = '';
  el.appendChild(thead);
  el.appendChild(tbody);
}

// ── Tabs ─────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
      window.dispatchEvent(new Event('resize')); // re-render Plotly charts
    });
  });
}

// ── Yearly charts ────────────────────────────────────
function plotYearly(rows) {
  const year = rows.map(r => toNum(r.year));
  const fees = rows.map(r => toNum(r.fees_ada));
  const inflow = rows.map(r => toNum(r.inflow_fees_plus_reserves_ada));
  const delta = rows.map(r => toNum(r.treasury_delta_ada));
  const withdrawals = rows.map(r => toNum(r.withdrawals_ada));

  Plotly.newPlot('chart_yearly', [
    { x: year, y: fees, name: 'Fees', mode: 'lines+markers', line: { color: COLORS.fees } },
    { x: year, y: inflow, name: 'Est. Inflow', mode: 'lines+markers', line: { color: COLORS.inflow } },
    { x: year, y: withdrawals, name: 'Withdrawals', mode: 'lines+markers', line: { color: COLORS.withdrawals } },
    { x: year, y: delta, name: 'Treasury Δ', mode: 'lines+markers', line: { color: COLORS.delta } },
  ], {
    ...PLOT_LAYOUT_BASE,
    xaxis: { ...PLOT_LAYOUT_BASE.xaxis, title: 'Year' },
    yaxis: { ...PLOT_LAYOUT_BASE.yaxis, title: 'ADA' },
  }, PLOT_CFG);

  Plotly.newPlot('chart_fees_withdrawals', [
    { x: year, y: fees, name: 'Fees', type: 'bar', marker: { color: COLORS.fees } },
    { x: year, y: withdrawals, name: 'Withdrawals', type: 'bar', marker: { color: COLORS.withdrawals } },
  ], {
    ...PLOT_LAYOUT_BASE,
    barmode: 'group',
    xaxis: { ...PLOT_LAYOUT_BASE.xaxis, title: 'Year' },
    yaxis: { ...PLOT_LAYOUT_BASE.yaxis, title: 'ADA' },
  }, PLOT_CFG);
}

// ── Epoch charts ─────────────────────────────────────
function plotEpoch(rows) {
  const epochs = rows.map(r => toNum(r.epoch_no));
  const balance = rows.map(r => toNum(r.treasury_end_ada));
  const fees = rows.map(r => toNum(r.fees_epoch_ada));

  Plotly.newPlot('chart_balance', [
    { x: epochs, y: balance, name: 'Treasury Balance', mode: 'lines', line: { color: COLORS.balance, width: 1.5 }, fill: 'tozeroy', fillcolor: 'rgba(167,139,250,0.08)' },
  ], {
    ...PLOT_LAYOUT_BASE,
    xaxis: { ...PLOT_LAYOUT_BASE.xaxis, title: 'Epoch' },
    yaxis: { ...PLOT_LAYOUT_BASE.yaxis, title: 'ADA' },
    showlegend: false,
  }, PLOT_CFG);

  Plotly.newPlot('chart_epoch_fees', [
    { x: epochs, y: fees, name: 'Fees', type: 'bar', marker: { color: COLORS.fees, opacity: 0.7 } },
  ], {
    ...PLOT_LAYOUT_BASE,
    xaxis: { ...PLOT_LAYOUT_BASE.xaxis, title: 'Epoch' },
    yaxis: { ...PLOT_LAYOUT_BASE.yaxis, title: 'ADA' },
    showlegend: false,
  }, PLOT_CFG);
}

// ── Main ─────────────────────────────────────────────
async function main() {
  const status = document.getElementById('status');
  initTabs();

  let yearCSVText = null;
  let epochCSVText = null;

  try {
    // Load status.json (optional)
    let meta = null;
    try {
      meta = JSON.parse(await fetchText('outputs/status.json'));
    } catch (e) { /* not present yet */ }

    // Load year CSV
    yearCSVText = await fetchText('outputs/year_treasury_fees.csv');
    const { rows: yearRows } = parseCSV(yearCSVText);

    // Enrich: compute withdrawals column
    const enrichedYear = yearRows.map(r => {
      const mir = toNum(r.mir_treasury_payments_ada) || 0;
      const conway = toNum(r.conway_enacted_withdrawals_ada) || 0;
      r.withdrawals_ada = String(mir + conway);
      return r;
    });

    // Status text
    const years = enrichedYear.map(r => r.year).filter(Boolean);
    if (meta && meta.network_name) {
      const tip = meta.tip_time ? meta.tip_time.split('T')[0] : 'unknown';
      const gen = meta.generated_at_utc ? meta.generated_at_utc.split('T')[0] : 'unknown';
      status.innerHTML = `<strong>${meta.network_name}</strong> · ${meta.source_kind || '?'} · tip: ${tip} · generated: ${gen} · ${enrichedYear.length} years (${years[0]}–${years[years.length - 1]})`;
    } else {
      status.textContent = `Loaded ${enrichedYear.length} years (${years[0]}–${years[years.length - 1]})`;
    }

    // Yearly charts + table
    plotYearly(enrichedYear);

    buildTable(
      document.getElementById('table-year'),
      ['year', 'fees_ada', 'inflow_fees_plus_reserves_ada', 'withdrawals_ada', 'treasury_donations_ada', 'treasury_delta_ada', 'implied_outflow_other_ada'],
      {
        year: 'Year',
        fees_ada: 'Fees (ADA)',
        inflow_fees_plus_reserves_ada: 'Est. Inflow',
        withdrawals_ada: 'Withdrawals',
        treasury_donations_ada: 'Donations',
        treasury_delta_ada: 'Treasury Δ',
        implied_outflow_other_ada: 'Implied Other Outflow',
      },
      enrichedYear,
      { colorDelta: true }
    );

    // Enable download
    const btnYear = document.getElementById('btn-download-year');
    btnYear.disabled = false;
    btnYear.addEventListener('click', () => downloadCSV(yearCSVText, 'year_treasury_fees.csv'));

    // Load epoch CSV
    try {
      epochCSVText = await fetchText('outputs/epoch_treasury_fees.csv');
      const { rows: epochRows } = parseCSV(epochCSVText);

      document.getElementById('epoch-count').textContent = `(${epochRows.length} total epochs)`;

      // Epoch charts (all data)
      plotEpoch(epochRows);

      // Epoch table (last 50 rows, newest first)
      const recentEpochs = epochRows.slice(-50).reverse();
      buildTable(
        document.getElementById('table-epoch'),
        ['epoch_no', 'fees_epoch_ada', 'treasury_end_ada', 'treasury_delta_ada', 'inflow_fees_plus_reserves_est_ada', 'conway_enacted_withdrawals_ada', 'treasury_donations_ada'],
        {
          epoch_no: 'Epoch',
          fees_epoch_ada: 'Fees (ADA)',
          treasury_end_ada: 'Balance (ADA)',
          treasury_delta_ada: 'Δ Treasury',
          inflow_fees_plus_reserves_est_ada: 'Est. Inflow',
          conway_enacted_withdrawals_ada: 'Conway Withdrawals',
          treasury_donations_ada: 'Donations',
        },
        recentEpochs,
        { colorDelta: true }
      );

      const btnEpoch = document.getElementById('btn-download-epoch');
      btnEpoch.disabled = false;
      btnEpoch.addEventListener('click', () => downloadCSV(epochCSVText, 'epoch_treasury_fees.csv'));
    } catch (e) {
      document.getElementById('epoch-count').textContent = '(epoch data not available yet)';
    }

  } catch (e) {
    status.textContent = `No data yet. Run the pipeline and publish outputs first. (${e.message})`;
  }
}

main();
