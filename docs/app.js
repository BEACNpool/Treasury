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
function plotYearly(rows, offchainYearly=null) {
  const year = rows.map(r => toNum(r.year));
  const fees = rows.map(r => toNum(r.fees_ada));
  const inflow = rows.map(r => toNum(r.inflow_fees_plus_reserves_ada));
  const delta = rows.map(r => toNum(r.treasury_delta_ada));
  const withdrawals = rows.map(r => toNum(r.withdrawals_ada));

  const impliedOther = rows.map(r => toNum(r.implied_outflow_other_ada));

  const withdrawalsAllZero = withdrawals.every(v => !v || v === 0);

  const traces = [
    { x: year, y: fees, name: 'Fees (on-chain)', mode: 'lines+markers', line: { color: COLORS.fees } },
    { x: year, y: inflow, name: 'Est. Inflow (on-chain)', mode: 'lines+markers', line: { color: COLORS.inflow } },

    // "Explicit" withdrawals are what we can attribute cleanly from known tables.
    // If this is all-zero, keep it out of the way by default.
    { x: year, y: withdrawals, name: 'Withdrawals (explicit, on-chain)', mode: 'lines+markers', line: { color: COLORS.withdrawals }, visible: withdrawalsAllZero ? 'legendonly' : true },

    // Ledger-reconciled outflow that makes the identity balance.
    { x: year, y: impliedOther, name: 'Outflow (implied, on-chain)', mode: 'lines+markers', line: { color: '#f97316', width: 2 } },

    { x: year, y: delta, name: 'Treasury Δ (on-chain)', mode: 'lines+markers', line: { color: COLORS.delta } },
  ];

  if (offchainYearly && offchainYearly.length) {
    const oy = offchainYearly.map(r => toNum(r.year));
    const ada = offchainYearly.map(r => toNum(r.distributed_ada));
    traces.push({
      x: oy,
      y: ada,
      name: 'Catalyst Distributed (off-chain, ADA)',
      mode: 'lines+markers',
      line: { color: '#a78bfa', dash: 'dot', width: 2 },
      marker: { color: '#a78bfa' },
      opacity: 0.9,
    });
  }

  Plotly.newPlot('chart_yearly', traces, {
    ...PLOT_LAYOUT_BASE,
    xaxis: { ...PLOT_LAYOUT_BASE.xaxis, title: 'Year' },
    yaxis: { ...PLOT_LAYOUT_BASE.yaxis, title: 'ADA' },
  }, PLOT_CFG);

  const bar2 = withdrawalsAllZero ? impliedOther : withdrawals;
  const bar2Name = withdrawalsAllZero ? 'Outflow (implied)' : 'Withdrawals (explicit)';

  Plotly.newPlot('chart_fees_withdrawals', [
    { x: year, y: fees, name: 'Fees', type: 'bar', marker: { color: COLORS.fees } },
    { x: year, y: bar2, name: bar2Name, type: 'bar', marker: { color: withdrawalsAllZero ? '#f97316' : COLORS.withdrawals } },
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

function sevLabel(sev){
  const s = (sev || '').toLowerCase();
  if(['red','orange','yellow','green'].includes(s)) return s;
  return 'yellow';
}

function renderFlags(flags, metaFlags){
  if(!flags || flags.length === 0) return;
  const card = document.getElementById('flags-card');
  const metaEl = document.getElementById('flags-meta');
  const list = document.getElementById('flags-list');
  card.style.display = '';

  if(metaFlags){
    const parts = [];
    if(metaFlags.generated_at_utc) parts.push(`generated: ${metaFlags.generated_at_utc}`);
    if(metaFlags.data_tip_time) parts.push(`tip: ${metaFlags.data_tip_time}`);
    if(metaFlags.source_kind) parts.push(`source: ${metaFlags.source_kind}`);
    metaEl.textContent = parts.join(' · ');
  }

  list.innerHTML = '';
  flags.slice(0, 50).forEach(f => {
    const item = document.createElement('div');
    item.className = 'flag';

    const sev = sevLabel(f.severity);
    const badge = document.createElement('span');
    badge.className = `flag-badge sev-${sev}`;
    badge.textContent = sev.toUpperCase();

    const title = document.createElement('span');
    title.className = 'flag-title';
    title.textContent = f.title || f.flag_id || 'Flag';

    const src = document.createElement('span');
    src.className = 'flag-src';
    const sk = (f.source_kind || '').toLowerCase();
    src.textContent = sk === 'onchain' ? '● on-chain' : sk === 'offchain' ? '■ off-chain' : sk === 'heuristic' ? '▲ heuristic' : '';

    const body = document.createElement('div');
    body.className = 'flag-body';
    body.textContent = f.summary || f.definition || '';

    const small = document.createElement('div');
    small.className = 'flag-small';
    const conf = f.confidence ? `confidence: ${f.confidence}` : '';
    const ent = f.entity_id ? `entity: ${f.entity_id}` : '';
    small.textContent = [src.textContent, conf, ent].filter(Boolean).join(' · ');

    const head = document.createElement('div');
    head.className = 'flag-head';
    head.appendChild(badge);
    head.appendChild(title);
    if(src.textContent) head.appendChild(src);

    item.appendChild(head);
    if(body.textContent) item.appendChild(body);
    if(small.textContent) item.appendChild(small);

    list.appendChild(item);
  });
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

    // Load flags.json (optional)
    try {
      const flagsText = await fetchText('outputs/flags.json');
      const flagsPayload = JSON.parse(flagsText);
      const flags = Array.isArray(flagsPayload) ? flagsPayload : (flagsPayload.flags || []);
      const metaFlags = flagsPayload.meta || null;
      renderFlags(flags, metaFlags);
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
    const withdrawalsAllZero = enrichedYear.every(r => (toNum(r.withdrawals_ada) || 0) === 0);
    const withdrawNote = withdrawalsAllZero ? ' · note: explicit withdrawals currently 0; using implied outflow series' : '';
    if (meta && meta.network_name) {
      const tip = meta.tip_time ? meta.tip_time.split('T')[0] : 'unknown';
      const gen = meta.generated_at_utc ? meta.generated_at_utc.split('T')[0] : 'unknown';
      status.innerHTML = `<strong>${meta.network_name}</strong> · ${meta.source_kind || '?'} · tip: ${tip} · generated: ${gen} · ${enrichedYear.length} years (${years[0]}–${years[years.length - 1]})${withdrawNote}`;
    } else {
      status.textContent = `Loaded ${enrichedYear.length} years (${years[0]}–${years[years.length - 1]})`;
    }

    // Off-chain yearly (optional): Catalyst distributions
    let catalystYearly = null;
    try {
      const cyText = await fetchText('outputs/offchain/catalyst/yearly_distributions.csv');
      catalystYearly = parseCSV(cyText).rows;
    } catch (e) { /* not present yet */ }

    // Yearly charts + table (combo: on-chain + off-chain)
    plotYearly(enrichedYear, catalystYearly);

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

    // Off-chain: Catalyst (optional)
    try {
      const sumText = await fetchText('outputs/offchain/catalyst/summary.json');
      const summary = JSON.parse(sumText);
      const el = document.getElementById('catalyst-summary');
      if (el) {
        const c = summary.counts || {};
        const t = summary.totals_usd || {};
        el.innerHTML = `rows: ${fmt(c.proposers_total)} · funded: ${fmt(c.proposers_with_funded_projects)} · completed: ${fmt(c.proposers_with_completed_projects)}<br>` +
          `distributed (USD): ${fmt(t.distributed_usd)} · remaining (USD): ${fmt(t.remaining_usd)} · requested (USD): ${fmt(t.requested_usd)}<br>` +
          `generated: ${summary.generated_at_utc || 'unknown'}`;
      }

      const topText = await fetchText('outputs/offchain/catalyst/top_recipients.csv');
      const { rows: topRows } = parseCSV(topText);
      const tbl = document.getElementById('table-catalyst-top');
      if (tbl) {
        buildTable(
          tbl,
          ['name', 'username', 'total_distributed_usd', 'funded_projects', 'completed_projects', 'total_projects'],
          {
            name: 'Name',
            username: 'Handle',
            total_distributed_usd: 'Distributed (USD)',
            funded_projects: 'Funded',
            completed_projects: 'Completed',
            total_projects: 'Total',
          },
          topRows,
          { colorDelta: false }
        );
      }

      const btn = document.getElementById('btn-download-catalyst-top');
      if (btn) {
        btn.disabled = false;
        btn.addEventListener('click', () => downloadCSV(topText, 'catalyst_top_recipients.csv'));
      }
    } catch (e) {
      const el = document.getElementById('catalyst-summary');
      if (el) el.textContent = 'No off-chain Catalyst data published yet.';
    }

  } catch (e) {
    status.textContent = `No data yet. Run the pipeline and publish outputs first. (${e.message})`;
  }
}

main();
